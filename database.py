import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

# Database configuration
try:
    from config import Config
    DB_HOST = Config.DB_HOST
    DB_PORT = Config.DB_PORT
    DB_NAME = Config.DB_NAME
    DB_USER = Config.DB_USER
    DB_PASSWORD = Config.DB_PASSWORD
    logger.info(f"Using Config: {DB_HOST}:{DB_PORT}/{DB_NAME}")
except ImportError:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '40211')  # Updated to match Docker port
    DB_NAME = os.getenv('DB_NAME', 'video_downloader')
    DB_USER = os.getenv('DB_USER', 'video_downloader')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'secure_password_123')
    logger.warning("Config not available, using fallback database configuration")

# Validate database URL (ensure port is not empty)
if not DB_PORT or DB_PORT == '':
    DB_PORT = '40211'  # Default to Docker port

# Enable PostgreSQL connection
USE_POSTGRESQL = True
engine = None

if USE_POSTGRESQL:
    try:
        DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        logger.info(f"Attempting PostgreSQL connection: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        logger.info("PostgreSQL engine created successfully")
        
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")
        USE_POSTGRESQL = False

if not USE_POSTGRESQL:
    logger.info("Falling back to SQLite database")
    import aiosqlite
    DATABASE_URL = "sqlite+aiosqlite:///./video_downloader.db"
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    logger.info("SQLite engine created successfully")

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
Base = declarative_base()

class DownloadTask(Base):
    """Database model for download tasks"""
    __tablename__ = "download_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    url = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="starting")
    progress = Column(Float, default=0.0)
    filename = Column(Text)
    download_url = Column(Text)
    storage_type = Column(String(50), default="local")
    file_size = Column(Integer)
    client_ip = Column(String(45))
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseManager:
    """Database manager for async operations"""
    
    def __init__(self):
        self.engine = engine
        self.async_session = async_session
    
    async def init_db(self):
        """Initialize database and create tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        if USE_POSTGRESQL:
            logger.info("PostgreSQL database initialized successfully")
        else:
            logger.info("SQLite database initialized successfully")
    
    async def create_task(self, task_data: Dict[str, Any]) -> DownloadTask:
        """Create a new download task"""
        async with self.async_session() as session:
            task = DownloadTask(**task_data)
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task
    
    async def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Get a task by task_id"""
        async with self.async_session() as session:
            result = await session.execute(
                select(DownloadTask).where(DownloadTask.task_id == task_id)
            )
            return result.scalar_one_or_none()
    
    async def update_task(self, task_id: str, update_data: Dict[str, Any]) -> Optional[DownloadTask]:
        """Update a task"""
        async with self.async_session() as session:
            result = await session.execute(
                select(DownloadTask).where(DownloadTask.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                for key, value in update_data.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                task.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(task)
            
            return task
    
    async def update_task_status(self, task_id: str, status: str, progress: float = None, error: str = None) -> Optional[DownloadTask]:
        """Update task status"""
        update_data = {'status': status}
        if progress is not None:
            update_data['progress'] = progress
        if error is not None:
            update_data['error'] = error
        return await self.update_task(task_id, update_data)
    
    async def update_task_completed(self, task_id: str, filename: str = None, download_url: str = None, 
                                   storage_type: str = None, file_size: int = None) -> Optional[DownloadTask]:
        """Update task as completed"""
        update_data = {
            'status': 'completed',
            'progress': 100.0
        }
        if filename is not None:
            update_data['filename'] = filename
        if download_url is not None:
            update_data['download_url'] = download_url
        if storage_type is not None:
            update_data['storage_type'] = storage_type
        if file_size is not None:
            update_data['file_size'] = file_size
        return await self.update_task(task_id, update_data)

    async def get_all_tasks(self, limit: int = 100) -> List[DownloadTask]:
        """Get all tasks with limit"""
        async with self.async_session() as session:
            result = await session.execute(
                select(DownloadTask).order_by(DownloadTask.created_at.desc()).limit(limit)
            )
            return result.scalars().all()
    
    async def get_tasks_by_status(self, status: str) -> List[DownloadTask]:
        """Get tasks by status"""
        async with self.async_session() as session:
            result = await session.execute(
                select(DownloadTask).where(DownloadTask.status == status)
            )
            return result.scalars().all()
    
    async def get_tasks_by_client_ip(self, client_ip: str, limit: int = 50) -> List[DownloadTask]:
        """Get tasks by client IP"""
        async with self.async_session() as session:
            result = await session.execute(
                select(DownloadTask)
                .where(DownloadTask.client_ip == client_ip)
                .order_by(DownloadTask.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        async with self.async_session() as session:
            result = await session.execute(
                select(DownloadTask).where(DownloadTask.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                await session.delete(task)
                await session.commit()
                return True
            return False
    
    async def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up tasks older than specified days"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with self.async_session() as session:
            result = await session.execute(
                select(DownloadTask).where(DownloadTask.created_at < cutoff_date)
            )
            old_tasks = result.scalars().all()
            
            for task in old_tasks:
                await session.delete(task)
            
            await session.commit()
            return len(old_tasks)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        async with self.async_session() as session:
            # Total tasks
            total_result = await session.execute(select(DownloadTask))
            total_tasks = len(total_result.scalars().all())
            
            # Tasks by status
            status_stats = {}
            for status in ['starting', 'downloading', 'uploading', 'completed', 'failed', 'cancelled']:
                result = await session.execute(
                    select(DownloadTask).where(DownloadTask.status == status)
                )
                status_stats[status] = len(result.scalars().all())
            
            # Recent activity (last 24 hours)
            from datetime import timedelta
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_result = await session.execute(
                select(DownloadTask).where(DownloadTask.created_at >= recent_cutoff)
            )
            recent_tasks = len(recent_result.scalars().all())
            
            return {
                'total_tasks': total_tasks,
                'status_breakdown': status_stats,
                'recent_24h': recent_tasks
            }

# Global database manager instance
db_manager = DatabaseManager()

# Initialize database on startup
async def init_database():
    """Initialize database on startup"""
    await db_manager.init_db() 