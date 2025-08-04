from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import yt_dlp
import os
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid
import logging
import time
from pathlib import Path
import requests
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration
try:
    from config import Config
    logger.info("Configuration loaded successfully")
except ImportError as e:
    logger.warning(f"Configuration not available: {e}")

# Lifespan context manager for startup/shutdown
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("Starting up Social Media Info Extractor API...")
    
    yield
    
    # Shutdown
    logger.info("Shutting down gracefully...")

app = FastAPI(
    title="Social Media Info Extractor API",
    description="Extract comprehensive metadata from social media posts",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SocialMediaRequest(BaseModel):
    url: HttpUrl
    include_media_urls: Optional[bool] = True
    include_thumbnail: Optional[bool] = True
    include_audio: Optional[bool] = False

class MediaInfo(BaseModel):
    url: str
    data_size: Optional[int] = None
    quality: Optional[str] = None
    extension: Optional[str] = None
    type: str
    duration: Optional[int] = None

class SocialMediaInfo(BaseModel):
    url: str
    source: str
    id: Optional[str] = None
    unique_id: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    upload_date: Optional[str] = None
    medias: List[MediaInfo] = []
    type: str = "single"
    error: bool = False
    error_message: Optional[str] = None
    time_end: Optional[int] = None

def detect_platform(url: str) -> str:
    """Detect the social media platform from URL"""
    url_lower = url.lower()
    
    if 'tiktok.com' in url_lower:
        return 'tiktok'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
        return 'facebook'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'reddit.com' in url_lower:
        return 'reddit'
    elif 'pinterest.com' in url_lower:
        return 'pinterest'
    elif 'snapchat.com' in url_lower:
        return 'snapchat'
    elif 'linkedin.com' in url_lower:
        return 'linkedin'
    elif 'twitch.tv' in url_lower:
        return 'twitch'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    elif 'dailymotion.com' in url_lower:
        return 'dailymotion'
    else:
        return 'unknown'

def extract_video_id(url: str, platform: str) -> Optional[str]:
    """Extract video ID from URL based on platform"""
    try:
        if platform == 'tiktok':
            # Extract from TikTok URL patterns
            if '/video/' in url:
                return url.split('/video/')[-1].split('?')[0]
            elif '@' in url and '/v/' in url:
                return url.split('/v/')[-1].split('?')[0]
        elif platform == 'youtube':
            # Extract from YouTube URL patterns
            if 'youtube.com/watch?v=' in url:
                return url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in url:
                return url.split('youtu.be/')[1].split('?')[0]
        elif platform == 'instagram':
            # Extract from Instagram URL patterns
            if '/p/' in url:
                return url.split('/p/')[1].split('/')[0]
            elif '/reel/' in url:
                return url.split('/reel/')[1].split('/')[0]
        elif platform == 'facebook':
            # Extract from Facebook URL patterns
            if '/videos/' in url:
                return url.split('/videos/')[1].split('/')[0]
        elif platform == 'twitter':
            # Extract from Twitter/X URL patterns
            if '/status/' in url:
                return url.split('/status/')[1].split('?')[0]
    except:
        pass
    return None

def extract_unique_id(url: str, platform: str) -> Optional[str]:
    """Extract unique user ID from URL based on platform"""
    try:
        if platform == 'tiktok':
            # Extract @username from TikTok
            if '@' in url:
                username = url.split('@')[1].split('/')[0]
                return username
        elif platform == 'youtube':
            # Extract channel ID from YouTube
            if '/channel/' in url:
                return url.split('/channel/')[1].split('/')[0]
            elif '/c/' in url:
                return url.split('/c/')[1].split('/')[0]
        elif platform == 'instagram':
            # Extract username from Instagram
            if '/' in url:
                parts = url.split('/')
                for i, part in enumerate(parts):
                    if part in ['p', 'reel'] and i + 1 < len(parts):
                        return parts[i - 1]  # Username is before /p/ or /reel/
    except:
        pass
    return None

def get_yt_dlp_opts(platform: str = None) -> Dict[str, Any]:
    """Get yt-dlp options for metadata extraction"""
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'writeinfojson': False,
        'writethumbnail': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'ignoreerrors': False,
        'no_check_certificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    }
    
    # Platform-specific options
    if platform == 'tiktok':
        base_opts.update({
            'extractor_args': {
                'tiktok': {
                    'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                    'app_version': '1.0.0',
                    'manifest_app_version': '1.0.0'
                }
            }
        })
    
    return base_opts

def categorize_media_format(format_info: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Categorize media format based on platform and format info"""
    media_info = {
        "url": format_info.get('url'),
        "data_size": format_info.get('filesize'),
        "quality": None,
        "extension": format_info.get('ext'),
        "type": "video",
        "duration": format_info.get('duration')
    }
    
    # Determine media type
    if format_info.get('vcodec') == 'none' and format_info.get('acodec') != 'none':
        media_info["type"] = "audio"
    elif format_info.get('vcodec') != 'none':
        media_info["type"] = "video"
    
    # Set quality based on platform and format
    if platform == 'tiktok':
        if media_info["type"] == "audio":
            media_info["quality"] = "audio"
        else:
            # Determine TikTok video quality based on bitrate and URL patterns
            bitrate = format_info.get('bitrate', 0)
            height = format_info.get('height', 0)
            url = format_info.get('url', '')
            
            # Check for specific URL patterns that indicate quality
            if 'euttp' in url and bitrate >= 900:
                media_info["quality"] = "hd_no_watermark"
            elif 'pve-0037-aiso' in url and bitrate >= 1800:
                media_info["quality"] = "no_watermark"
            elif 'pve-0037-aiso' in url and bitrate < 1800:
                media_info["quality"] = "watermark"
            elif height >= 1080:
                media_info["quality"] = "hd_no_watermark"
            elif height >= 720:
                media_info["quality"] = "no_watermark"
            else:
                media_info["quality"] = "watermark"
    elif platform == 'youtube':
        if media_info["type"] == "audio":
            media_info["quality"] = "audio"
        else:
            height = format_info.get('height', 0)
            if height >= 1080:
                media_info["quality"] = "1080p"
            elif height >= 720:
                media_info["quality"] = "720p"
            elif height >= 480:
                media_info["quality"] = "480p"
            else:
                media_info["quality"] = "360p"
    else:
        # Generic quality detection
        height = format_info.get('height', 0)
        if media_info["type"] == "audio":
            media_info["quality"] = "audio"
        elif height >= 1080:
            media_info["quality"] = "hd"
        elif height >= 720:
            media_info["quality"] = "hd"
        elif height >= 480:
            media_info["quality"] = "sd"
        else:
            media_info["quality"] = "low"
    
    return media_info

async def extract_tiktok_cdn_direct(url: str) -> Optional[Dict[str, Any]]:
    """Direct TikTok CDN extraction using alternative methods"""
    try:
        video_id = extract_video_id(url, 'tiktok')
        unique_id = extract_unique_id(url, 'tiktok')
        
        # Method 1: Try TikTok API directly
        api_url = f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('aweme_list') and len(data['aweme_list']) > 0:
                    aweme = data['aweme_list'][0]
                    return {
                        'uploader': aweme.get('author', {}).get('unique_id', unique_id),
                        'title': aweme.get('desc', f'TikTok Video {video_id}'),
                        'description': aweme.get('desc', ''),
                        'duration': aweme.get('video', {}).get('duration', 0) * 1000,  # Convert to milliseconds
                        'view_count': aweme.get('statistics', {}).get('play_count', 0),
                        'upload_date': aweme.get('create_time', 0),
                        'thumbnail': aweme.get('video', {}).get('cover', {}).get('url_list', [''])[0],
                        'formats': []
                    }
            except:
                pass
        
        # Method 2: Try with different API endpoint
        api_url2 = f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/play/?video_id={video_id}"
        response2 = requests.get(api_url2, headers=headers, timeout=10)
        if response2.status_code == 200:
            # This might give us direct video URLs
            pass
        
        # Method 3: Try TikTok-specific libraries
        try:
            # Try tiktok-api library
            from tiktok_api import TikTokApi
            api = TikTokApi()
            video_data = api.get_video_by_url(url)
            if video_data:
                return {
                    'uploader': video_data.get('author', {}).get('unique_id', unique_id),
                    'title': video_data.get('desc', f'TikTok Video {video_id}'),
                    'description': video_data.get('desc', ''),
                    'duration': video_data.get('video', {}).get('duration', 0),
                    'view_count': video_data.get('statistics', {}).get('play_count', 0),
                    'upload_date': video_data.get('create_time', 0),
                    'thumbnail': video_data.get('video', {}).get('cover', {}).get('url_list', [''])[0],
                    'formats': []
                }
        except ImportError:
            logger.warning("tiktok-api library not available")
        except Exception as e:
            logger.warning(f"tiktok-api extraction failed: {e}")
        
        # Method 4: Try tiktok-downloader library
        try:
            from tiktok_downloader import TikTokDownloader
            downloader = TikTokDownloader()
            video_info = downloader.get_video_info(url)
            if video_info:
                return {
                    'uploader': video_info.get('author', unique_id),
                    'title': video_info.get('title', f'TikTok Video {video_id}'),
                    'description': video_info.get('description', ''),
                    'duration': video_info.get('duration', 0),
                    'view_count': video_info.get('view_count', 0),
                    'upload_date': video_info.get('upload_date', 0),
                    'thumbnail': video_info.get('thumbnail', ''),
                    'formats': video_info.get('formats', [])
                }
        except ImportError:
            logger.warning("tiktok-downloader library not available")
        except Exception as e:
            logger.warning(f"tiktok-downloader extraction failed: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"Direct TikTok CDN extraction failed: {e}")
        return None

async def extract_tiktok_info_direct(url: str) -> Optional[Dict[str, Any]]:
    """Direct TikTok extraction using alternative methods"""
    try:
        # Try direct CDN extraction first
        info = await extract_tiktok_cdn_direct(url)
        if info:
            return info
        
        # Method 1: Try with updated yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'ignoreerrors': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info and not info.get('_type') == 'playlist':
                    return info
            except Exception as e:
                logger.warning(f"Direct TikTok extraction failed: {e}")
        
        # Method 2: Try with different extractor
        ydl_opts.update({
            'extractor_args': {
                'tiktok': {
                    'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                    'app_version': '1.0.0',
                    'manifest_app_version': '1.0.0'
                }
            }
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info and not info.get('_type') == 'playlist':
                    return info
            except Exception as e:
                logger.warning(f"TikTok with extractor args failed: {e}")
        
        # Method 3: Try with cookies
        ydl_opts.update({
            'cookiesfrombrowser': ('chrome',),
            'extract_flat': False
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info and not info.get('_type') == 'playlist':
                    return info
            except Exception as e:
                logger.warning(f"TikTok with cookies failed: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"All TikTok extraction methods failed: {e}")
        return None

async def extract_tiktok_info(url: str) -> Optional[Dict[str, Any]]:
    """Specialized TikTok extraction to bypass sigi state issues"""
    try:
        # Try direct extraction first
        info = await extract_tiktok_info_direct(url)
        if info:
            return info
        
        # Fallback: Try with standard yt-dlp but with different options
        ydl_opts = get_yt_dlp_opts('tiktok')
        ydl_opts.update({
            'extract_flat': True,
            'ignoreerrors': True,
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info and not info.get('_type') == 'playlist':
                    return info
            except Exception as e:
                logger.warning(f"Flat extraction failed: {e}")
        
        # Try with different user agent
        ydl_opts = get_yt_dlp_opts('tiktok')
        ydl_opts['http_headers']['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info and not info.get('_type') == 'playlist':
                    return info
            except Exception as e:
                logger.warning(f"Mobile user agent extraction failed: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"TikTok extraction failed: {e}")
        return None

async def extract_social_media_info(url: str, include_media_urls: bool = True, include_thumbnail: bool = True, include_audio: bool = False) -> Dict[str, Any]:
    """Extract comprehensive information from social media URL"""
    start_time = time.time()
    
    try:
        # Detect platform
        platform = detect_platform(url)
        video_id = extract_video_id(url, platform)
        unique_id = extract_unique_id(url, platform)
        
        # Initialize result
        result = {
            "url": url,
            "source": platform,
            "id": video_id,
            "unique_id": unique_id,
            "author": None,
            "title": None,
            "description": None,
            "thumbnail": None,
            "duration": None,
            "view_count": None,
            "like_count": None,
            "comment_count": None,
            "share_count": None,
            "upload_date": None,
            "medias": [],
            "type": "single",
            "error": False,
            "error_message": None,
            "time_end": None
        }
        
        # Platform-specific extraction
        if platform == 'tiktok':
            info = await extract_tiktok_info(url)
        else:
            # Use standard yt-dlp for other platforms
            ydl_opts = get_yt_dlp_opts(platform)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    info = None
                    result["error"] = True
                    result["error_message"] = str(e)
                    logger.error(f"Error extracting info from {url}: {e}")
        
        if info and not result["error"]:
            # Basic information
            result["author"] = info.get('uploader')
            result["title"] = info.get('title')
            result["description"] = info.get('description')
            result["duration"] = info.get('duration')
            result["view_count"] = info.get('view_count')
            result["upload_date"] = info.get('upload_date')
            
            # Thumbnail
            if include_thumbnail and info.get('thumbnail'):
                result["thumbnail"] = info.get('thumbnail')
            
            # Media formats
            if include_media_urls and info.get('formats'):
                formats = info.get('formats', [])
                
                for format_info in formats:
                    media_info = categorize_media_format(format_info, platform)
                    
                    # Filter based on preferences
                    if not include_audio and media_info["type"] == "audio":
                        continue
                        
                    result["medias"].append(media_info)
            
            # Handle playlists
            if info.get('_type') == 'playlist':
                result["type"] = "playlist"
                result["medias"] = []  # Don't include media for playlists
            elif len(result["medias"]) > 1:
                result["type"] = "multiple"
        else:
            result["error"] = True
            result["error_message"] = "Failed to extract information from the URL"
        
        # Calculate time_end (extraction time in milliseconds)
        extraction_time = time.time() - start_time
        result["time_end"] = int(extraction_time * 1000)  # Convert to milliseconds
        
        return result
        
    except Exception as e:
        result = {
            "url": url,
            "source": detect_platform(url),
            "error": True,
            "error_message": str(e),
            "time_end": int((time.time() - start_time) * 1000)
        }
        logger.error(f"Error processing {url}: {e}")
        return result

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Social Media Info Extractor API",
        "version": "2.0.0",
        "description": "Extract comprehensive metadata from social media posts",
        "supported_platforms": [
            "tiktok", "youtube", "instagram", "facebook", 
            "twitter", "reddit", "pinterest", "snapchat", 
            "linkedin", "twitch", "vimeo", "dailymotion"
        ],
        "endpoints": {
            "extract": "/extract",
            "health": "/health",
            "supported_platforms": "/platforms"
        }
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

@app.get("/platforms")
async def get_supported_platforms():
    """Get list of supported platforms"""
    return {
        "platforms": [
            {
                "name": "TikTok",
                "id": "tiktok",
                "url_patterns": ["tiktok.com/@username/video/", "tiktok.com/v/"],
                "features": ["video", "audio", "thumbnail", "metadata"]
            },
            {
                "name": "YouTube",
                "id": "youtube", 
                "url_patterns": ["youtube.com/watch?v=", "youtu.be/"],
                "features": ["video", "audio", "thumbnail", "metadata"]
            },
            {
                "name": "Instagram",
                "id": "instagram",
                "url_patterns": ["instagram.com/p/", "instagram.com/reel/"],
                "features": ["video", "image", "thumbnail", "metadata"]
            },
            {
                "name": "Facebook",
                "id": "facebook",
                "url_patterns": ["facebook.com/videos/"],
                "features": ["video", "thumbnail", "metadata"]
            },
            {
                "name": "Twitter/X",
                "id": "twitter",
                "url_patterns": ["twitter.com/status/", "x.com/status/"],
                "features": ["video", "image", "metadata"]
            }
        ]
    }

@app.post("/extract")
async def extract_info(request: SocialMediaRequest):
    """Extract comprehensive information from social media URL"""
    try:
        url = str(request.url)
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Extract information
        result = await extract_social_media_info(
            url, 
            include_media_urls=request.include_media_urls,
            include_thumbnail=request.include_thumbnail,
            include_audio=request.include_audio
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in extract endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.API_HOST, port=Config.API_PORT) 