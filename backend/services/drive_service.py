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
                    fields="nextPageToken, files(id, name, mimeType)",
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
                return

            if self._is_refreshing.get(folder_id, False):
                return  # Already running

            # Cache is empty and not refreshing. Start refresh.
            self._is_refreshing[folder_id] = True

            # OPTIONAL: Fetch first page synchronously so we don't return None immediately
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
        Simplified version: no thumbnails, no HEIC conversion.
        Returns (content_stream, mime_type)
        """
        # 1. Get file metadata to check type
        try:
            file_meta = (
                self.service.files()
                .get(fileId=file_id, fields="id, name, mimeType")
                .execute()
            )
        except HttpError as e:
            logger.error(f"Error getting file meta: {e}")
            raise

        mime_type = file_meta.get("mimeType", "application/octet-stream")

        # Download full file
        logger.info(f"Downloading full file {file_id}")
        raw_stream = self._download_raw(file_id)

        return raw_stream, mime_type

    def _download_raw(self, file_id: str) -> io.BytesIO:
        if not self.creds.valid:
            self.creds.refresh(Request())

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        headers = {"Authorization": f"Bearer {self.creds.token}"}

        # Removed timeout=5 to ensure large files can download even if slow,
        # or we could keep a generous timeout. Let's stick to default (requests default is no timeout)
        # or a reasonable one.
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        # buffer in memory
        return io.BytesIO(response.content)
