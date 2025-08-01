import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Video Downloader API"""
    
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'https://dbgate-u39275.vm.elestio.app')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'video_downloader')
    DB_USER = os.getenv('DB_USER', 'admin')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'G5oRd5V2-fPR7-XUyvX6VG')
    
    # MinIO Configuration
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio-u39275.vm.elestio.app:34256')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'root')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'o86Lv2Ta-x1rk-SHd5RK0B')
    MINIO_SECURE = os.getenv('MINIO_SECURE', 'true').lower() == 'true'
    MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'video-downloads')
    
    # API Configuration
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '8000'))
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Download Configuration
    MAX_DOWNLOAD_SIZE = int(os.getenv('MAX_DOWNLOAD_SIZE', '1073741824'))  # 1GB
    DOWNLOAD_TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', '300'))  # 5 minutes
    LOCAL_STORAGE_FALLBACK = os.getenv('LOCAL_STORAGE_FALLBACK', 'true').lower() == 'true'
    
    # Rate Limiting
    RATE_LIMIT = int(os.getenv('RATE_LIMIT', '10'))  # requests per minute
    
    @classmethod
    def get_database_url(cls):
        """Get the database URL for SQLAlchemy"""
        return f"postgresql+asyncpg://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        print("=== Video Downloader API Configuration ===")
        print(f"Database: {cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}")
        print(f"MinIO: {cls.MINIO_ENDPOINT}/{cls.MINIO_BUCKET}")
        print(f"API: {cls.API_HOST}:{cls.API_PORT}")
        print(f"Debug: {cls.DEBUG}")
        print(f"Max Download Size: {cls.MAX_DOWNLOAD_SIZE} bytes")
        print(f"Download Timeout: {cls.DOWNLOAD_TIMEOUT} seconds")
        print(f"Local Storage Fallback: {cls.LOCAL_STORAGE_FALLBACK}")
        print("=" * 40) 