from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class VideoRequest(BaseModel):
    url: str

@app.post("/api/extract")
async def extract_video_info(request: VideoRequest):
    ydl_options = {
        # Omit 'format' so yt-dlp returns all extracted stream metadata
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'cookiefile': './cookies.txt',
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'web_embedded', 'mweb'],
            },
            'tiktok': {
                'app_version': '20.2.1',
                'manifest_app_version': '20.2.1'
            }
        },
        'no_color': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
            download_url = info.get("url")
            
            # If a single direct URL isn't populated, find the best progressive (video+audio) format
            if not download_url and info.get("formats"):
                # 1. Prefer formats that have BOTH video and audio in a single stream
                progressive_formats = [
                    f for f in info["formats"]
                    if f.get("vcodec") != "none" 
                    and f.get("acodec") != "none" 
                    and f.get("url")
                ]
                
                if progressive_formats:
                    # Sort by resolution/height/tbr if available
                    download_url = progressive_formats[-1].get("url")
                else:
                    # 2. Fallback to the highest bitrate video-only or generic stream
                    valid_formats = [f for f in info["formats"] if f.get("url")]
                    if valid_formats:
                        download_url = valid_formats[-1].get("url")

            if not download_url:
                raise Exception("Could not extract a direct playable URL")

            return {
                "extractor": info.get("extractor_key"),
                "title": info.get("title", "Social Video"),
                "thumbnail": info.get("thumbnail"),
                "download_url": download_url,
                "duration": info.get("duration")
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process link: {str(e)}")

    