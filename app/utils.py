import os
import zipfile
import hashlib
import logging
from datetime import datetime

from config import THUMBNAILS_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def zip_directory(directory_name, zip_name):
    """Create a zip file from a directory"""
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(directory_name):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, directory_name))
        logger.info(f"{zip_name} created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating zip file: {e}")
        return False

def get_thumbnail_zip(timestamp=None):
    """Create and return a zip of thumbnails"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    zip_path = f"thumbnails_{timestamp}.zip"
    if zip_directory(THUMBNAILS_DIR, zip_path):
        return zip_path
    return None

def secure_filename(filename):
    """Generate a secure version of a filename"""
    # Remove any path component
    filename = os.path.basename(filename)
    
    # Add a timestamp and hash to make it unique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_hash = hashlib.md5(f"{filename}{timestamp}".encode()).hexdigest()[:8]
    
    # Get file extension
    name, ext = os.path.splitext(filename)
    
    # Create new filename
    new_name = f"{name}_{timestamp}_{file_hash}{ext}"
    
    return new_name