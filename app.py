import streamlit as st
import os
import logging
from urllib.parse import parse_qs, urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database initialization
from app.database import init_db
from app.auth import login_user, register_user, forgot_password, reset_password_form
from app.admin_panel import render_admin_panel
from app.user_panel import render_user_panel

# Initialize the database
init_db()

def main():
    """Main Streamlit application entry point"""
    # Set up page config
    st.set_page_config(
        page_title="YouTube Clickbait Data Collection",
        page_icon="🎬",
        layout="wide",
    )
    
    # Check for password reset token in URL
    query_params = st.experimental_get_query_params()
    if "token" in query_params:
        token = query_params["token"][0]
        reset_password_form(token)
        return
    
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
    
    # Authentication flow
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        # Handle authentication pages
        if st.session_state['page'] == 'login':
            login_user()
        elif st.session_state['page'] == 'register':
            register_user()
        elif st.session_state['page'] == 'forgot_password':
            forgot_password()
    else:
        # User is logged in, show appropriate panel
        if st.session_state.get('is_admin', False):
            render_admin_panel()
        else:
            render_user_panel()

if __name__ == "__main__":
    main()