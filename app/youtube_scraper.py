import os
import time
import pandas as pd
import requests
from yt_dlp import YoutubeDL
import logging
from config import THUMBNAILS_DIR
from app.database import add_video, mark_video_processed

logger = logging.getLogger(__name__)

class YouTubeDataScraper:
    def __init__(self, save_dir=THUMBNAILS_DIR):
        self.save_dir = save_dir
        self.create_directories()

    def create_directories(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def download_thumbnail(self, url, video_id):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                file_path = os.path.join(self.save_dir, f"{video_id}.jpg")
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return file_path
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {e}")
        return None

    def get_video_data(self, video_url):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                video_id = info['id']
                thumbnail_url = info.get('thumbnail', '')
                thumbnail_path = self.download_thumbnail(thumbnail_url, video_id)
                
                video_data = {
                    'video_id': video_id,
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'dislike_count': info.get('dislike_count', 0),
                    'thumbnail_url': thumbnail_url,
                    'local_thumbnail_path': thumbnail_path,
                    'duration': info.get('duration', 0),
                    'upload_date': info.get('upload_date', ''),
                    'channel_id': info.get('channel_id', ''),
                    'channel_name': info.get('channel', ''),
                    'video_url': video_url
                }
                
                logger.info(f"Successfully processed video: {info['title']}")
                
                # Add to database and mark as processed
                add_video(video_data)
                mark_video_processed(video_id)
                
                return video_data
                
        except Exception as e:
            logger.error(f"Error processing video {video_url}: {e}")
            return None

    def get_channel_videos(self, channel_url, number_of_videos=100):
        """Fetch video URLs from a channel's uploads playlist."""
        try:
            if '/@' in channel_url:
                # Convert channel URL to uploads playlist URL
                channel_username = channel_url.split('/')[-1]
                playlist_url = f"https://www.youtube.com/{channel_username}/videos"
            else:
                playlist_url = channel_url
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'playlistend': number_of_videos,
            }
    
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                if 'entries' in info:
                    video_urls = [entry['url'] for entry in info['entries'] if 'url' in entry]
                    logger.info(f"Found {len(video_urls)} videos on the channel")
                    return video_urls
                else:
                    logger.info("No videos found on the channel")
                    return []
        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")
            return []

    def process_videos(self, video_urls):
        video_data_list = []
        for url in video_urls:
            logger.info(f"Processing video: {url}")
            video_data = self.get_video_data(url)
            if video_data:
                video_data_list.append(video_data)
                logger.info("Data collected successfully")
            else:
                logger.info("Failed to collect data")
            time.sleep(1)
        
        if video_data_list:
            df = pd.DataFrame(video_data_list)
            logger.info(f"Collected data for {len(video_data_list)} videos")
            return df
        else:
            logger.info("No data collected")
            return pd.DataFrame()


def get_playlist_video_urls(playlist_id):
    """Get all video URLs from a YouTube playlist"""
    # If full URL is provided, extract playlist ID
    if 'youtube.com' in playlist_id:
        if 'playlist?list=' in playlist_id:
            playlist_id = playlist_id.split('playlist?list=')[1].split('&')[0]  # Handle additional parameters
        else:
            logger.info("Invalid playlist URL")
            return []

    # Create YouTube playlist URL
    playlist_url = f'https://www.youtube.com/playlist?list={playlist_id}'
    
    # Configure yt-dlp options with additional parameters
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'force_generic_extractor': False,
        'ignoreerrors': True,  # Skip unavailable videos
        'no_color': True,
        'geo_bypass': True,
        'cookiefile': None,  # Add cookie file if needed
        'format': 'best',  # Specify format to avoid format selection issues
    }

    try:
        # Create YouTube downloader object
        with YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract playlist information
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
                if not playlist_info:
                    logger.error("Could not fetch playlist information")
                    return []

                if 'entries' not in playlist_info:
                    logger.error("No entries found in playlist")
                    return []

                # Extract video URLs
                video_urls = []
                for entry in playlist_info['entries']:
                    if entry and entry.get('id'):  # Check if entry exists and has an ID
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        video_urls.append(video_url)
                
                if not video_urls:
                    logger.warning("No valid videos found in playlist")
                    return []
                
                logger.info(f"Successfully found {len(video_urls)} videos in playlist")
                return video_urls

            except Exception as e:
                logger.error(f"Error extracting playlist info: {str(e)}")
                return []

    except Exception as e:
        logger.error(f"Error initializing YouTube downloader: {str(e)}")
        return []


class YouTubeVideoFetcher:
    def __init__(self, save_dir=THUMBNAILS_DIR):
        self.scraper = YouTubeDataScraper(save_dir=save_dir)

    def fetch_videos(self, source_type, url, no_of_videos=100):
        """
        Fetches video data from a playlist, single video, or channel.

        Parameters:
        - source_type (str): "playlist", "video", or "channel"
        - url (str): The URL or ID of the source
        - no_of_videos (int): Number of videos to fetch (for channel only)

        Returns:
        - pandas.DataFrame: Data collected from the videos
        """
        video_urls = []

        if source_type == "playlist":
            video_urls = get_playlist_video_urls(url)
        elif source_type == "video":
            video_urls = [url]
        elif source_type == "channel":
            video_urls = self.scraper.get_channel_videos(url, no_of_videos)
        else:
            logger.error("Invalid source type. Choose from 'playlist', 'video', or 'channel'.")
            return None

        if video_urls:
            df = self.scraper.process_videos(video_urls)
            
            if not df.empty:
                df = df.applymap(lambda x: x if not isinstance(x, str) else x.encode('utf-8').decode('utf-8'))
                return df
            else:
                logger.error("No data was collected.")
                return None
        else:
            logger.error("No videos found.")
            return None