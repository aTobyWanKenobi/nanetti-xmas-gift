import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Set mock environment variables for all tests."""
    monkeypatch.setenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        '{"type": "service_account", "project_id": "test"}',
    )
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "folder123")
    monkeypatch.setenv("APP_PASSWORD", "secret")
    monkeypatch.setenv("SECRET_KEY", "testsecret")


@pytest.fixture(autouse=True)
def mock_google_auth(monkeypatch):
    """Mock Google Auth to avoid real API calls during import."""
    # We need to mock build() and Credentials to prevent network calls
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "google.oauth2.service_account.Credentials.from_service_account_info",
            MagicMock(),
        )
        m.setattr("googleapiclient.discovery.build", MagicMock())
        yield
