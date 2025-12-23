from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import random
from dotenv import load_dotenv

from models import Emotion, DrawResponse
from services.drive_service import DriveService

load_dotenv()

app = FastAPI(title="NanettApp API")

# Configuration
APP_PASSWORD = os.getenv("APP_PASSWORD", "secret")
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-secret")
DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
drive_service: Optional[DriveService] = None
try:
    drive_service = DriveService()
except ValueError as e:
    print(f"Warning: DriveService not initialized: {e}")
    drive_service = None

# Data
EMOTIONS = [
    Emotion(id="happy", label="Felice", color="#FFD700"),  # Gold
    Emotion(id="romantic", label="Romantica", color="#FF69B4"),  # HotPink
    Emotion(id="sad", label="Triste", color="#87CEEB"),  # SkyBlue
    Emotion(id="angry", label="Arrabbiata", color="#FF4500"),  # OrangeRed
]

CAPTIONS = {
    "happy": [
        "🎵 Happy happy happy 🎵",
        "Sorridi sempre così!",
        "Puzzi!",
        "Che bello vederti felice!",
        "Sciau belishima!",
    ],
    "romantic": [
        "TATAIIII",
        "Sciau nana ❤️",
        "Abrazo 🫂",
        "Grattini!",
        "Cucchiaiami",
    ],
    "sad": [
        "Passerà...",
        "Ti meriti un abbraccio.",
        "Ricorda i momenti belli.",
        "Sono qui per te.",
        "Dopo la pioggia esce sempre il sole.",
        "Ti mando un basho grande.",
    ],
    "angry": [
        "Respira...",
        "Calma e sangue freddo.",
        "Non ne vale la pena.",
        "Conta fino a dieci...",
        "Fai un bel respiro profondo.",
        "Avvia la macchina degli sganassoni",
    ],
}


# Auth Models
class LoginRequest(BaseModel):
    password: str


# Dependencies
def check_auth(request: Request):
    token = request.cookies.get("auth_token")
    if not token or token != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    return True


@app.post("/api/login")
def login(login_req: LoginRequest, response: Response):
    if login_req.password == APP_PASSWORD:
        response.set_cookie(
            key="auth_token",
            value=SECRET_KEY,
            httponly=True,
            max_age=60 * 60 * 24 * 30,
            samesite="lax",
            secure=False,  # Set True in production
        )
        return {"status": "success"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )


@app.get("/api/check-auth")
def check_auth_status(request: Request):
    try:
        check_auth(request)
        return {"authenticated": True}
    except HTTPException:
        return {"authenticated": False}


@app.get("/api/logout")
def logout(response: Response):
    response.delete_cookie("auth_token")
    return {"status": "success"}


@app.get("/api/emotions", response_model=List[Emotion])
def get_emotions(authorized: bool = Depends(check_auth)):
    return EMOTIONS


@app.get("/api/draw/{emotion_id}", response_model=DrawResponse)
def draw_photo(emotion_id: str, authorized: bool = Depends(check_auth)):
    if emotion_id not in CAPTIONS:
        raise HTTPException(status_code=404, detail="Emotion not found")

    if not drive_service:
        raise HTTPException(status_code=503, detail="Drive service unavailable")

    # 1. Map emotion to folder? No, we filter by name?
    # Logic: We have one folder. We just pick a random photo.
    # Ideally we'd have subfolders or metadata.
    # For now: Just random photo from the single folder.

    if not DRIVE_FOLDER_ID:
        # Graceful handling for dev/test without config
        return DrawResponse(
            photo_url="",
            caption=random.choice(CAPTIONS[emotion_id]),
            emotion_id=emotion_id,
        )

    try:
        photo = drive_service.get_random_photo(DRIVE_FOLDER_ID)
    except Exception as e:
        print(f"Drive Error: {e}")
        photo = None

    caption = random.choice(CAPTIONS[emotion_id])

    # Proxy URL
    # Assuming the photo dict has 'id'
    final_url = f"/api/image/{photo['id']}" if photo else ""

    return DrawResponse(photo_url=final_url, caption=caption, emotion_id=emotion_id)


@app.get("/api/image/{file_id}")
def proxy_image(file_id: str, authorized: bool = Depends(check_auth)):
    if not drive_service:
        raise HTTPException(status_code=503, detail="Drive service unavailable")
    try:
        file_stream, media_type = drive_service.get_file_content(file_id)
        return StreamingResponse(file_stream, media_type=media_type)
    except Exception as e:
        print(f"Proxy Error: {e}")
        raise HTTPException(status_code=404, detail="Image not found")


# Mount assets/static files
# Vite builds to 'dist', and our Dockerfile copies 'frontend/dist' to 'backend/static'
if os.path.isdir("static"):
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
    # Also mount other top-level files like favicon.ico if they exist in static
    # But for SPA, we mainly need to serve index.html for unknown routes


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    # If not found in API or static assets, serve index.html
    if os.path.exists("static/index.html"):
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return Response(content="Frontend not found", status_code=404)
