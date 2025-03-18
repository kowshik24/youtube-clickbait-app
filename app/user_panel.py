import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os

from app.database import (
    get_unlabeled_video_for_user, 
    save_label, 
    get_user_stats, 
    get_db_connection, 
    get_instructions,
    skip_video
)
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
    user_id = st.session_state['user_id']
    
    # Display labeling instructions
    instructions = get_instructions()
    with st.expander("Labeling Instructions", expanded=False):
        st.markdown(instructions)
    
    video = get_unlabeled_video_for_user(user_id)
    
    if not video:
        st.info("No more videos available for labeling at the moment!")
        return

    # Display video details
    st.markdown(f"### {video['title']}")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(video['thumbnail_url'])
    with col2:
        st.write(video['description'][:500] + "..." if len(video['description']) > 500 else video['description'])
        st.write(f"Views: {video['view_count']} | Likes: {video['like_count']}")
        st.markdown(f"[Watch on YouTube]({video['video_url']})")

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
    decision_cols = st.columns(3)
    
    with decision_cols[0]:
        if st.button("Yes, it's clickbait", disabled=not st.session_state['confidence_level']):
            save_label(video['id'], user_id, True, st.session_state['confidence_level'])
            st.session_state['confidence_level'] = 0
            st.success("Response recorded!")
            st.experimental_rerun()
    
    with decision_cols[1]:
        if st.button("No, it's not clickbait", disabled=not st.session_state['confidence_level']):
            save_label(video['id'], user_id, False, st.session_state['confidence_level'])
            st.session_state['confidence_level'] = 0
            st.success("Response recorded!")
            st.experimental_rerun()
            
    with decision_cols[2]:
        if st.button("Skip this video"):
            if skip_video(video['video_id'], user_id):
                st.success("Video skipped successfully!")
                st.experimental_rerun()
            else:
                st.error("Failed to skip video. You may have already skipped this video before.")

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