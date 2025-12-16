import pytest
from unittest.mock import MagicMock, patch
from services.drive_service import DriveService


@pytest.fixture
def mock_creds():
    with patch(
        "google.oauth2.service_account.Credentials.from_service_account_info"
    ) as mock:
        yield mock


@pytest.fixture
def mock_build():
    with patch("services.drive_service.build") as mock:
        yield mock


@pytest.fixture
def drive_service(mock_creds, mock_build):
    # Mock env vars
    with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": '{"test":"json"}'}):
        service = DriveService()
        return service


def test_init_with_env_var(mock_creds, mock_build):
    with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": '{"test":"json"}'}):
        service = DriveService()
        assert service.creds is not None


def test_init_no_creds():
    with patch.dict("os.environ", {}, clear=True):
        with patch("os.path.exists", return_value=False):
            with pytest.raises(ValueError, match="No credentials found"):
                DriveService()


def test_list_files_success(drive_service):
    # Mock service chain
    mock_files = drive_service.service.files.return_value
    mock_list = mock_files.list.return_value
    mock_list.execute.side_effect = [
        {
            "files": [{"id": "1", "name": "1.jpg"}, {"id": "2", "name": "2.jpg"}],
            "nextPageToken": None,
        }
    ]

    files = drive_service.list_files("folder123")
    assert len(files) == 2
    assert files[0]["id"] == "1"

    # Verify call arguments
    mock_files.list.assert_called()


def test_list_files_caching(drive_service):
    # First call
    mock_files = drive_service.service.files.return_value
    mock_list = mock_files.list.return_value
    mock_list.execute.return_value = {"files": [{"id": "1"}], "nextPageToken": None}

    drive_service.list_files("folder123")

    # Second call (should hit cache)
    drive_service.list_files("folder123")

    # List should be called only once
    assert mock_files.list.call_count == 1


def test_get_random_photo(drive_service):
    with patch.object(
        DriveService, "list_files", return_value=[{"id": "1"}, {"id": "2"}]
    ):
        photo = drive_service.get_random_photo("folder")
        assert photo["id"] in ["1", "2"]


def test_download_file_success(drive_service):
    with patch("services.drive_service.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raw = "stream"
        mock_get.return_value = mock_resp

        # Mock valid creds
        drive_service.creds.valid = True
        drive_service.creds.token = "token"

        result = drive_service.download_file("file1")
        assert result == "stream"
        mock_get.assert_called_with(
            "https://www.googleapis.com/drive/v3/files/file1?alt=media",
            headers={"Authorization": "Bearer token"},
            stream=True,
        )


def test_download_file_error(drive_service):
    with patch("services.drive_service.requests.get") as mock_get:
        mock_get.side_effect = Exception("Download failed")
        with pytest.raises(Exception):
            drive_service.download_file("missing")
