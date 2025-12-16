from models import Emotion, DrawResponse
import pytest
from pydantic import ValidationError


def test_emotion_model():
    emotion = Emotion(id="test", label="Test", color="#000000")
    assert emotion.id == "test"
    assert emotion.label == "Test"
    assert emotion.color == "#000000"


def test_emotion_model_invalid_type():
    with pytest.raises(ValidationError):
        Emotion(id="test", label="Test")  # type: ignore # Missing color


def test_draw_response_model():
    resp = DrawResponse(photo_url="http://url", caption="Hello", emotion_id="happy")
    assert resp.photo_url == "http://url"
    assert resp.caption == "Hello"


def test_draw_response_model_invalid_type():
    with pytest.raises(ValidationError):
        DrawResponse(photo_url=123, caption="Hello", emotion_id="happy")  # type: ignore
        # The original comment was: # URL should be str
