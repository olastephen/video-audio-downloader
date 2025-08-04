# Video Downloader API

A powerful, production-ready API for downloading videos from various platforms with cloud storage integration.

## 🚀 Features

- **Multi-Platform Support**: YouTube, Vimeo, Dailymotion, TikTok, Twitter/X, Reddit, Twitch, Instagram, Facebook
- **Direct Video Downloads**: Support for direct video file URLs (.mp4, .avi, .mkv, etc.)
- **Multiple Download Libraries**: yt-dlp, pytube, youtube-dl with intelligent fallback
- **Cloud Storage**: Automatic upload to MinIO cloud storage with presigned URLs
- **Background Processing**: Asynchronous downloads with real-time status updates
- **Quality Selection**: Choose video quality and format
- **Audio Extraction**: Download audio-only versions
- **Progress Tracking**: Real-time download progress monitoring
- **Rate Limiting**: Built-in rate limiting to prevent abuse
- **Database Integration**: PostgreSQL support for persistent task storage
- **Production Ready**: Docker support, health checks, and monitoring

## 📋 Supported Platforms

### ✅ **Fully Supported**
- **YouTube** - Full support with quality selection
- **Vimeo** - High-quality video downloads
- **Dailymotion** - Complete video extraction
- **TikTok** - Video and audio downloads
- **Twitter/X** - Video content extraction
- **Reddit** - Video posts and comments
- **Twitch** - Stream and clip downloads
- **Instagram** - Posts, stories, and reels
- **Facebook** - Video posts and stories
- **Direct Video URLs** - Any direct video file link

### 🔧 **Technical Features**
- **Multiple Download Engines**: yt-dlp, pytube, youtube-dl
- **Intelligent Fallback**: Automatic switching between download methods
- **Format Conversion**: MP4, WebM, AVI, MKV support
- **Quality Options**: Best, worst, specific resolutions
- **Subtitle Support**: Automatic subtitle downloads
- **Metadata Extraction**: Title, duration, uploader info

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (optional, for production)
- MinIO (optional, for cloud storage)

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd video-downloader

# Install dependencies
pip install -r requirements.txt

# Start the API
python main.py
```

### Environment Configuration
Create a `.env` file or set environment variables:

```bash
# Database Configuration (Optional)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=video_downloader
DB_USER=video_downloader
DB_PASSWORD=secure_password_123

# MinIO Configuration (Optional)
MINIO_ENDPOINT=your-minio-endpoint:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_SECURE=true
MINIO_BUCKET=video-downloads
MINIO_URL_EXPIRY=43200  # 12 hours in seconds (43200 = 12 * 60 * 60)

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Download Configuration
MAX_DOWNLOAD_SIZE=1073741824
DOWNLOAD_TIMEOUT=300
LOCAL_STORAGE_FALLBACK=true
```

## 🚀 Usage

### API Endpoints

#### 1. **Download Video**
```http
POST /download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "best",
  "format": "mp4",
  "audio_only": false
}
```

**Response:**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "started",
  "message": "Download task started successfully"
}
```

#### 2. **Check Download Status**
```http
GET /status/{task_id}
```

**Response:**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100.0,
  "filename": "Rick Astley - Never Gonna Give You Up.mp4",
  "download_url": "https://minio.example.com/presigned-url",
  "file_size": 5242880
}
```

#### 3. **Download File**
```http
GET /download_file/{task_id}
```

**Note**: This endpoint redirects to a MinIO presigned URL that expires after 12 hours. The expiration time can be configured via the `MINIO_URL_EXPIRY` environment variable.

#### 4. **Get Video Information**
```http
GET /video_info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

#### 5. **MinIO Management**
```http
GET /minio/files                    # List all files
DELETE /minio/files/{object_name}   # Delete specific file
```

### Example Usage

#### Python Client
```python
import requests

# Start download
response = requests.post("http://localhost:8000/download", json={
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "quality": "best",
    "format": "mp4"
})

task_id = response.json()["task_id"]

# Check status
status = requests.get(f"http://localhost:8000/status/{task_id}")
print(status.json())
```

#### cURL Examples
```bash
# Download YouTube video
curl -X POST "http://localhost:8000/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "quality": "best",
    "format": "mp4"
  }'

# Check status
curl "http://localhost:8000/status/{task_id}"

# Download file
curl "http://localhost:8000/download_file/{task_id}" -o video.mp4
```

## 🐳 Docker Deployment

### Using Docker Compose
```bash
# Start with PostgreSQL and MinIO
docker-compose -f docker-compose.prod.yml up -d

# Access services
# API: http://localhost:8000
# PostgreSQL: Direct connection to postgres-u39275.vm.elestio.app:5432
```

### Manual Docker Build
```bash
# Build image
docker build -t video-downloader .

# Run container
docker run -p 8000:8000 video-downloader
```

## 📊 Database Integration

The API supports PostgreSQL for persistent storage:

- **Task Tracking**: All download tasks are stored in the database
- **Status History**: Complete download history and statistics
- **User Management**: Track downloads by client IP
- **Cleanup**: Automatic cleanup of old tasks

### Database Schema
```sql
CREATE TABLE download_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    progress FLOAT DEFAULT 0.0,
    filename TEXT,
    download_url TEXT,
    storage_type VARCHAR(50) DEFAULT 'local',
    file_size BIGINT,
    client_ip VARCHAR(45),
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Configuration

### Download Options
- **Quality**: `best`, `worst`, `720p`, `1080p`, etc.
- **Format**: `mp4`, `webm`, `avi`, `mkv`
- **Audio Only**: Extract audio tracks only
- **Subtitles**: Download available subtitles

### Storage Options
- **Local Storage**: Files stored on server disk
- **MinIO Cloud**: Automatic upload to cloud storage
- **Presigned URLs**: Secure, time-limited download links
- **Cleanup**: Automatic local file cleanup

## 🚨 Rate Limiting

The API includes built-in rate limiting:
- **10 requests per minute** per IP address
- **Configurable limits** via environment variables
- **Automatic blocking** of abusive clients

## 🔍 Monitoring

### Health Checks
```http
GET /health
```

### Statistics
- Download success rates
- Platform usage statistics
- Storage utilization
- Performance metrics

## 🛡️ Security

- **Input Validation**: All URLs and parameters validated
- **File Type Checking**: Automatic file type verification
- **Size Limits**: Configurable maximum file sizes
- **Access Control**: IP-based rate limiting
- **Secure URLs**: Time-limited presigned URLs

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the API logs

---

**Note**: This API is designed for legitimate video downloads. Please respect copyright laws and terms of service of video platforms. 