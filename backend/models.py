from pydantic import BaseModel


class Emotion(BaseModel):
    id: str
    label: str  # Italian label
    color: str  # Hex color for UI


class DrawResponse(BaseModel):
    photo_url: str
    caption: str
    emotion_id: str
