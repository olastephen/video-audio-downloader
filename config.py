import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Social Media Info Extractor API"""
    
    # API Configuration
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '8000'))
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Extraction Configuration
    EXTRACTION_TIMEOUT = int(os.getenv('EXTRACTION_TIMEOUT', '30'))  # 30 seconds timeout
    MAX_URL_LENGTH = int(os.getenv('MAX_URL_LENGTH', '2048'))  # Maximum URL length
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        print("=== Social Media Info Extractor API Configuration ===")
        print(f"API: {cls.API_HOST}:{cls.API_PORT}")
        print(f"Debug: {cls.DEBUG}")
        print(f"Extraction Timeout: {cls.EXTRACTION_TIMEOUT} seconds")
        print(f"Max URL Length: {cls.MAX_URL_LENGTH} characters")
        print("=" * 50) 