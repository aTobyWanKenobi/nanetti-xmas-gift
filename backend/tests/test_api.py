from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app, SECRET_KEY, APP_PASSWORD

client = TestClient(app)


def test_login_success():
    resp = client.post("/api/login", json={"password": APP_PASSWORD})
    assert resp.status_code == 200
    assert "auth_token" in resp.cookies
    assert resp.cookies["auth_token"] == SECRET_KEY


def test_login_failure():
    resp = client.post("/api/login", json={"password": "wrong"})
    assert resp.status_code == 401


def test_check_auth_unauthorized():
    client.cookies.clear()
    resp = client.get("/api/check-auth")
    assert not resp.json()["authenticated"]


def test_check_auth_authorized():
    client.cookies.set("auth_token", SECRET_KEY)
    resp = client.get("/api/check-auth")
    assert resp.json()["authenticated"]


def test_get_emotions_unauthorized():
    client.cookies.clear()
    resp = client.get("/api/emotions")
    assert resp.status_code == 401


def test_get_emotions_success():
    client.cookies.set("auth_token", SECRET_KEY)
    resp = client.get("/api/emotions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4
    assert data[0]["label"] == "Felice"


@patch("main.drive_service")
def test_draw_photo_success(mock_drive_service):
    client.cookies.set("auth_token", SECRET_KEY)

    mock_drive_service.get_random_photo.return_value = {
        "id": "photo123",
        "webContentLink": "http://link",
    }

    # Mock Env var for folder ID to avoid "None" check if test env differs
    with patch("main.DRIVE_FOLDER_ID", "folder123"):
        resp = client.get("/api/draw/happy")

    assert resp.status_code == 200
    data = resp.json()
    assert data["emotion_id"] == "happy"
    assert data["photo_url"] == "/api/image/photo123"
    assert "caption" in data


def test_draw_photo_invalid_emotion():
    client.cookies.set("auth_token", SECRET_KEY)
    resp = client.get("/api/draw/invalid")
    assert resp.status_code == 404


@patch("main.drive_service")
def test_proxy_image_success(mock_drive_service):
    client.cookies.set("auth_token", SECRET_KEY)
    # Mock return value as BytesIO
    import io

    mock_drive_service.get_file_content.return_value = (
        io.BytesIO(b"image data"),
        "image/jpeg",
    )

    resp = client.get("/api/image/file123")
    assert resp.status_code == 200
    assert resp.content == b"image data"
    assert resp.headers["content-type"] == "image/jpeg"
