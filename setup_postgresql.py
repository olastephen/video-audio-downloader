#!/usr/bin/env python3
"""
PostgreSQL Setup Script for Video Downloader API
This script sets up the PostgreSQL database and user for production use.
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def run_command(command):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_postgresql_installed():
    """Check if PostgreSQL is installed"""
    success, stdout, stderr = run_command("psql --version")
    if success:
        print(f"✅ PostgreSQL found: {stdout.strip()}")
        return True
    else:
        print("❌ PostgreSQL not found. Please install PostgreSQL first.")
        print("   Download from: https://www.postgresql.org/download/")
        return False

def create_database_and_user():
    """Create database and user for the application"""
    
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'video_downloader')
    DB_USER = os.getenv('DB_USER', 'video_downloader')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'secure_password_123')
    
    print(f"🔧 Setting up PostgreSQL database...")
    print(f"   Host: {DB_HOST}")
    print(f"   Port: {DB_PORT}")
    print(f"   Database: {DB_NAME}")
    print(f"   User: {DB_USER}")
    
    try:
        # Connect to PostgreSQL as superuser
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user="postgres",
            password=os.getenv('POSTGRES_PASSWORD', 'postgres')
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create user if not exists
        print("👤 Creating database user...")
        cursor.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{DB_USER}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}'")
            print(f"✅ User '{DB_USER}' created successfully")
        else:
            print(f"ℹ️  User '{DB_USER}' already exists")
        
        # Create database if not exists
        print("🗄️ Creating database...")
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER}")
            print(f"✅ Database '{DB_NAME}' created successfully")
        else:
            print(f"ℹ️  Database '{DB_NAME}' already exists")
        
        # Grant privileges
        print("🔐 Granting privileges...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")
        cursor.execute(f"GRANT ALL ON SCHEMA public TO {DB_USER}")
        print("✅ Privileges granted successfully")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 PostgreSQL setup completed successfully!")
        print("\n📋 Environment variables to set:")
        print(f"export DB_HOST={DB_HOST}")
        print(f"export DB_PORT={DB_PORT}")
        print(f"export DB_NAME={DB_NAME}")
        print(f"export DB_USER={DB_USER}")
        print(f"export DB_PASSWORD={DB_PASSWORD}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up PostgreSQL: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your PostgreSQL superuser password")
        print("3. Ensure you have permission to create databases")
        return False

def create_env_file():
    """Create a .env file with database configuration"""
    env_content = """# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=video_downloader
DB_USER=video_downloader
DB_PASSWORD=secure_password_123

# MinIO Configuration
MINIO_ENDPOINT=minio-u39275.vm.elestio.app:34256
MINIO_ACCESS_KEY=root
MINIO_SECRET_KEY=o86Lv2Ta-x1rk-SHd5RK0B
MINIO_SECURE=true
MINIO_BUCKET=video-downloads

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Download Configuration
MAX_DOWNLOAD_SIZE=1073741824
DOWNLOAD_TIMEOUT=300
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("📄 Created .env file with database configuration")

def main():
    """Main setup function"""
    print("🚀 PostgreSQL Setup for Video Downloader API")
    print("=" * 50)
    
    # Check if PostgreSQL is installed
    if not check_postgresql_installed():
        sys.exit(1)
    
    # Create database and user
    if create_database_and_user():
        create_env_file()
        print("\n✅ Setup completed! You can now run your API with PostgreSQL.")
        print("\n📖 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Start the API: python main.py")
        print("3. Connect directly to your PostgreSQL database")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 