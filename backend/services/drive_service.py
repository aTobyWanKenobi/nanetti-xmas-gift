import os
import json
import random
import logging
import threading
import io
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import requests
from PIL import Image
from pillow_heif import register_heif_opener

# Register HEIF opener for Pillow
register_heif_opener()

load_dotenv()

logger = logging.getLogger(__name__)


class DriveService:
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self):
        self.creds = self._get_credentials()
        self.service = build("drive", "v3", credentials=self.creds)
        self._cache: Dict[str, List[Dict]] = {}
        # We don't use expiry anymore, we use background refresher
        self._is_refreshing: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def _get_credentials(self):
        # Try to get from Env Var (JSON content)
        json_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if json_creds:
            try:
                info = json.loads(json_creds)
                return service_account.Credentials.from_service_account_info(
                    info, scopes=self.SCOPES
                )
            except json.JSONDecodeError:
                logger.error("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON")
                raise ValueError("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON")

        # Try to load from file
        creds_file = "service_account.json"
        if os.path.exists(creds_file):
            return service_account.Credentials.from_service_account_file(
                creds_file, scopes=self.SCOPES
            )

        raise ValueError(
            "No credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON or provide service_account.json"
        )

    def _fetch_page(
        self, folder_id: str, page_token: Optional[str] = None
    ) -> tuple[List[Dict], Optional[str]]:
        """Fetches a single page of files."""
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        try:
            response = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, webContentLink, webViewLink, thumbnailLink, mimeType)",
                    pageToken=page_token,
                    pageSize=1000,  # Maximize page size
                )
                .execute()
            )
            return response.get("files", []), response.get("nextPageToken", None)
        except HttpError as error:
            logger.error(f"An error occurred fetching page: {error}")
            return [], None

    def _background_refresh_task(self, folder_id: str):
        """Background task to fetch all files."""
        logger.info(f"Starting background refresh for {folder_id}")
        all_files = []
        page_token = None

        while True:
            files, next_token = self._fetch_page(folder_id, page_token)
            all_files.extend(files)

            # Update cache incrementally if it was empty, so users get some photos quickly?
            # Or just swap at the end. Swapping at end is safer for consistency.
            # But for large libraries, maybe we want partial updates.
            # Let's just swap at the end for simplicity, assuming <5000 photos.

            page_token = next_token
            if page_token is None:
                break

        with self._lock:
            self._cache[folder_id] = all_files
            self._is_refreshing[folder_id] = False

        logger.info(f"Background refresh finished. Total files: {len(all_files)}")

    def ensure_cache(self, folder_id: str):
        """Ensures cache is populated or starting to populate."""
        with self._lock:
            if folder_id in self._cache and self._cache[folder_id]:
                # We have data. Is it stale? Maybe.
                # But we don't block. We could trigger a refresh if it's been a long time.
                # For now, we rely on app restarts or manual triggers (not implemented yet).
                # Let's just return.
                return

            if self._is_refreshing.get(folder_id, False):
                return  # Already running

            # Cache is empty and not refreshing. Start refresh.
            self._is_refreshing[folder_id] = True

            # OPTIONAL: Fetch first page synchronously so we don't return None immediately
            # if this is the very first call.
            if folder_id not in self._cache:
                logger.info("Fetching first page synchronously...")
                first_batch, next_token = self._fetch_page(folder_id)
                self._cache[folder_id] = first_batch
                if next_token is None:
                    self._is_refreshing[folder_id] = False
                    return  # We are done

            # Start background thread for the rest
            thread = threading.Thread(
                target=self._background_refresh_task, args=(folder_id,)
            )
            thread.daemon = True
            thread.start()

    def get_random_photo(self, folder_id: str) -> Optional[Dict]:
        self.ensure_cache(folder_id)

        with self._lock:
            files = self._cache.get(folder_id)

        if not files:
            return None

        return random.choice(files)

    def get_file_content(
        self, file_id: str, high_quality=True
    ) -> tuple[io.BytesIO, str]:
        """
        Downloads file content.
        Promotes HEIC to JPEG.
        Uses thumbnailLink for speed if suitable.
        Returns (content_stream, mime_type)
        """
        # 1. Get file metadata to check type and thumbnail link
        try:
            file_meta = (
                self.service.files()
                .get(fileId=file_id, fields="id, name, mimeType, thumbnailLink")
                .execute()
            )
        except HttpError as e:
            logger.error(f"Error getting file meta: {e}")
            raise

        mime_type = file_meta.get("mimeType", "")
        thumbnail_link = file_meta.get("thumbnailLink")

        # Strategy:
        # If possible, use the thumbnailLink with a high resolution parameter (e.g. s1600 or s3000)
        # This is usually a JPEG served by Google, which effectively handles HEIC conversion AND resizing.
        # This is MUCH faster than downloading original HEIC and converting locally.

        # 's' parameter controls size. 's0' might be full size but we want a reasonable max.
        # s2048 is decent for web.

        use_thumbnail = True

        if use_thumbnail and thumbnail_link:
            # Modify the link size parameter
            # thumbnailLink usually looks like: https://lh3.googleusercontent.com/...?s=220
            # We strip the last param and add ours.
            base_link = thumbnail_link
            if "=s" in thumbnail_link:
                base_link = thumbnail_link.split("=s")[0]
            elif "?s=" in thumbnail_link:
                base_link = (
                    thumbnail_link.split("?s=")[0] + "?"
                )  # Maintain query start if needed, but usually ?s= is the start
                if base_link.endswith("?"):
                    base_link = base_link[:-1]  # Remove trailing ? if it was valid

            # If we rely on string splitting it's fragile. But for now common cases:
            # - .../docid=s220
            # - ...?s=220

            # Simple approach: append =s1600 if we have a base without size,
            # or try to replace query param.
            # Best effort:

            if "?s=" in thumbnail_link:
                base_link = thumbnail_link.split("?s=")[0]
                download_url = f"{base_link}?s=1600"
            elif "=s" in thumbnail_link:
                base_link = thumbnail_link.split("=s")[0]
                download_url = f"{base_link}=s1600"
            else:
                # Just append, hoping it works
                download_url = f"{thumbnail_link}=s1600"

            try:
                # Add timeout to prevent hanging on bad thumbnails
                resp = requests.get(download_url, timeout=5)
                resp.raise_for_status()

                # Validation: Check Content-Type
                content_type = resp.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    logger.warning(
                        f"Thumbnail had non-image Content-Type: {content_type}. Content preview: {resp.content[:100]}"
                    )
                    raise ValueError("Invalid Content-Type")

                # Validation: Check if it's really an image
                try:
                    img_test = Image.open(io.BytesIO(resp.content))
                    img_test.verify()
                except Exception as e:
                    logger.warning(f"Thumbnail bytes verification failed: {e}")
                    raise ValueError("Invalid Image Bytes")

                return io.BytesIO(resp.content), "image/jpeg"
            except Exception as e:
                logger.warning(
                    f"Thumbnail fetch failed for file {file_id} ({e}), falling back to full download"
                )
                # Fallback to full download below

        # Fallback: Download full file
        logger.info(f"Downloading full file {file_id}")
        raw_stream = self._download_raw(file_id)

        # Convert if HEIC
        if "heif" in mime_type.lower() or "heic" in mime_type.lower():
            logger.info("Converting HEIC to JPEG...")
            try:
                image = Image.open(raw_stream)
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=85)
                output.seek(0)
                return output, "image/jpeg"
            except Exception as e:
                logger.error(f"HEIC conversion failed: {e}")
                # Return original if conversion fails, though browser might not show it
                raw_stream.seek(0)
                return raw_stream, mime_type

        return raw_stream, mime_type

    def _download_raw(self, file_id: str) -> io.BytesIO:
        if not self.creds.valid:
            self.creds.refresh(Request())

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        headers = {"Authorization": f"Bearer {self.creds.token}"}

        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        # buffer in memory
        return io.BytesIO(response.content)
