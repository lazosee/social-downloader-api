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
    print(request)
    # Advanced options to bypass TikTok/Instagram bot detection
    ydl_options = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False, # Ensures we get actual video file, not just a link to the post
        'cookiefile': './cookies.txt',
        'extractor_args': {
            'youtube': {
                'player_cient': ['web_embedded', 'web', 'tv'], # Bypasses iOS/Android blocks
                'player_skip': ['webpage', 'configs'],
                'skip': ['dash', 'hls']
            },
            'tiktok': {
                'app_version': '20.2.1',
                'manifest_app_version': '20.2.1'
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
            'Referer': 'https://www.tiktok.com/',
        },
        # Automatically updates cookies/sessions for tough platforms if needed
        'no_color': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(request.url, download=False)

            # TikTok/Instagram often put the direct mp4 url inside an array of formats
            # If the top-level 'url' is missing, grab the best formart URL
            download_url = info.get("url")
            if not download_url and info.get("formats"):
                # Sort formats to find the best quality video that includes audio
                formats = [f for f in info["formats"] if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("url")]
                if formats:
                    download_url = formats[-1].get("url")
                else:
                    download_url = info["formats"][-1].get("url")

            if not download_url:
                raise Exception("Could not extract direct download URL")

            return {
                "extractor": info.get("extractor_key"), # e.g., "TikTok", "Instagram"
                "title": info.get("title", "Social Video"),
                "thumbnail": info.get("thumbnail"),
                "download_url": download_url,
                "duration": info.get("duration")
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process link: {str(e)}")

