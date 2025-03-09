# Configuration settings for the application

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = os.path.join(BASE_DIR, "data")
THUMBNAILS_DIR = os.path.join(DATA_DIR, "thumbnails")
DATABASE_DIR = os.path.join(BASE_DIR, "database")

# Database
DATABASE_PATH = os.path.join(DATABASE_DIR, "clickbait_db.sqlite3")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)

# Application settings
APP_NAME = "YouTube Clickbait Data Collection"
ADMIN_PASSWORD = "admin123"  # Default admin password (should be changed in production)

# Password reset token expiration (in minutes)
TOKEN_EXPIRY_MINUTES = 30

# Email settings for password reset (configure with actual email service)
EMAIL_HOST = "smtp.example.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "noreply@example.com"
EMAIL_HOST_PASSWORD = "your-email-password"