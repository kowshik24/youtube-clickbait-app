import streamlit as st
import pandas as pd
import io
import datetime
import matplotlib.pyplot as plt
import json

from app.database import get_admin_dashboard_stats, get_all_labeled_data
from app.youtube_scraper import YouTubeVideoFetcher
from app.auth import logout_user

def render_admin_panel():
    """Render the admin panel"""
    st.title("YouTube Clickbait Admin Panel")
    
    st.sidebar.write(f"Logged in as: {st.session_state['username']} (Admin)")
    logout_user()
    
    tabs = st.tabs(["Dashboard", "Add Videos", "Upload CSV", "View Data", "Export Data"])
    
    with tabs[0]:
        render_admin_dashboard()
    
    with tabs[1]:
        render_add_videos()
    
    with tabs[2]:
        render_csv_upload()
    
    with tabs[3]:
        render_view_data()
    
    with tabs[4]:
        render_export_data()

def render_admin_dashboard():
    """Render admin dashboard with statistics"""
    st.header("Dashboard")
    
    # Get statistics
    stats = get_admin_dashboard_stats()
    
    # Display summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Videos", stats['total_videos'])
    
    with col2:
        st.metric("Processed Videos", stats['processed_videos'])
    
    with col3:
        st.metric("Labeled Videos", stats['labeled_videos'])
    
    with col4:
        st.metric("Total Users", stats['total_users'])
    
    # Top contributors
    st.subheader("Top Contributors")
    if stats['top_contributors']:
        contributor_df = pd.DataFrame(stats['top_contributors'])
        
        # Display as chart
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(contributor_df['username'], contributor_df['count'])
        ax.set_xlabel('User')
        ax.set_ylabel('Number of Contributions')
        ax.set_title('Top Contributors')
        plt.xticks(rotation=45, ha='right')
        
        st.pyplot(fig)
    else:
        st.write("No contributions yet.")

def render_add_videos():
    """Render form to add videos"""
    st.header("Add YouTube Videos for Processing")
    
    source_type = st.selectbox(
        "Select Source Type", 
        ["video", "playlist", "channel"]
    )
    
    url = st.text_input("Enter YouTube URL")
    
    num_videos = 100
    if source_type == "channel":
        num_videos = st.number_input(
            "Number of videos to fetch (for channels)", 
            min_value=1, 
            max_value=500, 
            value=100
        )
    
    if st.button("Add Videos for Processing"):
        if url:
            with st.spinner(f"Processing {source_type}..."):
                try:
                    fetcher = YouTubeVideoFetcher()
                    df = fetcher.fetch_videos(source_type, url, no_of_videos=num_videos)
                    
                    if df is not None and not df.empty:
                        st.success(f"Successfully added {len(df)} videos for processing!")
                    else:
                        st.error("No videos were found or could be processed.")
                except Exception as e:
                    st.error(f"Error processing {source_type}: {str(e)}")
        else:
            st.warning("Please enter a URL")

def render_csv_upload():
    """Render CSV upload interface"""
    st.header("Upload Video Data CSV")
    
    # Instructions
    st.write("""
    Upload a CSV file containing video data with the following columns:
    ```
    Required columns:
    - video_id        : YouTube video ID
    - title          : Video title
    - description    : Video description
    - view_count     : Number of views
    - like_count     : Number of likes
    - thumbnail_url  : URL of video thumbnail
    - duration       : Video duration in seconds
    - upload_date    : Video upload date
    - channel_id     : YouTube channel ID
    - channel_name   : Channel name
    - video_url      : Full video URL
    ```
    """)
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            expected_columns = [
                'video_id', 'title', 'description', 'view_count', 
                'like_count', 'thumbnail_url', 'duration', 'upload_date',
                'channel_id', 'channel_name', 'video_url'
            ]
            
            # Check for missing columns
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
                return
            
            # Preview the data
            st.write("Preview of uploaded data:")
            st.dataframe(df.head())
            
            # Additional statistics
            st.write("Dataset Statistics:")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"Total videos: {len(df)}")
                st.write(f"Unique channels: {df['channel_name'].nunique()}")
            with col2:
                st.write(f"Date range: {df['upload_date'].min()} to {df['upload_date'].max()}")
            
            if st.button("Process CSV Data"):
                with st.spinner("Processing videos from CSV..."):
                    success_count = 0
                    error_count = 0
                    progress_bar = st.progress(0)
                    
                    for idx, row in df.iterrows():
                        try:
                            video_data = {
                                'video_id': str(row['video_id']),
                                'title': str(row['title']),
                                'description': str(row['description']),
                                'view_count': int(row['view_count']),
                                'like_count': int(row['like_count']),
                                'thumbnail_url': str(row['thumbnail_url']),
                                'duration': int(row['duration']),
                                'upload_date': str(row['upload_date']),
                                'channel_id': str(row['channel_id']),
                                'channel_name': str(row['channel_name']),
                                'video_url': str(row['video_url']),
                                'local_thumbnail_path': None
                            }
                            
                            # Download thumbnail
                            from app.youtube_scraper import YouTubeDataScraper
                            scraper = YouTubeDataScraper()
                            video_data['local_thumbnail_path'] = scraper.download_thumbnail(
                                video_data['thumbnail_url'],
                                video_data['video_id']
                            )
                            
                            # Add to database
                            from app.database import add_video, mark_video_processed
                            if add_video(video_data):
                                mark_video_processed(video_data['video_id'])
                                success_count += 1
                        except Exception as e:
                            error_count += 1
                            st.error(f"Error processing video {row['video_id']}: {str(e)}")
                        
                        # Update progress
                        progress_bar.progress((idx + 1) / len(df))
                    
                    st.success(f"""
                    Processing complete!
                    - Successfully processed: {success_count} videos
                    - Errors: {error_count} videos
                    """)
                    
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

def render_view_data():
    """View collected and labeled data"""
    st.header("View Labeled Data")
    
    df = get_all_labeled_data()
    
    if not df.empty:
        st.write(f"Total records: {len(df)}")
        st.dataframe(df)
    else:
        st.info("No labeled data available yet.")

def render_export_data():
    """Export data as CSV"""
    st.header("Export Data")
    
    df = get_all_labeled_data()
    
    if not df.empty:
        # Create a download link
        csv = df.to_csv(index=False)
        current_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"youtube_clickbait_data_{current_date}.csv"
        
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )
    else:
        st.info("No data available for export.")