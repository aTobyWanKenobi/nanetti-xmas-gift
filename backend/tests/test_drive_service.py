import pytest
from unittest.mock import MagicMock, patch
from services.drive_service import DriveService


@pytest.fixture
def drive_service():
    with (
        patch(
            "services.drive_service.service_account.Credentials.from_service_account_info"
        ),
        patch("services.drive_service.build"),
    ):
        service = DriveService()
        return service


def test_drive_service_init(drive_service):
    assert drive_service.service is not None


def test_ensure_cache_starts_background_task(drive_service):
    # Mock threading.Thread to verify it starts
    with patch("services.drive_service.threading.Thread") as mock_thread_cls:
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        # Mock fetch_page for sync path
        drive_service._fetch_page = MagicMock(return_value=([], None))

        drive_service.ensure_cache("folder123")

        drive_service._fetch_page.return_value = ([], "token")

        # Reset to clear previous calls
        drive_service._cache = {}
        drive_service._is_refreshing = {}

        drive_service.ensure_cache("folder123")

        mock_thread.start.assert_called_once()


def test_get_random_photo_returns_none_when_empty(drive_service):
    # If cache is empty and sync fetch returns nothing
    drive_service._fetch_page = MagicMock(return_value=([], None))
    # Avoid thread start by not returning token

    photo = drive_service.get_random_photo("folder123")
    assert photo is None


def test_get_random_photo_returns_file(drive_service):
    # Pre-populate cache
    drive_service._cache["folder123"] = [{"id": "1"}, {"id": "2"}]

    photo = drive_service.get_random_photo("folder123")
    assert photo is not None
    assert photo["id"] in ["1", "2"]


def test_get_file_content_download_simple(drive_service):
    # Test simple download path without checking for thumbnails
    mock_files = drive_service.service.files.return_value
    mock_get_req = mock_files.get.return_value
    mock_get_req.execute.return_value = {
        "id": "1",
        "mimeType": "image/jpeg",
    }

    with patch("services.drive_service.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.content = b"raw data"
        mock_get.return_value = mock_resp

        content, mime = drive_service.get_file_content("file1")

        assert mime == "image/jpeg"
        assert content.read() == b"raw data"
