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
    DOWNLOAD_TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', '600'))  # 10 minutes (increased for large files)
    LOCAL_STORAGE_FALLBACK = os.getenv('LOCAL_STORAGE_FALLBACK', 'true').lower() == 'true'
    
    # Concurrency and Performance Configuration
    MAX_CONCURRENT_DOWNLOADS = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '50'))  # Limit concurrent downloads
    MAX_MEMORY_TASKS = int(os.getenv('MAX_MEMORY_TASKS', '1000'))  # Max tasks in memory
    TASK_CLEANUP_INTERVAL = int(os.getenv('TASK_CLEANUP_INTERVAL', '3600'))  # Cleanup every hour
    TASK_RETENTION_HOURS = int(os.getenv('TASK_RETENTION_HOURS', '24'))  # Keep tasks for 24 hours
    
    # Rate Limiting - Removed (RapidAPI handles rate limiting)
    
    # Worker Configuration
    WORKER_POOL_SIZE = int(os.getenv('WORKER_POOL_SIZE', '10'))  # Number of worker processes
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '8192'))  # Download chunk size
    
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
        print(f"Max Concurrent Downloads: {cls.MAX_CONCURRENT_DOWNLOADS}")
        print(f"Max Memory Tasks: {cls.MAX_MEMORY_TASKS}")
        print(f"Worker Pool Size: {cls.WORKER_POOL_SIZE}")
        print(f"Rate Limiting: Handled by RapidAPI")
        print("=" * 40)
    
    @classmethod
    def calculate_optimal_concurrency(cls, available_ram_gb: float = None, cpu_cores: int = None):
        """Calculate optimal concurrency settings based on system resources"""
        import psutil
        
        if available_ram_gb is None:
            available_ram_gb = psutil.virtual_memory().total / (1024**3)
        
        if cpu_cores is None:
            cpu_cores = psutil.cpu_count(logical=True)
        
        # Memory-based calculation (conservative)
        # Each download uses ~150MB on average
        memory_per_download_mb = 150
        max_downloads_by_memory = int((available_ram_gb * 1024 * 0.7) / memory_per_download_mb)  # Use 70% of RAM
        
        # CPU-based calculation
        # Each download can use 1-2 cores, but we want to leave some for the system
        max_downloads_by_cpu = int(cpu_cores * 0.8)  # Use 80% of CPU cores
        
        # Network-based calculation (assuming 100 Mbps connection)
        # Each download can use ~10 Mbps
        network_mbps = 100  # Conservative estimate
        max_downloads_by_network = int(network_mbps / 10)
        
        # Take the minimum of all constraints
        optimal_concurrent_downloads = min(max_downloads_by_memory, max_downloads_by_cpu, max_downloads_by_network)
        
        # Ensure reasonable limits
        optimal_concurrent_downloads = max(10, min(optimal_concurrent_downloads, 100))
        
        # Calculate other settings
        optimal_memory_tasks = int(optimal_concurrent_downloads * 20)  # 20x for task history
        optimal_global_rate_limit = int(optimal_concurrent_downloads * 2)  # 2x for queuing
        
        return {
            "system_resources": {
                "available_ram_gb": round(available_ram_gb, 2),
                "cpu_cores": cpu_cores,
                "estimated_network_mbps": network_mbps
            },
            "calculations": {
                "max_by_memory": max_downloads_by_memory,
                "max_by_cpu": max_downloads_by_cpu,
                "max_by_network": max_downloads_by_network,
                "limiting_factor": "memory" if max_downloads_by_memory <= max_downloads_by_cpu else "cpu" if max_downloads_by_cpu <= max_downloads_by_network else "network"
            },
            "recommended_settings": {
                "MAX_CONCURRENT_DOWNLOADS": optimal_concurrent_downloads,
                "MAX_MEMORY_TASKS": optimal_memory_tasks,
                "GLOBAL_RATE_LIMIT": optimal_global_rate_limit,
                "WORKER_POOL_SIZE": max(5, int(optimal_concurrent_downloads / 5))
            }
        } 