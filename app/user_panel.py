import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os

from app.database import get_unlabeled_video_for_user, save_label, get_user_stats, get_db_connection, get_instructions
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
    
    # Show labeling instructions
    with st.expander("Labeling Instructions", expanded=True):
        instructions = get_instructions()
        st.markdown(instructions)
    
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
        
        # Labeling interface
        st.subheader("Is this video clickbait?")
        
        confidence_desc = {
            1: "Not very confident",
            2: "Somewhat confident", 
            3: "Confident",
            4: "Very confident"
        }

        # Display confidence buttons
        st.write("How confident are you in your assessment?")
        confidence_cols = st.columns(4)
        confidence_level = 0
        
        for i, (level, desc) in enumerate(confidence_desc.items()):
            with confidence_cols[i]:
                if st.button(f"Level {level}\n{desc}", key=f"conf_{level}"):
                    confidence_level = level
                    st.session_state['confidence_level'] = level

        # Store confidence level in session state if not already present
        if 'confidence_level' not in st.session_state:
            st.session_state['confidence_level'] = 0
        
        # Display decision buttons
        decision_cols = st.columns(2)
        
        with decision_cols[0]:
            if st.button("Yes, it's clickbait", key="yes_button", disabled=not st.session_state['confidence_level']):
                save_label(video['id'], user_id, True, st.session_state['confidence_level'])
                st.session_state['confidence_level'] = 0
                st.success("Response recorded!")
                st.experimental_rerun()
        
        with decision_cols[1]:
            if st.button("No, it's not clickbait", key="no_button", disabled=not st.session_state['confidence_level']):
                save_label(video['id'], user_id, False, st.session_state['confidence_level'])
                st.session_state['confidence_level'] = 0
                st.success("Response recorded!")
                st.experimental_rerun()
        
        # Skip button at the bottom
        st.markdown("---")
        if st.button("Skip this video", key="skip_button"):
            # Clear the video assignment without saving any label
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE videos 
                    SET assigned_to = NULL, assigned_at = NULL 
                    WHERE id = ?
                ''', (video['id'],))
                conn.commit()
            
            st.session_state['confidence_level'] = 0
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