#!/usr/bin/env python3

import sys
import os
import logging
import datetime
import time
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import init_db, get_db_connection
from app.youtube_scraper import YouTubeVideoFetcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("youtube_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def process_pending_videos():
    """Process videos that have been added but not processed"""
    logger.info("Starting video processing job")
    
    # Initialize the database if needed
    init_db()
    
    # Get pending videos
    with get_db_connection() as conn:
        cursor = conn.cursor()
        pending_videos = cursor.execute(
            "SELECT * FROM videos WHERE processed = 0 LIMIT 10"
        ).fetchall()
    
    if not pending_videos:
        logger.info("No pending videos to process")
        return
    
    logger.info(f"Found {len(pending_videos)} pending videos to process")
    
    fetcher = YouTubeVideoFetcher()
    
    # Process each video
    for video in pending_videos:
        try:
            logger.info(f"Processing video: {video['video_url']}")
            fetcher.fetch_videos("video", video['video_url'])
            logger.info(f"Successfully processed video: {video['video_id']}")
        except Exception as e:
            logger.error(f"Error processing video {video['video_id']}: {e}")
            # Mark as processed anyway to avoid endless retry
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE videos SET processed = 1 WHERE id = ?", 
                    (video['id'],)
                )
                conn.commit()
        
        # Sleep to avoid rate limiting
        time.sleep(2)
    
    logger.info("Video processing job completed")

if __name__ == "__main__":
    process_pending_videos()