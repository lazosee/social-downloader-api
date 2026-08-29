from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from urllib.parse import unquote
import yt_dlp
import httpx


BASE_URL = "https://social-downloader-api-6pv6.onrender.com"

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


@app.get("/health")
async def health_check():
    return { "status": "healthy", "uptime": "active" }


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



@app.get("/api/stream")
async def proxy_stream(url: str):
    decoded_url = unquote(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
        "Accept": "*/*",
    }
    
    client = httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=60.0)
    req = client.build_request("GET", decoded_url)
    res = await client.send(req, stream=True)
    
    return StreamingResponse(
        res.aiter_raw(),
        status_code=res.status_code,
        headers={
            "Content-Type": res.headers.get("Content-Type", "video/mp4"),
            "Content-Length": res.headers.get("Content-Length", ""),
        },
        background=client.aclose
    )  