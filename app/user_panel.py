import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os

from app.database import get_unlabeled_video_for_user, save_label, get_user_stats
from app.auth import logout_user

def render_user_panel():
    """Render the user panel"""
    st.title("YouTube Clickbait Data Labeling")
    
    st.sidebar.write(f"Logged in as: {st.session_state['username']}")
    logout_user()
    
    tabs = st.tabs(["Label Videos", "My Stats"])
    
    with tabs[0]:
        render_labeling_interface()
    
    with tabs[1]:
        render_user_stats()

def render_labeling_interface():
    """Render interface for labeling videos"""
    st.header("Label Videos")
    
    user_id = st.session_state['user_id']
    
    # Get a video for the user to label
    video = get_unlabeled_video_for_user(user_id)
    
    if video:
        # Display video information
        with st.expander("Video Information", expanded=True):
            if os.path.exists(video['local_thumbnail_path']):
                image = mpimg.imread(video['local_thumbnail_path'])
                st.image(image, caption=video['title'])
            else:
                st.warning("Thumbnail not available")
            
            st.write(f"**Title:** {video['title']}")
            st.subheader("Description:")
            st.write(video['description'])
            st.write(f"**Channel:** {video['channel_name']}")
            st.write(f"**Views:** {video['view_count']:,}")
            st.write(f"**Likes:** {video['like_count']:,}")
        
        # Labeling buttons
        st.subheader("Is this video clickbait?")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Yes, it's clickbait", key="yes_button"):
                save_label(video['id'], user_id, True)
                st.success("Response recorded!")
                st.experimental_rerun()
        
        with col2:
            if st.button("No, it's not clickbait", key="no_button"):
                save_label(video['id'], user_id, False)
                st.success("Response recorded!")
                st.experimental_rerun()
                
        # Optional: View on YouTube link
        st.markdown(f"[View on YouTube]({video['video_url']})")
        
    else:
        st.info("No more videos available for labeling at the moment. Please check back later.")

def render_user_stats():
    """Render user statistics"""
    st.header("My Contribution Statistics")
    
    user_id = st.session_state['user_id']
    stats = get_user_stats(user_id)
    
    # Display total contributions
    st.metric("Total Contributions", stats['total'])
    
    # Display daily contributions chart
    st.subheader("Daily Contributions (Last 7 Days)")
    
    daily_data = pd.DataFrame(stats['daily'])
    
    # Create a bar chart
    if not daily_data.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(daily_data['date'], daily_data['count'])
        ax.set_xlabel('Date')
        ax.set_ylabel('Number of Contributions')
        ax.set_title('Your Daily Contributions')
        plt.xticks(rotation=45, ha='right')
        
        st.pyplot(fig)
    else:
        st.write("No contribution data available yet.")