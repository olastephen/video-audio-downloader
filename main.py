from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import yt_dlp
import os
import asyncio
import aiofiles
import json
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration and MinIO storage
try:
    from config import Config
    from minio_config import minio_storage
    MINIO_AVAILABLE = True
    logger.info("MinIO storage loaded successfully")
except ImportError as e:
    MINIO_AVAILABLE = False
    logger.warning(f"MinIO storage not available: {e}, using local storage only")

# Import database
try:
    from database import db_manager, init_database
    DATABASE_AVAILABLE = True
    logger.info("Database loaded successfully")
except ImportError as e:
    DATABASE_AVAILABLE = False
    logger.warning(f"Database not available: {e}, using in-memory storage only")

# Import enhanced downloader
try:
    from enhanced_downloader import EnhancedVideoDownloader
    ENHANCED_DOWNLOADER_AVAILABLE = True
    logger.info("Enhanced downloader loaded successfully")
except ImportError as e:
    ENHANCED_DOWNLOADER_AVAILABLE = False
    logger.warning(f"Enhanced downloader not available: {e}, using basic yt-dlp only")

# Lifespan context manager for startup/shutdown
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("Starting up...")
    if DATABASE_AVAILABLE:
        try:
            await init_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down gracefully...")
    # Mark all ongoing tasks as cancelled
    for task_id in list(download_status.keys()):
        if download_status[task_id]['status'] in ['downloading', 'uploading']:
            download_status[task_id]['status'] = 'cancelled'
            download_status[task_id]['error'] = 'Server shutdown'
    logger.info("All tasks marked as cancelled")

# Start periodic cleanup task
async def start_cleanup_task():
    """Start periodic cleanup of old tasks"""
    while True:
        try:
            await asyncio.sleep(Config.TASK_CLEANUP_INTERVAL)
            await cleanup_old_tasks()
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

# Start cleanup task when app starts
@app.on_event("startup")
async def startup_event():
    """Startup event to initialize cleanup task"""
    asyncio.create_task(start_cleanup_task())

app = FastAPI(
    title="Video Downloader API",
    description="A powerful API to download videos from various platforms",
    version="1.0.0",
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

# Create downloads directory
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Store download status with concurrency management
download_status = {}
active_downloads = 0  # Track active downloads
download_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_DOWNLOADS)

# Rate limiting removed - RapidAPI handles rate limiting

async def cleanup_old_tasks():
    """Clean up old completed tasks from memory"""
    import time
    current_time = time.time()
    cutoff_time = current_time - (Config.TASK_RETENTION_HOURS * 3600)
    
    tasks_to_remove = []
    for task_id, task_data in download_status.items():
        # Remove tasks older than retention period
        if task_data.get('status') in ['completed', 'failed', 'cancelled']:
            if 'timestamp' in task_data and task_data['timestamp'] < cutoff_time:
                tasks_to_remove.append(task_id)
    
    for task_id in tasks_to_remove:
        del download_status[task_id]
    
    if tasks_to_remove:
        logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks from memory")
    
    # Rate limiting cleanup removed - RapidAPI handles rate limiting

# Initialize enhanced downloader if available
if ENHANCED_DOWNLOADER_AVAILABLE:
    enhanced_downloader = EnhancedVideoDownloader(str(DOWNLOADS_DIR))
else:
    enhanced_downloader = None

class VideoRequest(BaseModel):
    url: HttpUrl
    quality: Optional[str] = "best"
    format: Optional[str] = "mp4"
    audio_only: Optional[bool] = False
    direct_download: Optional[bool] = False

class DownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str

class DownloadStatus(BaseModel):
    task_id: str
    status: str
    progress: Optional[float] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None

def get_ydl_opts(quality: str = "best", format: str = "mp4", audio_only: bool = False) -> Dict[str, Any]:
    """Configure yt-dlp options based on user preferences"""
    opts = {
        'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'noplaylist': True,
        'ignoreerrors': False,
        # Add better compatibility options
        'no_check_certificate': True,
        'prefer_insecure': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'extractor_retries': 3,
        'fragment_retries': 3,
        'retries': 3,
    }
    
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
            # Custom quality selection
            opts['format'] = quality
    
    return opts

def progress_hook(d):
    """Progress hook for yt-dlp to track download progress"""
    if d['status'] == 'downloading':
        task_id = d.get('info_dict', {}).get('_task_id')
        if task_id and task_id in download_status:
            try:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    progress = (downloaded / total) * 100
                    download_status[task_id]['progress'] = round(progress, 2)
            except Exception as e:
                logger.error(f"Error updating progress: {e}")
    
    elif d['status'] == 'finished':
        task_id = d.get('info_dict', {}).get('_task_id')
        if task_id and task_id in download_status:
            download_status[task_id]['status'] = 'completed'
            download_status[task_id]['filename'] = d.get('filename', '')

async def download_video_task(task_id: str, url: str, quality: str = "best", format: str = "mp4", audio_only: bool = False, direct_download: bool = False):
    """Background task to download video with concurrency management"""
    global active_downloads
    
    # Add timestamp for cleanup
    if task_id in download_status:
        download_status[task_id]['timestamp'] = time.time()
    
    # Use semaphore to limit concurrent downloads
    async with download_semaphore:
        active_downloads += 1
        logger.info(f"Starting download task {task_id} (active downloads: {active_downloads})")
        
        try:
            # Update status to downloading immediately
            if task_id in download_status:
                download_status[task_id]['status'] = 'downloading'
                download_status[task_id]['progress'] = 0.0
            
            # Update database if available
            if DATABASE_AVAILABLE:
                try:
                    await db_manager.update_task_status(task_id, 'downloading', progress=0.0)
                except Exception as e:
                    logger.error(f"Failed to update database status: {e}")
        except Exception as e:
            logger.error(f"Error in download task {task_id}: {e}")
            active_downloads -= 1
            raise
    
    # Create progress callback function
    def progress_callback(progress: float):
        """Callback to update progress in real-time"""
        if task_id in download_status:
            download_status[task_id]['progress'] = progress
            logger.info(f"Task {task_id} progress: {progress}%")
        
        # Update database if available
        if DATABASE_AVAILABLE:
            try:
                # Use asyncio.create_task to avoid blocking
                asyncio.create_task(db_manager.update_task_status(task_id, 'downloading', progress=progress))
            except Exception as e:
                logger.debug(f"Failed to update database progress: {e}")
    
    try:
        # Create enhanced downloader instance with progress callback for this task
        task_downloader = EnhancedVideoDownloader(str(DOWNLOADS_DIR), progress_callback=progress_callback)
        
        logger.info(f"Using enhanced downloader for task {task_id} (direct_download: {direct_download})")
        try:
            # Always stream directly to MinIO
            object_name = task_downloader.download_video(url, quality, format, audio_only, direct_download, stream_to_minio=True)
            downloaded_file = f"minio://{object_name}"  # Special marker for MinIO objects
        except Exception as e:
            logger.error(f"Enhanced downloader error: {e}")
            if task_id in download_status:
                download_status[task_id]['status'] = 'failed'
                download_status[task_id]['error'] = str(e)
            if DATABASE_AVAILABLE:
                try:
                    await db_manager.update_task_status(task_id, 'failed', error=str(e))
                except Exception as db_error:
                    logger.error(f"Failed to update database error status: {db_error}")
            return
        
        # Check if file exists and get file size
        if downloaded_file.startswith("minio://"):
            # File is already in MinIO
            object_name = downloaded_file.replace("minio://", "")
            filename = object_name
            file_size = 0  # Will be updated from MinIO metadata
            logger.info(f"File already uploaded to MinIO: {object_name}")
        elif not os.path.exists(downloaded_file):
            error_msg = f"Downloaded file not found: {downloaded_file}"
            logger.error(error_msg)
            if task_id in download_status:
                download_status[task_id]['status'] = 'failed'
                download_status[task_id]['error'] = error_msg
            if DATABASE_AVAILABLE:
                try:
                    await db_manager.update_task_status(task_id, 'failed', error=error_msg)
                except Exception as db_error:
                    logger.error(f"Failed to update database error status: {db_error}")
            return
        else:
            file_size = os.path.getsize(downloaded_file)
            filename = os.path.basename(downloaded_file)
        
        # Upload to MinIO (required - no local storage fallback)
        if MINIO_AVAILABLE and minio_storage:
            try:
                if downloaded_file.startswith("minio://"):
                    # File is already in MinIO, just get the object name
                    object_name = downloaded_file.replace("minio://", "")
                    logger.info(f"File already in MinIO: {object_name}")
                else:
                    logger.info(f"Uploading {downloaded_file} to MinIO for task {task_id}")
                    
                    # Upload to MinIO
                    object_name = f"{task_id}_{filename}"
                    minio_storage.upload_file(downloaded_file, object_name)
                
                # Get presigned URL with proper headers
                download_url = minio_storage.generate_download_url(object_name)
                
                # Clean up local file (only if it's a local file)
                if not downloaded_file.startswith("minio://"):
                    os.remove(downloaded_file)
                    logger.info(f"Cleaned up local file: {downloaded_file}")
                
                # Update status
                if task_id in download_status:
                    download_status[task_id]['status'] = 'completed'
                    download_status[task_id]['progress'] = 100.0
                    download_status[task_id]['filename'] = filename
                    download_status[task_id]['download_url'] = download_url
                    download_status[task_id]['file_size'] = file_size
                
                # Update database
                if DATABASE_AVAILABLE:
                    try:
                        await db_manager.update_task_completed(
                            task_id, 
                            filename=filename,
                            download_url=download_url,
                            file_size=file_size
                        )
                    except Exception as db_error:
                        logger.error(f"Failed to update database completion status: {db_error}")
                
                logger.info(f"Successfully uploaded to MinIO: {object_name}")
                
            except Exception as e:
                error_msg = f"Failed to upload to MinIO: {e}"
                logger.error(error_msg)
                
                # Clean up local file even if MinIO upload fails (only if it's a local file)
                if not downloaded_file.startswith("minio://") and os.path.exists(downloaded_file):
                    os.remove(downloaded_file)
                    logger.info(f"Cleaned up local file after MinIO failure: {downloaded_file}")
                
                if task_id in download_status:
                    download_status[task_id]['status'] = 'failed'
                    download_status[task_id]['error'] = error_msg
                
                if DATABASE_AVAILABLE:
                    try:
                        await db_manager.update_task_status(task_id, 'failed', error=error_msg)
                    except Exception as db_error:
                        logger.error(f"Failed to update database error status: {db_error}")
        else:
            error_msg = "MinIO storage not available - local storage is disabled"
            logger.error(error_msg)
            
            # Clean up local file since we don't allow local storage (only if it's a local file)
            if not downloaded_file.startswith("minio://") and os.path.exists(downloaded_file):
                os.remove(downloaded_file)
                logger.info(f"Cleaned up local file (MinIO not available): {downloaded_file}")
            
            if task_id in download_status:
                download_status[task_id]['status'] = 'failed'
                download_status[task_id]['error'] = error_msg
            
            if DATABASE_AVAILABLE:
                try:
                    await db_manager.update_task_status(task_id, 'failed', error=error_msg)
                except Exception as db_error:
                    logger.error(f"Failed to update database error status: {db_error}")
                    
    except Exception as e:
        error_msg = f"Download task failed: {e}"
        logger.error(error_msg)
        
        if task_id in download_status:
            download_status[task_id]['status'] = 'failed'
            download_status[task_id]['error'] = error_msg
        
        if DATABASE_AVAILABLE:
            try:
                await db_manager.update_task_status(task_id, 'failed', error=error_msg)
            except Exception as db_error:
                logger.error(f"Failed to update database error status: {db_error}")
    
    finally:
        # Always decrement active downloads counter
        active_downloads -= 1
        logger.info(f"Completed download task {task_id} (active downloads: {active_downloads})")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Video Downloader API",
        "version": "1.0.0",
        "enhanced_downloader": ENHANCED_DOWNLOADER_AVAILABLE,
        "minio_storage": MINIO_AVAILABLE,
        "database": DATABASE_AVAILABLE,
        "available_libraries": {
            "yt-dlp": True,
            "pytube": True,
            "youtube-dl": True,
            "cloudscraper": True,
        },
        "storage": {
            "minio": MINIO_AVAILABLE and minio_storage.client is not None,
            "local": False,  # Local storage is disabled
            "bucket": minio_storage.bucket_name if MINIO_AVAILABLE else None
        },
        "endpoints": {
            "download": "/download",
            "status": "/status/{task_id}",
            "download_file": "/download_file/{task_id}",
            "video_info": "/video_info",
            "minio_files": "/minio/files",
            "delete_minio_file": "/minio/files/{object_name}",
            "system_status": "/system/status"
        }
    }

@app.get("/system/status")
async def system_status():
    """Get system status and concurrency information"""
    import psutil
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Count tasks by status
    task_counts = {}
    for task_data in download_status.values():
        status = task_data.get('status', 'unknown')
        task_counts[status] = task_counts.get(status, 0) + 1
    
    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        },
        "concurrency": {
            "active_downloads": active_downloads,
            "max_concurrent_downloads": Config.MAX_CONCURRENT_DOWNLOADS,
            "download_semaphore_available": download_semaphore._value,
            "total_tasks_in_memory": len(download_status),
            "max_memory_tasks": Config.MAX_MEMORY_TASKS
        },
        "tasks": task_counts,
        "rate_limiting": {
            "note": "Rate limiting handled by RapidAPI",
            "rapidapi_managed": True
        },
        "configuration": {
            "download_timeout": Config.DOWNLOAD_TIMEOUT,
            "max_download_size": Config.MAX_DOWNLOAD_SIZE,
            "task_retention_hours": Config.TASK_RETENTION_HOURS,
            "cleanup_interval": Config.TASK_CLEANUP_INTERVAL
        }
    }

@app.post("/download", response_model=DownloadResponse)
async def download_video(
    request: VideoRequest,
    background_tasks: BackgroundTasks
):
    """Start a video download task
    
    Parameters:
    - url: The video URL to download
    - quality: Video quality (best, worst, or custom format string)
    - format: Output format (mp4, webm, etc.)
    - audio_only: If True, download audio only
    - direct_download: If True, skip site-specific handlers and use direct download only
    
    Note: All downloads are streamed directly to MinIO without saving locally
    """
    try:
        task_id = str(uuid.uuid4())
        
        # Initialize task status immediately
        download_status[task_id] = {
            'status': 'starting',
            'progress': 0.0,
            'filename': None,
            'error': None,
            'download_url': None,
            'storage_type': 'minio',  # Changed to minio since local storage is disabled
            'file_size': None,
            'client_ip': None,  # RapidAPI handles client tracking
            'created_at': time.time()
        }
        
        # Create database task if available
        if DATABASE_AVAILABLE:
            try:
                task_data = {
                    'task_id': task_id,
                    'url': str(request.url),
                    'status': 'starting',
                    'progress': 0.0,
                    'client_ip': None,  # RapidAPI handles client tracking
                    'storage_type': 'minio'
                }
                await db_manager.create_task(task_data)
                logger.info(f"Created database task: {task_id}")
            except Exception as e:
                logger.error(f"Failed to create database task: {e}")
        
        # Basic URL validation only
        url = str(request.url)
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Schedule background task without waiting
        background_tasks.add_task(
            download_video_task,
            task_id,
            url,
            request.quality,
            request.format,
            request.audio_only,
            request.direct_download
        )
        
        # Return immediately
        return DownloadResponse(
            task_id=task_id,
            status="started",
            message="Download task started successfully"
        )
        
    except Exception as e:
        logger.error(f"Error starting download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}", response_model=DownloadStatus)
async def get_download_status(task_id: str):
    """Get the status of a download task"""
    # First check in-memory status
    if task_id in download_status:
        status_info = download_status[task_id]
        return DownloadStatus(
            task_id=task_id,
            status=status_info['status'],
            progress=status_info.get('progress'),
            filename=status_info.get('filename'),
            error=status_info.get('error'),
            download_url=status_info.get('download_url'),
            file_size=status_info.get('file_size')
        )
    
    # If not in memory, check database
    if DATABASE_AVAILABLE:
        try:
            db_task = await db_manager.get_task(task_id)
            if db_task:
                return DownloadStatus(
                    task_id=task_id,
                    status=db_task.status,
                    progress=db_task.progress,
                    filename=db_task.filename,
                    error=db_task.error,
                    download_url=db_task.download_url,
                    file_size=db_task.file_size
                )
        except Exception as e:
            logger.error(f"Database error when getting task status: {e}")
    
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/download_file/{task_id}")
async def download_file(task_id: str):
    """Download the completed video file by redirecting to MinIO URL"""
    # Check in-memory status first
    status_info = None
    if task_id in download_status:
        status_info = download_status[task_id]
    
    # If not in memory, check database
    if not status_info and DATABASE_AVAILABLE:
        try:
            db_task = await db_manager.get_task(task_id)
            if db_task:
                status_info = {
                    'status': db_task.status,
                    'download_url': db_task.download_url,
                    'file_size': db_task.file_size
                }
        except Exception as e:
            logger.error(f"Database error when getting task: {e}")
    
    if not status_info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if status_info['status'] != 'completed':
        raise HTTPException(
            status_code=400, 
            detail=f"Download not completed. Status: {status_info['status']}"
        )
    
    # Only MinIO storage is supported (local storage disabled)
    if status_info.get('download_url'):
        # Redirect to the MinIO download URL with proper headers
        from fastapi.responses import RedirectResponse
        
        # Get the download URL (it should already have proper headers from MinIO)
        download_url = status_info['download_url']
        
        # Create redirect response with proper headers
        response = RedirectResponse(url=download_url)
        
        # Add additional headers for better file handling
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Pragma"] = "no-cache"
        
        return response
    
    # No local storage fallback
    raise HTTPException(
        status_code=400, 
        detail="File not available. Local storage is disabled and MinIO storage failed."
    )



@app.get("/video_info")
async def get_video_info(url: str = Query(..., description="Video URL to get information")):
    """Get video information without downloading"""
    try:
        if enhanced_downloader:
            # Use enhanced downloader for better info extraction
            info = enhanced_downloader.get_video_info(url)
            return {
                "title": info.get('title'),
                "duration": info.get('duration'),
                "uploader": info.get('uploader'),
                "upload_date": info.get('upload_date'),
                "view_count": info.get('view_count'),
                "like_count": info.get('like_count'),
                "formats": info.get('formats', []),
                "extractor": info.get('extractor', 'enhanced')
            }
        else:
            # Fall back to yt-dlp
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
                    "extractor": "yt-dlp"
                }
            
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/minio/files")
async def list_minio_files():
    """List files stored in MinIO bucket"""
    if not MINIO_AVAILABLE or not minio_storage.client:
        raise HTTPException(status_code=503, detail="MinIO storage not available")
    
    try:
        files = minio_storage.list_files()
        return {
            "files": files,
            "total_count": len(files),
            "bucket": minio_storage.bucket_name
        }
    except Exception as e:
        logger.error(f"Error listing MinIO files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/minio/files/{object_name}")
async def delete_minio_file(object_name: str):
    """Delete a specific file from MinIO bucket"""
    if not MINIO_AVAILABLE or not minio_storage.client:
        raise HTTPException(status_code=503, detail="MinIO storage not available")
    
    try:
        success = minio_storage.delete_file(object_name)
        if success:
            return {"message": f"File {object_name} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"File {object_name} not found")
    except Exception as e:
        logger.error(f"Error deleting MinIO file {object_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    ) 