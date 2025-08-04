# Social Media Info Extractor API

A lightweight, fast API to extract comprehensive metadata from social media posts across multiple platforms.

## 🌟 Features

- **Multi-Platform Support**: TikTok, YouTube, Instagram, Facebook, Twitter/X, Reddit, Pinterest, and more
- **Comprehensive Metadata**: Extract title, author, description, thumbnail, media URLs, and more
- **No Downloads**: Pure information extraction - no files are downloaded or stored
- **Fast & Efficient**: Optimized for quick metadata extraction (1-3 seconds)
- **Ultra Lightweight**: No database or storage required - completely stateless
- **RESTful API**: Clean, easy-to-use endpoints

## 🚀 Supported Platforms

- **TikTok** - Videos, audio, thumbnails, metadata
- **YouTube** - Videos, audio, thumbnails, metadata
- **Instagram** - Posts, reels, stories, metadata
- **Facebook** - Videos, posts, metadata
- **Twitter/X** - Tweets, videos, images, metadata
- **Reddit** - Posts, videos, images, metadata
- **Pinterest** - Pins, images, metadata
- **Snapchat** - Stories, snaps, metadata
- **LinkedIn** - Posts, videos, metadata
- **Twitch** - Streams, clips, metadata
- **Vimeo** - Videos, metadata
- **Dailymotion** - Videos, metadata

## 📋 API Endpoints

### Extract Information
```http
POST /extract
```

**Request Body:**
```json
{
  "url": "https://www.tiktok.com/@username/video/1234567890",
  "include_media_urls": true,
  "include_thumbnail": true,
  "include_audio": false
}
```

**Response:**
```json
{
  "url": "https://www.tiktok.com/@username/video/1234567890",
  "source": "tiktok",
  "id": "1234567890",
  "unique_id": "username",
  "author": "username",
  "title": "Amazing video title",
  "description": "Video description...",
  "thumbnail": "https://example.com/thumbnail.jpg",
  "duration": 88447,
  "view_count": 1000000,
  "like_count": 50000,
  "comment_count": 1000,
  "share_count": 500,
  "upload_date": "20240101",
  "medias": [
    {
      "url": "https://example.com/video.mp4",
      "data_size": 5466143,
      "quality": "hd_no_watermark",
      "extension": "mp4",
      "type": "video",
      "duration": 88447
    }
  ],
  "type": "single",
  "error": false,
  "error_message": null,
  "extraction_time": 1.234
}
```

### Get Supported Platforms
```http
GET /platforms
```

### Health Check
```http
GET /health
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/social-media-info-extractor.git
cd social-media-info-extractor
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables (optional):**
```bash
cp env_template.txt .env
# Edit .env with your configuration
```

4. **Run the API:**
```bash
python main.py
```

## ⚙️ Configuration

### Environment Variables

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Extraction Configuration
EXTRACTION_TIMEOUT=30
MAX_URL_LENGTH=2048
```

## 🔧 Usage Examples

### Python
```python
import requests

# Extract information from TikTok
response = requests.post("http://localhost:8000/extract", json={
    "url": "https://www.tiktok.com/@username/video/1234567890",
    "include_media_urls": True,
    "include_thumbnail": True
})

data = response.json()
print(f"Title: {data['title']}")
print(f"Author: {data['author']}")
print(f"Duration: {data['duration']} seconds")
```

### JavaScript/Node.js
```javascript
const response = await fetch('http://localhost:8000/extract', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        url: 'https://www.tiktok.com/@username/video/1234567890',
        include_media_urls: true,
        include_thumbnail: true
    })
});

const data = await response.json();
console.log(`Title: ${data.title}`);
console.log(`Author: ${data.author}`);
```

### cURL
```bash
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.tiktok.com/@username/video/1234567890",
       "include_media_urls": true,
       "include_thumbnail": true
     }'
```

## 🚀 Deployment

### Docker
```bash
docker build -t social-media-info-extractor .
docker run -p 8000:8000 social-media-info-extractor
```

### Docker Compose
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📈 Performance

- **Extraction Time**: Typically 1-3 seconds per request
- **Concurrent Requests**: No artificial limits
- **Memory Usage**: Minimal (no file storage)
- **Dependencies**: Only essential packages (6 total)
- **Startup Time**: < 1 second

## 🔒 Security

- **No File Storage**: Only metadata extraction
- **Input Validation**: URL validation and sanitization
- **Rate Limiting**: Handled by RapidAPI (if deployed there)
- **Stateless**: No persistent data storage
- **No External Storage**: Completely self-contained

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the API endpoints

## 🔄 Changelog

### v2.0.0
- Complete rewrite to focus on information extraction
- Removed download functionality
- Removed database dependencies
- Removed MinIO storage dependencies
- Added comprehensive metadata extraction
- Improved platform detection
- Enhanced error handling
- Ultra lightweight and stateless design
- Only 6 essential dependencies

### v1.0.0
- Initial release with download functionality 