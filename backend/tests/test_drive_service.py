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

        # Should start thread if cache empty
        # First call might trigger sync fetch then if done, no thread?
        # In our implementation:
        #   if folder not in cache: fetch first page sync.
        #   if next_token is None: done.
        # So mocks need to return next_token to trigger thread.

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


def test_get_file_content_thumbnail(drive_service):
    # Test optimized path
    with patch("services.drive_service.requests.get") as mock_get:
        # Mock file metadata response
        mock_files = drive_service.service.files.return_value
        mock_get_req = mock_files.get.return_value
        mock_get_req.execute.return_value = {
            "id": "1",
            "mimeType": "image/jpeg",
            "thumbnailLink": "http://thumb/foo=s220",
        }

        mock_resp = MagicMock()
        mock_resp.content = b"thumbnail data"
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_get.return_value = mock_resp

        with patch("services.drive_service.Image.open") as mock_img_open:
            mock_img = MagicMock()
            mock_img_open.return_value = mock_img

            content, mime = drive_service.get_file_content("file1")

            assert mime == "image/jpeg"
            assert content.read() == b"thumbnail data"
            # Verify it called the resized link
            mock_get.assert_called_with("http://thumb/foo=s1600", timeout=5)


def test_get_file_content_fallback_download(drive_service):
    # Test fallback path when no thumbnail
    mock_files = drive_service.service.files.return_value
    mock_get_req = mock_files.get.return_value
    mock_get_req.execute.return_value = {
        "id": "1",
        "mimeType": "image/png",  # No thumbnail link
    }

    with patch("services.drive_service.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.content = b"raw data"
        mock_get.return_value = mock_resp

        content, mime = drive_service.get_file_content("file1")

        assert mime == "image/png"
        assert content.read() == b"raw data"


def test_get_file_content_thumbnail_invalid_fallback(drive_service):
    # Test fallback when thumbnail exists but returns invalid content (e.g. login page)
    with patch("services.drive_service.requests.get") as mock_get:
        # Mock file metadata response
        mock_files = drive_service.service.files.return_value
        mock_get_req = mock_files.get.return_value
        mock_get_req.execute.return_value = {
            "id": "1",
            "mimeType": "image/jpeg",
            "thumbnailLink": "http://thumb/foo=s220",
        }

        # First response: Invalid (e.g. HTML)
        bad_resp = MagicMock()
        bad_resp.content = b"<html>Login</html>"
        bad_resp.headers = {"Content-Type": "text/html"}

        # Second response: Valid raw download
        good_resp = MagicMock()
        good_resp.content = b"raw image data"
        # _download_raw doesn't check headers, just returns content

        mock_get.side_effect = [bad_resp, good_resp]

        content, mime = drive_service.get_file_content("file1")

        # Should return raw data (fallback)
        assert content.read() == b"raw image data"

        # Verify both calls were made
        assert mock_get.call_count == 2
        # First call to thumbnail
        mock_get.call_args_list[0].args[0] == "http://thumb/foo=s1600"
        # Second call to API
        assert "googleapis.com" in mock_get.call_args_list[1].args[0]
