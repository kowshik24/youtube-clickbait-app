# YouTube Clickbait Data Collection App

A web application for collecting and labeling YouTube videos as clickbait or not clickbait. The app includes:

- Admin panel to add YouTube URLs/playlists for processing
- User panel for labeling videos
- User authentication system with password reset functionality
- Background processing of YouTube videos
- Daily user contribution tracking
- FastAPI endpoints for data export

## Features

### Admin Panel

- Add YouTube videos, playlists, or channels for processing
- View statistics on labeled data and user contributions
- Export labeled data as CSV

### User Panel

- Label videos as clickbait or not clickbait
- View contribution statistics
- Track daily contribution progress

### Authentication

- User registration and login
- Password reset via email
- Admin and regular user roles

## Project Structure

youtube-clickbait-app/
├── app/
│   ├── auth.py           # Authentication functions
│   ├── database.py       # Database operations
│   ├── youtube_scraper.py # YouTube data scraping functionality
│   ├── admin_panel.py    # Admin panel implementation
│   ├── user_panel.py     # User panel implementation
│   └── utils.py          # Utility functions
├── api/
│   ├── endpoints.py      # FastAPI endpoints
│   └── main.py           # FastAPI app setup
├── data/
│   └── thumbnails/       # Directory to store thumbnails
├── database/
│   └── clickbait_db.sqlite3 # SQLite database
├── scripts/
│   └── process_videos.py # Cron job script for processing videos
├── app.py                # Main Streamlit application
├── config.py             # Application configuration
├── Dockerfile            # For containerization
└── requirements.txt      # Dependencies


## Setup and Installation

### Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the Streamlit app: `streamlit run app.py`
4. Run the FastAPI server: `uvicorn api.main:app --reload`
5. Set up a cron job to run `scripts/process_videos.py` periodically

### Docker Deployment

1. Build the Docker image: `docker build -t youtube-clickbait-app .`
2. Run the container: `docker run -p 8501:8501 -p 8000:8000 youtube-clickbait-app`
3. Access the app at `http://localhost:8501` and the API at `http://localhost:8000`

## Usage

### Admin Account

- Default admin credentials: `admin`/`admin123`
- Change this password after first login for security

### API Endpoints

- `/api/auth` - Authenticate admin users
- `/api/export-data` - Download labeled data as CSV
- `/api/stats` - Get system statistics

## Background Processing

The application uses a cron job to process videos that have been added by admins.
This ensures that the processing of potentially large playlists or channels doesn't
block the user interface.
