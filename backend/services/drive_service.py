import os
import json
import random
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
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
        self._cache_expiry: Dict[str, datetime] = {}
        self.CACHE_DURATION = timedelta(minutes=60)  # Cache file list for 1 hour

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

    def list_files(self, folder_id: str) -> List[Dict]:
        """Lists image files in the specified folder with caching."""
        if not folder_id:
            raise ValueError("Folder ID is required")

        # Check cache
        if folder_id in self._cache and datetime.now() < self._cache_expiry.get(
            folder_id, datetime.min
        ):
            logger.info(f"Returning cached files for folder {folder_id}")
            return self._cache[folder_id]

        try:
            results = []
            page_token = None
            query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"

            while True:
                response = (
                    self.service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name, webContentLink, webViewLink, thumbnailLink)",
                        pageToken=page_token,
                    )
                    .execute()
                )

                items = response.get("files", [])
                results.extend(items)

                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break

            # Update cache
            self._cache[folder_id] = results
            self._cache_expiry[folder_id] = datetime.now() + self.CACHE_DURATION
            logger.info(f"Found {len(results)} images in folder {folder_id}")
            return results

        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            raise

    def get_random_photo(self, folder_id: str) -> Optional[Dict]:
        files = self.list_files(folder_id)
        if not files:
            return None
        return random.choice(files)

    def download_file(self, file_id: str):
        """Downloads a file using requests and returns the raw stream."""
        try:
            # excessive caching?
            if not self.creds.valid:
                self.creds.refresh(Request())

            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            headers = {"Authorization": f"Bearer {self.creds.token}"}

            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            return response.raw
        except Exception as error:
            logger.error(f"An error occurred downloading file: {error}")
            raise
