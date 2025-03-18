import sqlite3
import time
import datetime
import pandas as pd
import os
import uuid
import hashlib
import secrets
from contextlib import contextmanager

from config import DATABASE_PATH

# Create tables if they don't exist
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Reset tokens table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Videos table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            title TEXT,
            description TEXT,
            view_count INTEGER,
            like_count INTEGER,
            thumbnail_url TEXT,
            local_thumbnail_path TEXT,
            duration INTEGER,
            upload_date TEXT,
            channel_id TEXT,
            channel_name TEXT,
            video_url TEXT,
            processed BOOLEAN DEFAULT 0,
            assigned_to INTEGER DEFAULT NULL,
            assigned_at TIMESTAMP DEFAULT NULL,
            FOREIGN KEY (assigned_to) REFERENCES users (id)
        )
        ''')
        
        # Labels table (for user contributions)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            is_clickbait BOOLEAN NOT NULL,
            confidence_level INTEGER NOT NULL CHECK(confidence_level BETWEEN 1 AND 4),
            labeled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Add confidence_level column if it doesn't exist
        try:
            cursor.execute('ALTER TABLE labels ADD COLUMN confidence_level INTEGER NOT NULL DEFAULT 3 CHECK(confidence_level BETWEEN 1 AND 4)')
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Daily stats table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            contribution_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE (user_id, date)
        )
        ''')
        
        # Add skipped_videos table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS skipped_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(video_id, user_id)
        )
        ''')
        
        # Create default admin user if it doesn't exist
        cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, is_admin)
        VALUES (?, ?, ?, 1)
        ''', ('admin', 'admin@example.com', hash_password('admin123')))
        
        conn.commit()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Authentication and user management functions
def hash_password(password):
    """Create a salted hash of the password"""
    salt = secrets.token_hex(16)
    h = hashlib.sha256()
    h.update(f"{salt}:{password}".encode())
    return f"{salt}:{h.hexdigest()}"

def check_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    salt, hash_value = stored_password.split(":", 1)
    h = hashlib.sha256()
    h.update(f"{salt}:{provided_password}".encode())
    return h.hexdigest() == hash_value

def authenticate_user(username, password):
    """Authenticate a user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = cursor.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        
        if user and check_password(user['password_hash'], password):
            return dict(user)
        return None

def create_user(username, email, password, is_admin=False):
    """Create a new user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                (username, email, hash_password(password), is_admin)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def create_reset_token(user_id):
    """Create a password reset token"""
    token = secrets.token_urlsafe(32)
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=30)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Delete any existing tokens for the user
        cursor.execute("DELETE FROM reset_tokens WHERE user_id = ?", (user_id,))
        # Create new token
        cursor.execute(
            "INSERT INTO reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expiry)
        )
        conn.commit()
    
    return token

def validate_reset_token(token):
    """Validate a password reset token"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        token_data = cursor.execute(
            "SELECT user_id, expires_at FROM reset_tokens WHERE token = ?",
            (token,)
        ).fetchone()
        
        if not token_data:
            return None
        
        expires_at = datetime.datetime.fromisoformat(token_data['expires_at'])
        if datetime.datetime.now() > expires_at:
            # Token expired, delete it
            cursor.execute("DELETE FROM reset_tokens WHERE token = ?", (token,))
            conn.commit()
            return None
        
        return token_data['user_id']

def reset_password(user_id, new_password):
    """Reset user password"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id)
        )
        # Delete the used token
        cursor.execute("DELETE FROM reset_tokens WHERE user_id = ?", (user_id,))
        conn.commit()
        return True

# Video management functions
def add_video(video_data):
    """Add a video to the database"""
    required_fields = [
        'video_id', 'title', 'description', 'view_count', 
        'like_count', 'thumbnail_url', 'duration', 'upload_date',
        'channel_id', 'channel_name', 'video_url'
    ]
    
    # Validate required fields
    for field in required_fields:
        if field not in video_data:
            raise ValueError(f"Missing required field: {field}")
            
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Check if video already exists
            existing = cursor.execute(
                "SELECT id FROM videos WHERE video_id = ?", 
                (video_data['video_id'],)
            ).fetchone()
            
            if existing:
                # Update existing record
                cursor.execute('''
                UPDATE videos SET 
                    title = ?,
                    description = ?,
                    view_count = ?,
                    like_count = ?,
                    thumbnail_url = ?,
                    local_thumbnail_path = ?,
                    duration = ?,
                    upload_date = ?,
                    channel_id = ?,
                    channel_name = ?,
                    video_url = ?
                WHERE video_id = ?
                ''', (
                    video_data['title'],
                    video_data['description'],
                    video_data['view_count'],
                    video_data['like_count'],
                    video_data['thumbnail_url'],
                    video_data['local_thumbnail_path'],
                    video_data['duration'],
                    video_data['upload_date'],
                    video_data['channel_id'],
                    video_data['channel_name'],
                    video_data['video_url'],
                    video_data['video_id']
                ))
            else:
                # Insert new record
                cursor.execute('''
                INSERT INTO videos 
                (video_id, title, description, view_count, like_count, 
                 thumbnail_url, local_thumbnail_path, duration, upload_date,
                 channel_id, channel_name, video_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video_data['video_id'],
                    video_data['title'],
                    video_data['description'],
                    video_data['view_count'],
                    video_data['like_count'],
                    video_data['thumbnail_url'],
                    video_data['local_thumbnail_path'],
                    video_data['duration'],
                    video_data['upload_date'],
                    video_data['channel_id'],
                    video_data['channel_name'],
                    video_data['video_url']
                ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding video: {e}")
            return False

def get_unlabeled_video_for_user(user_id):
    """Get an unlabeled video and assign it to a user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # First check if the user already has an assigned video
        assigned_video = cursor.execute('''
            SELECT * FROM videos 
            WHERE assigned_to = ? 
            AND id NOT IN (SELECT video_id FROM labels WHERE user_id = ?)
            AND id NOT IN (SELECT video_id FROM skipped_videos WHERE user_id = ?)
            LIMIT 1
        ''', (user_id, user_id, user_id)).fetchone()
        
        if assigned_video:
            return dict(assigned_video)
        
        # Get a video that hasn't been labeled by this user, hasn't been skipped,
        # and isn't assigned to anyone
        current_time = datetime.datetime.now().isoformat()
        video = cursor.execute('''
            SELECT * FROM videos 
            WHERE processed = 1 
            AND (assigned_to IS NULL OR 
                (julianday(?) - julianday(assigned_at)) * 24 * 60 > 15)
            AND id NOT IN (SELECT video_id FROM labels)
            AND id NOT IN (SELECT video_id FROM skipped_videos WHERE user_id = ?)
            LIMIT 1
        ''', (current_time, user_id)).fetchone()
        
        if video:
            # Assign the video to this user
            cursor.execute('''
                UPDATE videos 
                SET assigned_to = ?, assigned_at = ? 
                WHERE id = ?
            ''', (user_id, current_time, video['id']))
            conn.commit()
            return dict(video)
        
        return None

def save_label(video_id, user_id, is_clickbait, confidence_level):
    """Save a user's label for a video and update daily stats"""
    current_date = datetime.date.today().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Save the label with confidence level
        cursor.execute('''
            INSERT INTO labels (video_id, user_id, is_clickbait, confidence_level) 
            VALUES (?, ?, ?, ?)
        ''', (video_id, user_id, is_clickbait, confidence_level))
        
        # Update daily stats
        cursor.execute('''
            INSERT INTO daily_stats (user_id, date, contribution_count) 
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, date) 
            DO UPDATE SET contribution_count = contribution_count + 1
        ''', (user_id, current_date))
        
        # Clear assignment
        cursor.execute('''
            UPDATE videos 
            SET assigned_to = NULL, assigned_at = NULL 
            WHERE id = ?
        ''', (video_id,))
        
        conn.commit()
        return True

def skip_video(video_id, user_id):
    """Record a skipped video and clear its assignment"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Get the internal video ID first
            video = cursor.execute(
                "SELECT id FROM videos WHERE video_id = ?", 
                (video_id,)
            ).fetchone()
            
            if not video:
                return False
                
            # Record the skip
            cursor.execute('''
                INSERT INTO skipped_videos (video_id, user_id)
                VALUES (?, ?)
            ''', (video['id'], user_id))
            
            # Clear the assignment
            cursor.execute('''
                UPDATE videos 
                SET assigned_to = NULL, assigned_at = NULL 
                WHERE video_id = ?
            ''', (video_id,))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Video was already skipped by this user
            return False

def get_user_stats(user_id):
    """Get user contribution statistics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get total contributions
        total = cursor.execute('''
            SELECT COUNT(*) as count FROM labels WHERE user_id = ?
        ''', (user_id,)).fetchone()['count']
        
        # Get daily breakdown for the past 7 days
        today = datetime.date.today()
        daily_stats = []
        
        for i in range(7):
            date = (today - datetime.timedelta(days=i)).isoformat()
            stat = cursor.execute('''
                SELECT contribution_count FROM daily_stats 
                WHERE user_id = ? AND date = ?
            ''', (user_id, date)).fetchone()
            
            daily_stats.append({
                'date': date,
                'count': stat['contribution_count'] if stat else 0
            })
        
        return {
            'total': total,
            'daily': daily_stats
        }

def get_all_labeled_data():
    """Get all labeled data for export"""
    with get_db_connection() as conn:
        query = '''
        SELECT 
            v.video_id, v.title, v.description, v.view_count, 
            v.like_count, v.thumbnail_url, v.duration, v.upload_date,
            v.channel_id, v.channel_name, v.video_url,
            l.is_clickbait, l.confidence_level, u.username as labeled_by, l.labeled_at
        FROM 
            labels l
        JOIN 
            videos v ON l.video_id = v.id
        JOIN 
            users u ON l.user_id = u.id
        ORDER BY 
            l.labeled_at DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        return df

def get_admin_dashboard_stats():
    """Get statistics for the admin dashboard"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Total videos in system
        total_videos = cursor.execute(
            "SELECT COUNT(*) as count FROM videos"
        ).fetchone()['count']
        
        # Processed videos
        processed_videos = cursor.execute(
            "SELECT COUNT(*) as count FROM videos WHERE processed = 1"
        ).fetchone()['count']
        
        # Labeled videos
        labeled_videos = cursor.execute(
            "SELECT COUNT(DISTINCT video_id) as count FROM labels"
        ).fetchone()['count']
        
        # Total users
        total_users = cursor.execute(
            "SELECT COUNT(*) as count FROM users WHERE is_admin = 0"
        ).fetchone()['count']
        
        # Top contributors
        top_contributors = cursor.execute('''
            SELECT u.username, COUNT(*) as contribution_count
            FROM labels l
            JOIN users u ON l.user_id = u.id
            GROUP BY l.user_id
            ORDER BY contribution_count DESC
            LIMIT 5
        ''').fetchall()
        
        top_contributors = [
            {'username': row['username'], 'count': row['contribution_count']}
            for row in top_contributors
        ]
        
        return {
            'total_videos': total_videos,
            'processed_videos': processed_videos,
            'labeled_videos': labeled_videos,
            'total_users': total_users,
            'top_contributors': top_contributors
        }

# Mark videos as processed after background processing
def mark_video_processed(video_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE videos SET processed = 1 WHERE video_id = ?", 
            (video_id,)
        )
        conn.commit()
        return True

# Global variable to store labeling instructions
_labeling_instructions = """Default labeling instructions:
1. Watch the video title and thumbnail carefully
2. Determine if it's clickbait based on misleading content
3. Rate your confidence level from 1-4"""

def save_instructions(instructions):
    """Save labeling instructions to memory"""
    global _labeling_instructions
    _labeling_instructions = instructions

def get_instructions():
    """Get current labeling instructions from memory"""
    return _labeling_instructions