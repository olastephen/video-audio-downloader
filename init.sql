-- PostgreSQL Database Initialization Script
-- This script sets up the database schema for the Video Downloader API

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create download_tasks table
CREATE TABLE IF NOT EXISTS download_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'starting',
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_download_tasks_task_id ON download_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_download_tasks_status ON download_tasks(status);
CREATE INDEX IF NOT EXISTS idx_download_tasks_created_at ON download_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_download_tasks_client_ip ON download_tasks(client_ip);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_download_tasks_updated_at 
    BEFORE UPDATE ON download_tasks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions to the application user
GRANT ALL PRIVILEGES ON TABLE download_tasks TO video_downloader;
GRANT USAGE, SELECT ON SEQUENCE download_tasks_id_seq TO video_downloader;

-- Create a view for recent downloads
CREATE OR REPLACE VIEW recent_downloads AS
SELECT 
    task_id,
    url,
    status,
    progress,
    file_size,
    client_ip,
    created_at,
    updated_at
FROM download_tasks
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY created_at DESC;

GRANT SELECT ON recent_downloads TO video_downloader;

-- Create a view for download statistics
CREATE OR REPLACE VIEW download_stats AS
SELECT 
    status,
    COUNT(*) as count,
    AVG(progress) as avg_progress,
    AVG(file_size) as avg_file_size,
    MIN(created_at) as first_download,
    MAX(created_at) as last_download
FROM download_tasks
GROUP BY status;

GRANT SELECT ON download_stats TO video_downloader;

-- Insert some sample data for testing (optional)
-- INSERT INTO download_tasks (task_id, url, status, progress) VALUES 
-- ('sample-1', 'https://example.com/video1.mp4', 'completed', 100.0),
-- ('sample-2', 'https://example.com/video2.mp4', 'downloading', 45.5);

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL database initialized successfully for Video Downloader API';
END $$; 