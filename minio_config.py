import os
import logging
from typing import Optional, Dict, Any
from minio import Minio
from minio.error import S3Error
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

class MinIOStorage:
    def __init__(self):
        # Try to use Config class first, fallback to environment variables
        try:
            from config import Config
            self.endpoint = Config.MINIO_ENDPOINT
            self.access_key = Config.MINIO_ACCESS_KEY
            self.secret_key = Config.MINIO_SECRET_KEY
            self.secure = Config.MINIO_SECURE
            self.bucket_name = Config.MINIO_BUCKET
            self.url_expiry = Config.MINIO_URL_EXPIRY
            logger.info(f"Using Config class for MinIO settings")
            logger.info(f"MinIO endpoint from config: {self.endpoint}")
        except ImportError:
            # Fallback to environment variables
            self.endpoint = os.getenv('MINIO_ENDPOINT', 'minio-u39275.vm.elestio.app:34256')
            self.access_key = os.getenv('MINIO_ACCESS_KEY', 'root')
            self.secret_key = os.getenv('MINIO_SECRET_KEY', 'o86Lv2Ta-x1rk-SHd5RK0B')
            self.secure = os.getenv('MINIO_SECURE', 'true').lower() == 'true'
            self.bucket_name = os.getenv('MINIO_BUCKET', 'video-downloads')
            self.url_expiry = int(os.getenv('MINIO_URL_EXPIRY', '43200'))
            logger.info(f"Using environment variables for MinIO settings")
            logger.info(f"MinIO endpoint from env: {self.endpoint}")
        
        # Ensure endpoint has port
        if ':' not in self.endpoint:
            self.endpoint = f"{self.endpoint}:34256"
            logger.info(f"Added port to MinIO endpoint: {self.endpoint}")
        
        # Initialize MinIO client
        try:
            logger.info(f"Connecting to MinIO: {self.endpoint} (secure: {self.secure})")
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region="us-east-1"  # Default region for MinIO
            )
            
            # Test connection
            self._test_connection()
            self._ensure_bucket_exists()
            logger.info(f"MinIO client initialized successfully. Bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            self.client = None
    
    def _test_connection(self):
        """Test MinIO connection"""
        try:
            # Try to list buckets to test connection
            buckets = self.client.list_buckets()
            logger.info(f"MinIO connection test successful. Found {len(list(buckets))} buckets")
        except Exception as e:
            logger.error(f"MinIO connection test failed: {e}")
            raise
    
    def _get_content_type(self, file_path: str) -> str:
        """
        Determine the MIME content type based on file extension
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME content type string
        """
        import mimetypes
        
        # Get file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Define common video/audio MIME types
        mime_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.flv': 'video/x-flv',
            '.m4v': 'video/x-m4v',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/mp4',
            '.wav': 'audio/wav',
            '.aac': 'audio/aac',
            '.ogg': 'audio/ogg',
            '.wma': 'audio/x-ms-wma'
        }
        
        # Return specific MIME type if known, otherwise use mimetypes module
        if file_ext in mime_types:
            return mime_types[file_ext]
        else:
            # Fallback to mimetypes module
            content_type, _ = mimetypes.guess_type(file_path)
            return content_type or 'application/octet-stream'
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(f"Creating bucket: {self.bucket_name}")
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            # Don't raise the error, just log it and continue
            logger.warning("Continuing without MinIO bucket creation")
        except Exception as e:
            logger.error(f"Unexpected error ensuring bucket exists: {e}")
            logger.warning("Continuing without MinIO bucket creation")
    
    def upload_file(self, file_path: str, object_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a file to MinIO bucket
        
        Args:
            file_path: Path to the file to upload
            object_name: Name for the object in MinIO (defaults to filename)
            
        Returns:
            Dict with upload result including URL and metadata
        """
        if not self.client:
            raise Exception("MinIO client not initialized")
        
        try:
            if not object_name:
                object_name = os.path.basename(file_path)
            
            # Determine content type based on file extension
            content_type = self._get_content_type(file_path)
            
            # Upload the file with proper content type
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type
            )
            
            # Generate presigned URL for download (valid for configured time)
            from datetime import timedelta
            download_url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=self.url_expiry)
            )
            
            # Get object info
            stat = self.client.stat_object(self.bucket_name, object_name)
            
            result = {
                "success": True,
                "bucket": self.bucket_name,
                "object_name": object_name,
                "download_url": download_url,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified.isoformat(),
                "content_type": stat.content_type
            }
            
            logger.info(f"File uploaded successfully: {object_name} ({stat.size} bytes)")
            return result
            
        except S3Error as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error uploading file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def upload_from_memory(self, data: bytes, object_name: str, content_type: str = "video/mp4") -> Dict[str, Any]:
        """
        Upload data directly from memory to MinIO
        
        Args:
            data: File data as bytes
            object_name: Name for the object in MinIO
            content_type: MIME type of the file
            
        Returns:
            Dict with upload result
        """
        if not self.client:
            raise Exception("MinIO client not initialized")
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(data)
                temp_file_path = temp_file.name
            
            try:
                # Upload using the temporary file with proper content type
                return self.upload_file(temp_file_path, object_name)
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error uploading from memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def upload_stream(self, stream, object_name: str, content_type: str = "video/mp4", chunk_size: int = 8192) -> Dict[str, Any]:
        """
        Upload data directly from a stream to MinIO without saving to disk
        
        Args:
            stream: File-like object or stream to upload
            object_name: Name for the object in MinIO
            content_type: MIME type of the file
            chunk_size: Size of chunks to read from stream
            
        Returns:
            Dict with upload result
        """
        if not self.client:
            raise Exception("MinIO client not initialized")
        
        try:
            # Use put_object with stream
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=stream,
                length=-1,  # Let MinIO determine length from stream
                content_type=content_type
            )
            
            logger.info(f"Stream uploaded successfully: {object_name}")
            return {
                "success": True,
                "object_name": object_name,
                "etag": result.etag,
                "version_id": result.version_id
            }
            
        except Exception as e:
            logger.error(f"Error uploading stream: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def upload_from_url_stream(self, url: str, object_name: str, content_type: str = "video/mp4") -> Dict[str, Any]:
        """
        Download from URL and upload directly to MinIO without saving locally
        
        Args:
            url: URL to download from
            object_name: Name for the object in MinIO
            content_type: MIME type of the file
            
        Returns:
            Dict with upload result
        """
        if not self.client:
            raise Exception("MinIO client not initialized")
        
        try:
            import requests
            
            # Stream download from URL
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Create a stream wrapper that provides content length
            class StreamWrapper:
                def __init__(self, response):
                    self.response = response
                    self.content_length = int(response.headers.get('content-length', 0))
                
                def read(self, chunk_size=8192):
                    return self.response.raw.read(chunk_size)
                
                def __iter__(self):
                    return self.response.iter_content(chunk_size=8192)
            
            stream_wrapper = StreamWrapper(response)
            
            # Upload stream to MinIO
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=stream_wrapper,
                length=stream_wrapper.content_length if stream_wrapper.content_length > 0 else -1,
                content_type=content_type
            )
            
            logger.info(f"URL stream uploaded successfully: {object_name}")
            return {
                "success": True,
                "object_name": object_name,
                "etag": result.etag,
                "version_id": result.version_id,
                "size": stream_wrapper.content_length
            }
            
        except Exception as e:
            logger.error(f"Error uploading from URL stream: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO bucket
        
        Args:
            object_name: Name of the object to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File deleted successfully: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file {object_name}: {e}")
            return False
    
    def get_file_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file in MinIO
        
        Args:
            object_name: Name of the object
            
        Returns:
            Dict with file info or None if not found
        """
        if not self.client:
            return None
        
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)
            return {
                "object_name": object_name,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified.isoformat(),
                "content_type": stat.content_type
            }
        except S3Error as e:
            logger.error(f"Error getting file info for {object_name}: {e}")
            return None
    
    def list_files(self, prefix: str = "") -> list:
        """
        List files in the bucket with optional prefix
        
        Args:
            prefix: Prefix to filter files
            
        Returns:
            List of file objects
        """
        if not self.client:
            return []
        
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def generate_download_url(self, object_name: str, expires: int = None, response_headers: Dict[str, str] = None) -> Optional[str]:
        """
        Generate a presigned download URL with optional response headers
        
        Args:
            object_name: Name of the object
            expires: URL expiration time in seconds (defaults to MINIO_URL_EXPIRY from config)
            response_headers: Optional response headers to include in the URL
            
        Returns:
            Presigned URL or None if error
        """
        if not self.client:
            return None
        
        try:
            from datetime import timedelta
            # Use configured expiry time if not specified
            if expires is None:
                expires = self.url_expiry
            
            # Set default response headers for proper file download
            if response_headers is None:
                # Get file info to set proper content type
                try:
                    stat = self.client.stat_object(self.bucket_name, object_name)
                    content_type = stat.content_type
                except:
                    content_type = 'application/octet-stream'
                
                # Extract filename from object name
                filename = os.path.basename(object_name)
                
                response_headers = {
                    'response-content-type': content_type,
                    'response-content-disposition': f'attachment; filename="{filename}"'
                }
                
            return self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires),
                response_headers=response_headers
            )
        except S3Error as e:
            logger.error(f"Error generating download URL for {object_name}: {e}")
            return None

# Global MinIO storage instance
minio_storage = MinIOStorage() 