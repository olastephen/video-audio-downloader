import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Video Downloader API"""
    
    # Database Configuration - Pure PostgreSQL (Elestio)
    DB_HOST = os.getenv('DB_HOST', 'postgres-u39275.vm.elestio.app')  # Elestio PostgreSQL host
    DB_PORT = os.getenv('DB_PORT', '25432')  # Elestio PostgreSQL port
    DB_NAME = os.getenv('POSTGRES1_DB', 'video_downloader')  # Database name
    DB_USER = os.getenv('POSTGRES1_USER', 'postgres')  # PostgreSQL user
    DB_PASSWORD = os.getenv('POSTGRES1_PASSWORD', 'Dc8y1zsi-EAih-ojZwCiVI')  # PostgreSQL password
    DB_SSL_MODE = os.getenv('DB_SSL_MODE', 'require')  # SSL mode for secure connections (working with Elestio)
    ALLOW_SQLITE_FALLBACK = os.getenv('ALLOW_SQLITE_FALLBACK', 'false').lower() == 'true'  # Disable for production
    
    # MinIO Configuration
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio-u39275.vm.elestio.app:34256')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'root')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'o86Lv2Ta-x1rk-SHd5RK0B')
    MINIO_SECURE = os.getenv('MINIO_SECURE', 'true').lower() == 'true'
    MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'video-downloads')
    MINIO_URL_EXPIRY = int(os.getenv('MINIO_URL_EXPIRY', '43200'))  # 12 hours in seconds
    
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
        return f"postgresql+asyncpg://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}?sslmode={cls.DB_SSL_MODE}"
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        print("=== Video Downloader API Configuration ===")
        print(f"Database: {cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}")
        print(f"MinIO: {cls.MINIO_ENDPOINT}/{cls.MINIO_BUCKET}")
        print(f"MinIO URL Expiry: {cls.MINIO_URL_EXPIRY} seconds")
        print(f"API: {cls.API_HOST}:{cls.API_PORT}")
        print(f"Debug: {cls.DEBUG}")
        print(f"Max Download Size: {cls.MAX_DOWNLOAD_SIZE} bytes")
        print(f"Download Timeout: {cls.DOWNLOAD_TIMEOUT} seconds")
        print(f"Local Storage Fallback: {cls.LOCAL_STORAGE_FALLBACK}")
        print("=" * 40) 