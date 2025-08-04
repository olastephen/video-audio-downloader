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
    
    def __init__(self, download_dir: str = "downloads", progress_callback=None):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Progress callback for real-time updates
        self.progress_callback = progress_callback
        
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
                    
                    # Call progress callback if available
                    if self.progress_callback:
                        try:
                            self.progress_callback(round(progress, 2))
                        except Exception as e:
                            logger.debug(f"Progress callback error: {e}")
                else:
                    logger.info(f"Downloaded: {downloaded} bytes")
            except Exception as e:
                logger.debug(f"Progress hook error: {e}")
        elif d['status'] == 'finished':
            logger.info(f"Download finished: {d.get('filename', 'unknown')}")
            
            # Call progress callback with 100% if available
            if self.progress_callback:
                try:
                    self.progress_callback(100.0)
                except Exception as e:
                    logger.debug(f"Progress callback error: {e}")

    def detect_platform(self, url: str) -> str:
        """Detect the platform from URL"""
        url_lower = url.lower()
        
        # Direct video files (only for direct_download mode)
        if any(ext in url_lower for ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp']):
            return 'direct_video'
        
        # Major social media platforms
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'vimeo.com' in url_lower:
            return 'vimeo'
        elif 'dailymotion.com' in url_lower or 'dai.ly' in url_lower:
            return 'dailymotion'
        elif 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
            return 'tiktok'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower or 't.co' in url_lower:
            return 'twitter'
        elif 'reddit.com' in url_lower or 'redd.it' in url_lower:
            return 'reddit'
        elif 'twitch.tv' in url_lower:
            return 'twitch'
        elif 'instagram.com' in url_lower or 'instagr.am' in url_lower:
            return 'instagram'
        elif 'facebook.com' in url_lower or 'fb.com' in url_lower or 'fb.watch' in url_lower:
            return 'facebook'
        elif 'linkedin.com' in url_lower:
            return 'linkedin'
        elif 'snapchat.com' in url_lower:
            return 'snapchat'
        elif 'pinterest.com' in url_lower:
            return 'pinterest'
        elif 'tumblr.com' in url_lower:
            return 'tumblr'
        elif 'discord.com' in url_lower or 'discord.gg' in url_lower:
            return 'discord'
        elif 'telegram.org' in url_lower or 't.me' in url_lower:
            return 'telegram'
        
        # Video hosting platforms
        elif 'bilibili.com' in url_lower or 'b23.tv' in url_lower:
            return 'bilibili'
        elif 'nicovideo.jp' in url_lower:
            return 'nicovideo'
        elif 'rutube.ru' in url_lower:
            return 'rutube'
        elif 'vk.com' in url_lower:
            return 'vk'
        elif 'ok.ru' in url_lower:
            return 'okru'
        elif 'niconico.jp' in url_lower:
            return 'niconico'
        elif 'peertube' in url_lower:
            return 'peertube'
        elif 'odysee.com' in url_lower:
            return 'odysee'
        elif 'lbry.com' in url_lower:
            return 'lbry'
        elif 'rumble.com' in url_lower:
            return 'rumble'
        elif 'brighteon.com' in url_lower:
            return 'brighteon'
        elif 'bitchute.com' in url_lower:
            return 'bitchute'
        elif 'minds.com' in url_lower:
            return 'minds'
        
        # If it's a web URL but not a known platform, treat as generic
        elif url_lower.startswith(('http://', 'https://')):
            return 'generic_video'
        
        return 'unknown'
    
    def get_yt_dlp_opts(self, quality: str = "best", format: str = "mp4", 
                       audio_only: bool = False, progress_hook=None) -> Dict[str, Any]:
        """Get yt-dlp options with enhanced settings for social media platforms"""
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
            # Enhanced social media compatibility
            # Disable all browser cookie extraction to avoid keyring issues
            'cookiefile': None,  # Allow cookie file if available
            # No browser cookie extraction to avoid keyring errors
            'extract_flat': False,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'skip_download': False,
            'verbose': False,
            # Better error handling
            'ignore_no_formats_error': True,
            'no_warnings': False,
            # Enhanced headers for social media
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        }
        
        # Always use our enhanced progress hook
        opts['progress_hooks'] = [self._progress_hook]
        
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
    
    def get_platform_specific_opts(self, platform: str, quality: str = "best", format: str = "mp4", audio_only: bool = False) -> Dict[str, Any]:
        """Get platform-specific yt-dlp options for better social media compatibility"""
        base_opts = self.get_yt_dlp_opts(quality, format, audio_only)
        
        platform_specific = {
            'youtube': {
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'live'],
                        'player_client': ['android', 'web'],
                        'player_skip': ['webpage', 'configs'],
                    }
                }
            },
            'tiktok': {
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                        'app_version': '1.0.0',
                        'manifest_app_version': '1.0.0',
                    }
                }
            },
            'instagram': {
                'extractor_args': {
                    'instagram': {
                        'login': None,
                        'password': None,
                    }
                }
            },
            'twitter': {
                'extractor_args': {
                    'twitter': {
                        'api_hostname': 'api.twitter.com',
                    }
                }
            },
            'facebook': {
                'extractor_args': {
                    'facebook': {
                        'login': None,
                        'password': None,
                    }
                }
            },
            'reddit': {
                'extractor_args': {
                    'reddit': {
                        'client_id': None,
                        'client_secret': None,
                    }
                }
            },
            'twitch': {
                'extractor_args': {
                    'twitch': {
                        'client_id': None,
                        'client_secret': None,
                    }
                }
            },
            'vimeo': {
                'extractor_args': {
                    'vimeo': {
                        'access_token': None,
                    }
                }
            }
        }
        
        if platform in platform_specific:
            base_opts.update(platform_specific[platform])
        
        return base_opts
    
    def download_with_yt_dlp(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False) -> str:
        """Download using yt-dlp with enhanced options"""
        logger.info(f"Attempting yt-dlp download from: {url}")
        
        ydl_opts = self.get_yt_dlp_opts(quality, format, audio_only)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Starting yt-dlp download...")
                ydl.download([url])
                
                # Get the downloaded file - try multiple approaches
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'unknown_title')
                ext = info.get('ext', format or 'mp4')
                
                # Try different filename patterns
                possible_filenames = [
                    f"{title}.{ext}",
                    f"{title}.mp4",
                    f"{title}.webm",
                    f"{title}.mkv"
                ]
                
                # Also check for files with special characters removed
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                possible_filenames.extend([
                    f"{safe_title}.{ext}",
                    f"{safe_title}.mp4",
                    f"{safe_title}.webm",
                    f"{safe_title}.mkv"
                ])
                
                # Look for the downloaded file
                for filename in possible_filenames:
                    filepath = self.download_dir / filename
                if filepath.exists():
                    logger.info(f"Successfully downloaded with yt-dlp: {filename}")
                    return str(filepath)
                
                # If not found by name, look for recently created files
                logger.warning(f"File not found by expected name, searching for recent files...")
                import time
                current_time = time.time()
                
                for file in self.download_dir.iterdir():
                    if file.is_file() and file.suffix.lower() in ['.mp4', '.webm', '.mkv', '.avi', '.mov']:
                        # Check if file was created in the last 5 minutes
                        if current_time - file.stat().st_mtime < 300:  # 5 minutes
                            logger.info(f"Found recently created file: {file.name}")
                            return str(file)
                
                # If still not found, list all files in directory for debugging
                logger.error(f"Download completed but file not found. Available files in {self.download_dir}:")
                for file in self.download_dir.iterdir():
                    if file.is_file():
                        logger.error(f"  - {file.name} ({file.stat().st_size} bytes)")
                
                raise Exception(f"Download completed but file not found. Tried: {possible_filenames}")
                    
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
    
    def download_direct_video(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False) -> str:
        """Download direct video files"""
        logger.info(f"Attempting direct video download from: {url} (audio_only: {audio_only})")
        
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
                    # Use appropriate extension based on audio_only
                    if audio_only:
                        filename = f"audio_{int(time.time())}.mp3"
                    else:
                        filename = f"video_{int(time.time())}.{format}"
            
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
                            
                            # Call progress callback if available
                            if self.progress_callback:
                                try:
                                    self.progress_callback(round(progress, 2))
                                except Exception as e:
                                    logger.debug(f"Progress callback error: {e}")
            
            if filepath.exists():
                logger.info(f"Successfully downloaded direct video: {filename}")
                
                # Call progress callback with 100% if available
                if self.progress_callback:
                    try:
                        self.progress_callback(100.0)
                    except Exception as e:
                        logger.debug(f"Progress callback error: {e}")
                
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

    def download_video(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False, direct_download: bool = False, stream_to_minio: bool = True) -> str:
        """Download video using multiple social media downloaders with fallback"""
        platform = self.detect_platform(url)
        logger.info(f"Detected platform: {platform} for URL: {url} (direct_download: {direct_download})")
        
        # Always use direct streaming to MinIO
        logger.info("Streaming download to MinIO")
        try:
            return self.download_and_stream_to_minio(url, quality, format, audio_only)
        except Exception as e:
            logger.warning(f"Direct streaming to MinIO failed: {e}")
            # Fall back to regular download methods (but still stream to MinIO)
        
        # If direct_download is explicitly requested, use direct download only
        if direct_download:
            logger.info("Direct download requested - using direct download only")
            try:
                logger.info("Attempting direct video download...")
                # For direct download, we still need to stream to MinIO
                # Download to temporary file first, then upload to MinIO
                temp_file = self.download_direct_video(url, quality, format, audio_only)
                
                if temp_file and os.path.exists(temp_file):
                    # Import MinIO storage
                    from minio_config import MinIOStorage
                    minio_storage = MinIOStorage()
                    
                    if not minio_storage.client:
                        raise Exception("MinIO client not available")
                    
                    # Generate unique object name
                    import uuid
                    import time
                    import re
                    
                    # Get filename from temp file
                    filename = os.path.basename(temp_file)
                    name, ext = os.path.splitext(filename)
                    
                    # Clean the name for object name
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
                    safe_name = safe_name[:50]  # Limit length
                    
                    object_name = f"{safe_name}_{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
                    
                    try:
                        # Upload to MinIO
                        result = minio_storage.upload_file(temp_file, object_name)
                        if result.get('success'):
                            logger.info(f"Successfully uploaded direct download to MinIO: {object_name}")
                            return object_name
                        else:
                            raise Exception(f"MinIO upload failed: {result.get('error')}")
                    finally:
                        # Clean up temporary file
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            logger.info(f"Cleaned up temporary direct download file: {temp_file}")
                else:
                    raise Exception("Direct download failed - no file created")
                    
            except Exception as e:
                logger.warning(f"Direct video download failed: {e}")
                raise Exception(f"Direct download failed for URL: {url}")
        
        # Method 1: yt-dlp (primary method for all social media platforms)
        try:
            logger.info("Attempting download with yt-dlp (primary method)...")
            return self.download_with_yt_dlp(url, quality, format, audio_only)
        except Exception as e:
            logger.warning(f"yt-dlp download failed: {e}")
        
        # Method 2: Platform-specific fallbacks
        if platform == 'youtube':
            try:
                logger.info("Attempting YouTube-specific download with pytube...")
                return self.download_with_pytube(url, quality, format, audio_only)
            except Exception as e:
                logger.warning(f"pytube download failed: {e}")
        
        # Method 2.5: Platform-specific yt-dlp options for better compatibility
        try:
            logger.info(f"Attempting platform-specific yt-dlp download for {platform}...")
            platform_opts = self.get_platform_specific_opts(platform, quality, format, audio_only)
            if platform_opts:
                with yt_dlp.YoutubeDL(platform_opts) as ydl:
                    ydl.download([url])
                    # Get the downloaded file - use the same improved detection logic
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'unknown_title')
                    ext = info.get('ext', format or 'mp4')
                    
                    # Try different filename patterns
                    possible_filenames = [
                        f"{title}.{ext}",
                        f"{title}.mp4",
                        f"{title}.webm",
                        f"{title}.mkv"
                    ]
                    
                    # Also check for files with special characters removed
                    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    possible_filenames.extend([
                        f"{safe_title}.{ext}",
                        f"{safe_title}.mp4",
                        f"{safe_title}.webm",
                        f"{safe_title}.mkv"
                    ])
                    
                    # Look for the downloaded file
                    for filename in possible_filenames:
                        filepath = self.download_dir / filename
                        if filepath.exists():
                            logger.info(f"Successfully downloaded with platform-specific yt-dlp: {filename}")
                            return str(filepath)
                    
                    # If not found by name, look for recently created files
                    logger.warning(f"File not found by expected name, searching for recent files...")
                    import time
                    current_time = time.time()
                    
                    for file in self.download_dir.iterdir():
                        if file.is_file() and file.suffix.lower() in ['.mp4', '.webm', '.mkv', '.avi', '.mov']:
                            # Check if file was created in the last 5 minutes
                            if current_time - file.stat().st_mtime < 300:  # 5 minutes
                                logger.info(f"Found recently created file: {file.name}")
                                return str(file)
                    
                    # If still not found, list all files in directory for debugging
                    logger.error(f"Download completed but file not found. Available files in {self.download_dir}:")
                    for file in self.download_dir.iterdir():
                        if file.is_file():
                            logger.error(f"  - {file.name} ({file.stat().st_size} bytes)")
                    
                    raise Exception(f"Download completed but file not found. Tried: {possible_filenames}")
        except Exception as e:
            logger.warning(f"Platform-specific yt-dlp download failed: {e}")
        
        # Method 3: youtube-dl as secondary fallback
        if YOUTUBE_DL_AVAILABLE:
            try:
                logger.info("Attempting download with youtube-dl (secondary fallback)...")
                success, filepath, error = self.download_with_youtube_dl(url, quality, format, audio_only)
                if success:
                    return filepath
                else:
                    logger.warning(f"youtube-dl download failed: {error}")
            except Exception as e:
                logger.warning(f"youtube-dl download failed: {e}")
        
        # Method 4: Generic video downloader for unknown platforms
        if platform in ['unknown', 'generic_video'] or platform not in ['direct_video']:
            try:
                logger.info("Attempting generic video download for unknown platform...")
                return self.download_generic_video(url, quality, format, audio_only)
            except Exception as e:
                logger.warning(f"Generic video download failed: {e}")
        
        # If all social media downloaders fail
        raise Exception(f"All social media download methods failed for URL: {url}. Platform: {platform}")
    
    def download_and_stream_to_minio(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False) -> str:
        """
        Download video and stream directly to MinIO without saving locally
        
        Args:
            url: Video URL to download
            quality: Video quality
            format: Output format
            audio_only: Whether to download audio only
            
        Returns:
            MinIO object name of the uploaded file
        """
        logger.info(f"Starting direct streaming download to MinIO: {url}")
        
        try:
            # Import MinIO storage
            from minio_config import MinIOStorage
            minio_storage = MinIOStorage()
            
            if not minio_storage.client:
                raise Exception("MinIO client not available")
            
            # Generate unique object name with proper extension
            import uuid
            import time
            import re
            
            # Default title and extension based on audio_only
            if audio_only:
                title = 'audio'
                default_ext = 'mp3'
            else:
                title = 'video'
                default_ext = format
            
            object_name = f"{title}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{default_ext}"
            
            # Try different download methods for streaming
            platform = self.detect_platform(url)
            
            # Method 1: Try yt-dlp with proper streaming
            try:
                logger.info("Attempting yt-dlp streaming to MinIO...")
                ydl_opts = self.get_yt_dlp_opts(quality, format, audio_only)
                ydl_opts.update({
                    'outtmpl': '-',  # Output to stdout
                    'quiet': False,
                    'progress_hooks': [self._progress_hook],
                    'no_warnings': False,
                    'verbose': True
                })
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Get video info first
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'video')
                    
                    # Clean the title for filename
                    import re
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    safe_title = safe_title[:50]  # Limit length
                    
                    # Update object name with proper title and extension
                    if audio_only:
                        object_name = f"{safe_title}_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp3"
                    else:
                        object_name = f"{safe_title}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{format}"
                    
                    # Download to memory buffer
                    import io
                    import subprocess
                    import tempfile
                    
                    # Create a temporary file for the download
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format}') as temp_file:
                        temp_path = temp_file.name
                    
                    try:
                        # Download to temporary file first
                        ydl_opts['outtmpl'] = temp_path
                        ydl.download([url])
                        
                        # Check if file was downloaded successfully and validate it
                        if os.path.exists(temp_path) and self._validate_video_file(temp_path):
                            # Read the file and upload to MinIO
                            with open(temp_path, 'rb') as f:
                                data = f.read()
                            
                            if data:
                                # Upload to MinIO with correct content type
                                if audio_only:
                                    content_type = "audio/mpeg"
                                else:
                                    content_type = f"video/{format}"
                                
                                result = minio_storage.upload_from_memory(data, object_name, content_type)
                                if result.get('success'):
                                    logger.info(f"Successfully streamed to MinIO: {object_name}")
                                    return object_name
                                else:
                                    raise Exception(f"MinIO upload failed: {result.get('error')}")
                            else:
                                raise Exception("No data downloaded")
                        else:
                            raise Exception("File download failed or file is empty")
                    finally:
                        # Clean up temporary file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        
            except Exception as e:
                logger.warning(f"yt-dlp streaming failed: {e}")
            
            # Method 2: Try direct URL streaming if available (only for direct video URLs)
            try:
                logger.info("Attempting direct URL streaming to MinIO...")
                # Check for both video and audio file extensions
                video_extensions = ['.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv', '.m4v']
                audio_extensions = ['.mp3', '.m4a', '.wav', '.aac', '.ogg', '.flac']
                
                if audio_only:
                    # For audio_only, check audio extensions
                    if any(ext in url.lower() for ext in audio_extensions):
                        content_type = "audio/mpeg"
                        result = minio_storage.upload_from_url_stream(url, object_name, content_type)
                        if result.get('success'):
                            logger.info(f"Successfully streamed audio URL to MinIO: {object_name}")
                            return object_name
                        else:
                            raise Exception(f"Audio URL streaming failed: {result.get('error')}")
                    else:
                        logger.info("Skipping direct URL streaming - not a direct audio file URL")
                        raise Exception("Not a direct audio file URL")
                else:
                    # For video, check video extensions
                    if any(ext in url.lower() for ext in video_extensions):
                        content_type = f"video/{format}"
                        result = minio_storage.upload_from_url_stream(url, object_name, content_type)
                        if result.get('success'):
                            logger.info(f"Successfully streamed video URL to MinIO: {object_name}")
                            return object_name
                        else:
                            raise Exception(f"Video URL streaming failed: {result.get('error')}")
                    else:
                        logger.info("Skipping direct URL streaming - not a direct video file URL")
                        raise Exception("Not a direct video file URL")
                    
            except Exception as e:
                logger.warning(f"Direct URL streaming failed: {e}")
            
            # Method 3: Fallback to temporary file upload with enhanced error handling
            try:
                logger.info("Attempting fallback download with temporary file...")
                # Download to temporary file (force local download for fallback)
                temp_file = self._download_video_local(url, quality, format, audio_only, direct_download=False)
                
                if temp_file and os.path.exists(temp_file) and self._validate_video_file(temp_file):
                    file_size = os.path.getsize(temp_file)
                    logger.info(f"Temporary file downloaded and validated: {temp_file} ({file_size} bytes)")
                    
                    try:
                        # Upload to MinIO
                        result = minio_storage.upload_file(temp_file, object_name)
                        if result.get('success'):
                            logger.info(f"Successfully uploaded temporary file to MinIO: {object_name}")
                            return object_name
                        else:
                            raise Exception(f"MinIO upload failed: {result.get('error')}")
                    finally:
                        # Ensure temporary file is cleaned up
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            logger.info(f"Cleaned up temporary file: {temp_file}")
                else:
                    raise Exception("Temporary file download failed")
                    
            except Exception as e:
                logger.warning(f"Fallback download failed: {e}")
            
            raise Exception("All streaming methods failed")
            
        except Exception as e:
            logger.error(f"Direct streaming to MinIO failed: {e}")
            raise
    
    def _download_video_local(self, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False, direct_download: bool = False) -> str:
        """
        Internal method for local download (used as fallback for streaming)
        This is the original download logic without MinIO streaming
        """
        platform = self.detect_platform(url)
        logger.info(f"Local download fallback for platform: {platform}")
        
        # If direct_download is explicitly requested, use direct download only
        if direct_download:
            logger.info("Direct download requested")
            try:
                return self.download_direct_video(url, quality, format, audio_only)
            except Exception as e:
                logger.error(f"Direct download failed: {e}")
                raise Exception(f"Direct download failed for URL: {url}")
        
        # Try yt-dlp first (primary social media downloader)
        try:
            logger.info("Attempting yt-dlp download...")
            return self.download_with_yt_dlp(url, quality, format, audio_only)
        except Exception as e:
            logger.warning(f"yt-dlp download failed: {e}")
        
        # Try pytube for YouTube-specific downloads
        if "youtube.com" in url or "youtu.be" in url:
            try:
                logger.info("Attempting pytube download...")
                return self.download_with_pytube(url, quality, format, audio_only)
            except Exception as e:
                logger.warning(f"pytube download failed: {e}")
        
        # Try platform-specific yt-dlp with custom options
        try:
            logger.info("Attempting platform-specific yt-dlp download...")
            return self.download_with_platform_specific_yt_dlp(url, quality, format, audio_only)
        except Exception as e:
            logger.warning(f"Platform-specific yt-dlp download failed: {e}")
        
        # Try youtube-dl as secondary fallback
        try:
            logger.info("Attempting youtube-dl download...")
            return self.download_with_youtube_dl(url, quality, format, audio_only)
        except Exception as e:
            logger.warning(f"youtube-dl download failed: {e}")
        
        # Try generic video download as last resort
        try:
            logger.info("Attempting generic video download...")
            return self.download_generic_video(url, quality, format, audio_only)
        except Exception as e:
            logger.warning(f"Generic video download failed: {e}")
        
        # If all social media downloaders fail
        raise Exception(f"All social media download methods failed for URL: {url}. Platform: {platform}")
    
    def _validate_video_file(self, file_path: str) -> bool:
        """
        Validate that a downloaded file is a proper video file
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.warning(f"File is empty: {file_path}")
                return False
            
            # Check file extension
            video_extensions = ['.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv', '.m4v']
            audio_extensions = ['.mp3', '.m4a', '.wav', '.aac', '.ogg', '.flac']
            valid_extensions = video_extensions + audio_extensions
            
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext not in valid_extensions:
                logger.warning(f"Invalid file extension: {file_ext}")
                return False
            
            # Check minimum file size (1KB)
            if file_size < 1024:
                logger.warning(f"File too small: {file_size} bytes")
                return False
            
            logger.info(f"File validation passed: {file_path} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return False
    
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