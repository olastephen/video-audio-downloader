#!/usr/bin/env python3
"""
Enhanced Video Downloader with Multiple Libraries
Uses yt-dlp, pytube, youtube-dl, and custom extractors for maximum compatibility
"""

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, parse_qs
import json

# Import multiple download libraries
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

try:
    from pytube import YouTube
    PYTUBE_AVAILABLE = True
except ImportError:
    PYTUBE_AVAILABLE = False

try:
    import youtube_dl
    YOUTUBE_DL_AVAILABLE = True
except ImportError:
    YOUTUBE_DL_AVAILABLE = False

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class EnhancedVideoDownloader:
    """Enhanced video downloader using multiple libraries and methods"""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Initialize scrapers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        if CLOUDSCRAPER_AVAILABLE:
            self.cloud_scraper = cloudscraper.create_scraper()
        else:
            self.cloud_scraper = None
    
    def _progress_hook(self, d):
        """Progress hook for downloads"""
        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    progress = (downloaded / total) * 100
                    logger.info(f"Download progress: {progress:.1f}% ({downloaded}/{total} bytes)")
                else:
                    logger.info(f"Downloaded: {downloaded} bytes")
            except Exception as e:
                logger.debug(f"Progress hook error: {e}")
        elif d['status'] == 'finished':
            logger.info(f"Download finished: {d.get('filename', 'unknown')}")

    def detect_platform(self, url: str) -> str:
        """Detect the platform from URL"""
        url_lower = url.lower()
        
        # Direct video files
        if any(ext in url_lower for ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp']):
            return 'direct_video'
        
        # Social media platforms
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'vimeo.com' in url_lower:
            return 'vimeo'
        elif 'dailymotion.com' in url_lower:
            return 'dailymotion'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        elif 'reddit.com' in url_lower:
            return 'reddit'
        elif 'twitch.tv' in url_lower:
            return 'twitch'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'facebook.com' in url_lower:
            return 'facebook'
        
        # Known video platforms
        elif any(site in url_lower for site in ['bilibili', 'nicovideo', 'rutube', 'vk.com', 'ok.ru']):
            return 'generic_video'
        
        # If it's a web URL but not a known platform, treat as generic
        elif url_lower.startswith(('http://', 'https://')):
            return 'generic_video'
        
        return 'unknown'
    
    def get_yt_dlp_opts(self, quality: str = "best", format: str = "mp4", 
                       audio_only: bool = False, progress_hook=None) -> Dict[str, Any]:
        """Get yt-dlp options with enhanced settings"""
        opts = {
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'noplaylist': True,
            'ignoreerrors': False,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'extractor_retries': 5,
            'fragment_retries': 5,
            'retries': 5,
            'socket_timeout': 30,
            'extractor_timeout': 60,
            'http_chunk_size': 10485760,  # 10MB chunks
            'buffersize': 1024,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        if progress_hook:
            opts['progress_hooks'] = [progress_hook]
        
        if audio_only:
            opts.update({
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            if quality == "best":
                opts['format'] = f'best[ext={format}]/best'
            elif quality == "worst":
                opts['format'] = f'worst[ext={format}]/worst'
            else:
                opts['format'] = quality
        
        return opts
    
    def download_with_yt_dlp(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False) -> str:
        """Download using yt-dlp with enhanced options"""
        logger.info(f"Attempting yt-dlp download from: {url}")
        
        ydl_opts = self.get_yt_dlp_opts(quality, format, audio_only)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Starting yt-dlp download...")
                ydl.download([url])
                
                # Get the downloaded file
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'unknown_title')
                ext = info.get('ext', format or 'mp4')
                filename = f"{title}.{ext}"
                filepath = self.download_dir / filename
                
                if filepath.exists():
                    logger.info(f"Successfully downloaded with yt-dlp: {filename}")
                    return str(filepath)
                else:
                    raise Exception(f"Download completed but file not found: {filename}")
                    
        except Exception as e:
            logger.error(f"yt-dlp download failed: {e}")
            raise

    def download_with_pytube(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False) -> str:
        """Download using pytube (YouTube only)"""
        logger.info(f"Attempting pytube download from: {url}")
        
        try:
            from pytube import YouTube
            
            yt = YouTube(url)
            
            if audio_only:
                stream = yt.streams.filter(only_audio=True).first()
            else:
                if quality == "best":
                    stream = yt.streams.filter(progressive=True, file_extension=format).get_highest_resolution()
                else:
                    stream = yt.streams.filter(progressive=True, file_extension=format).first()
            
            if not stream:
                raise Exception("No suitable stream found")
            
            filename = f"{yt.title}.{stream.subtype}"
            filepath = self.download_dir / filename
            
            stream.download(output_path=str(self.download_dir), filename=filename)
            
            if filepath.exists():
                logger.info(f"Successfully downloaded with pytube: {filename}")
                return str(filepath)
            else:
                raise Exception(f"Download completed but file not found: {filename}")
                
        except Exception as e:
            logger.error(f"pytube download failed: {e}")
            raise
    
    def download_with_youtube_dl(self, url: str, quality: str = "best", 
                               format: str = "mp4", audio_only: bool = False) -> Tuple[bool, str, str]:
        """Download using youtube-dl (legacy but sometimes works when yt-dlp fails)"""
        if not YOUTUBE_DL_AVAILABLE:
            return False, "youtube-dl not available", ""
        
        try:
            opts = {
                'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
                'format': 'bestaudio' if audio_only else f'best[ext={format}]/best',
                'noplaylist': True,
                'ignoreerrors': False,
            }
            
            if audio_only:
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }]
            
            with youtube_dl.YoutubeDL(opts) as ydl:
                ydl.download([url])
                
                # Try to find the downloaded file
                info = ydl.extract_info(url, download=False)
                if info:
                    title = info.get('title', 'video')
                    ext = 'mp3' if audio_only else format
                    filename = f"{title}.{ext}"
                    filepath = self.download_dir / filename
                    
                    if filepath.exists():
                        return True, "Download completed successfully", str(filepath)
                
                return False, "Download completed but file not found", ""
                
        except Exception as e:
            logger.error(f"youtube-dl download error: {e}")
            return False, f"youtube-dl error: {str(e)}", ""
    
    def extract_direct_url(self, url: str) -> Tuple[bool, str, str]:
        """Try to extract direct video URL using web scraping"""
        try:
            # Use cloudscraper if available
            if self.cloud_scraper:
                response = self.cloud_scraper.get(url)
            else:
                response = self.session.get(url)
            
            if response.status_code != 200:
                return False, f"HTTP {response.status_code}", ""
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for video sources
            video_sources = []
            
            # Check for video tags
            for video in soup.find_all('video'):
                for source in video.find_all('source'):
                    src = source.get('src')
                    if src:
                        video_sources.append(src)
            
            # Check for meta tags
            for meta in soup.find_all('meta', property='og:video'):
                content = meta.get('content')
                if content:
                    video_sources.append(content)
            
            # Check for JSON-LD structured data
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'contentUrl' in data:
                        video_sources.append(data['contentUrl'])
                except:
                    continue
            
            if video_sources:
                # Try to download the first video source
                video_url = video_sources[0]
                if not video_url.startswith('http'):
                    # Handle relative URLs
                    parsed = urlparse(url)
                    video_url = f"{parsed.scheme}://{parsed.netloc}{video_url}"
                
                # Download the video
                filename = f"direct_video_{int(time.time())}.mp4"
                filepath = self.download_dir / filename
                
                response = self.session.get(video_url, stream=True)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    return True, "Direct download completed", str(filepath)
            
            return False, "No direct video URL found", ""
            
        except Exception as e:
            logger.error(f"Direct URL extraction error: {e}")
            return False, f"Direct extraction error: {str(e)}", ""
    
    def download_direct_video(self, url: str) -> str:
        """Download direct video files"""
        logger.info(f"Attempting direct video download from: {url}")
        
        try:
            import requests
            from urllib.parse import urlparse
            
            # Get filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            if not filename or '.' not in filename:
                # Try to get filename from Content-Disposition header
                response = requests.head(url, allow_redirects=True)
                content_disposition = response.headers.get('content-disposition', '')
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')
                else:
                    filename = f"video_{int(time.time())}.mp4"
            
            filepath = self.download_dir / filename
            
            # Download with progress
            response = requests.get(url, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Download progress: {progress:.1f}%")
            
            if filepath.exists():
                logger.info(f"Successfully downloaded direct video: {filename}")
                return str(filepath)
            else:
                raise Exception(f"Download completed but file not found: {filename}")
                
        except Exception as e:
            logger.error(f"Direct video download failed: {e}")
            raise
    
    def download_generic_video(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False) -> str:
        """Generic video downloader for unknown platforms"""
        logger.info(f"Attempting generic video download from: {url}")
        
        # Enhanced yt-dlp options for generic sites
        ydl_opts = {
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'format': f'best[ext={format}]/best' if format else 'best',
            'noplaylist': True,
            'ignoreerrors': False,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_retries': 5,
            'fragment_retries': 5,
            'retries': 5,
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            # Enhanced headers for generic sites
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            },
            # Force generic extractor for unknown sites
            'force_generic_extractor': True,
            # Additional options for streaming sites
            'extractor_args': {
                'generic': {
                    'skip': ['dash', 'live']
                }
            }
        }
        
        if audio_only:
            ydl_opts.update({
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Starting generic video download with enhanced options...")
                
                # First, try to extract info to see what we're dealing with
                try:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Extracted info: {info.get('title', 'Unknown')} - {info.get('duration', 'Unknown duration')}")
                    
                    # Check if we got actual video info
                    if not info.get('formats'):
                        logger.warning("No video formats found, this might be a protected site")
                        raise Exception("No video formats available")
                        
                except Exception as e:
                    logger.warning(f"Could not extract video info: {e}")
                    # Continue with download attempt anyway
                
                # Attempt download
                ydl.download([url])
                
                # Get the downloaded file
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'unknown_title')
                ext = info.get('ext', format or 'mp4')
                filename = f"{title}.{ext}"
                filepath = self.download_dir / filename
                
                if filepath.exists():
                    # Check file size to ensure it's actually a video
                    file_size = filepath.stat().st_size
                    if file_size < 100000:  # Less than 100KB is suspicious
                        logger.warning(f"Downloaded file is very small ({file_size} bytes), might be an error page")
                        # Try to read the file to see if it's HTML
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read(1000)  # Read first 1000 chars
                                if '<html' in content.lower() or '<!doctype' in content.lower():
                                    logger.error(f"Downloaded file appears to be HTML, not a video: {filepath}")
                                    filepath.unlink()  # Delete the file
                                    raise Exception("Downloaded HTML instead of video - site may require authentication or be protected")
                        except UnicodeDecodeError:
                            # File is binary, might be a small video or error
                            if file_size < 50000:  # Very small binary file
                                logger.error(f"Downloaded file is too small ({file_size} bytes) to be a valid video: {filepath}")
                                filepath.unlink()
                                raise Exception("Downloaded file is too small to be a valid video")
                    
                    logger.info(f"Successfully downloaded generic video: {filename} ({file_size} bytes)")
                    return str(filepath)
                else:
                    raise Exception(f"Download completed but file not found: {filename}")
                    
        except Exception as e:
            logger.error(f"Generic video download failed: {e}")
            raise

    def download_video(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False) -> str:
        """Download video using multiple methods with fallback"""
        platform = self.detect_platform(url)
        logger.info(f"Detected platform: {platform} for URL: {url}")
        
        # Method 1: Direct video download (only for actual video files)
        if platform == 'direct_video':
            try:
                logger.info("Attempting direct video download...")
                return self.download_direct_video(url)
            except Exception as e:
                logger.warning(f"Direct video download failed: {e}")
        
        # Method 2: yt-dlp with enhanced options
        try:
            logger.info("Attempting download with yt-dlp...")
            return self.download_with_yt_dlp(url, quality, format, audio_only)
        except Exception as e:
            logger.warning(f"yt-dlp download failed: {e}")
        
        # Method 3: pytube (for YouTube)
        if platform == 'youtube':
            try:
                logger.info("Attempting download with pytube...")
                return self.download_with_pytube(url, quality, format, audio_only)
            except Exception as e:
                logger.warning(f"pytube download failed: {e}")
        
        # Method 4: Generic downloader for unknown platforms
        if platform == 'unknown' or platform == 'generic_video':
            try:
                logger.info("Attempting generic video download...")
                return self.download_generic_video(url, quality, format, audio_only)
            except Exception as e:
                logger.warning(f"Generic video download failed: {e}")
        
        # Method 5: Direct video as last resort (only for non-HTML URLs)
        if not any(html_indicator in url.lower() for html_indicator in ['html', 'htm', 'php', 'asp', 'jsp']):
            try:
                logger.info("Attempting direct video download as last resort...")
                return self.download_direct_video(url)
            except Exception as e:
                logger.warning(f"Direct video fallback failed: {e}")
        
        # If all methods fail
        raise Exception(f"All download methods failed for URL: {url}")
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video information without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "title": info.get('title'),
                    "duration": info.get('duration'),
                    "uploader": info.get('uploader'),
                    "upload_date": info.get('upload_date'),
                    "view_count": info.get('view_count'),
                    "like_count": info.get('like_count'),
                    "formats": [
                        {
                            "format_id": f.get('format_id'),
                            "ext": f.get('ext'),
                            "resolution": f.get('resolution'),
                            "filesize": f.get('filesize'),
                            "vcodec": f.get('vcodec'),
                            "acodec": f.get('acodec'),
                        }
                        for f in info.get('formats', [])
                    ],
                    "extractor": info.get('extractor', 'enhanced')
                }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            raise 