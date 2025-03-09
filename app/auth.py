import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
from app.database import (
    authenticate_user, 
    create_user, 
    create_reset_token,
    validate_reset_token,
    reset_password
)

def login_user():
    """Handle user login functionality"""
    st.title("Login")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username and password:
                user = authenticate_user(username, password)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user['username']
                    st.session_state['user_id'] = user['id']
                    st.session_state['is_admin'] = bool(user['is_admin'])
                    st.success(f"Welcome back, {username}!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")
    
    with col2:
        st.write("Don't have an account?")
        if st.button("Register"):
            st.session_state['page'] = 'register'
            st.experimental_rerun()
            
        st.write("Forgot your password?")
        if st.button("Reset Password"):
            st.session_state['page'] = 'forgot_password'
            st.experimental_rerun()

def register_user():
    """Handle user registration functionality"""
    st.title("Register")
    
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    if st.button("Register"):
        if username and email and password and confirm_password:
            if password != confirm_password:
                st.error("Passwords do not match")
                return
            
            success = create_user(username, email, password)
            if success:
                st.success("Registration successful! Please log in.")
                st.session_state['page'] = 'login'
                st.experimental_rerun()
            else:
                st.error("Username or email already taken.")
        else:
            st.warning("Please fill out all fields")
    
    if st.button("Back to Login"):
        st.session_state['page'] = 'login'
        st.experimental_rerun()

def forgot_password():
    """Handle forgot password functionality"""
    st.title("Forgot Password")
    
    email = st.text_input("Enter your email address")
    
    if st.button("Send Reset Link"):
        if email:
            from app.database import get_db_connection
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                user = cursor.execute(
                    "SELECT id, username FROM users WHERE email = ?",
                    (email,)
                ).fetchone()
                
                if user:
                    token = create_reset_token(user['id'])
                    reset_url = f"http://localhost:8501/?token={token}"
                    
                    # In a real app, you would send an email
                    # Here we just display the link for demonstration purposes
                    st.info(f"Password reset link (normally sent via email): {reset_url}")
                    
                    # Attempt to send email (will need proper SMTP setup for production)
                    try:
                        msg = MIMEMultipart()
                        msg['From'] = EMAIL_HOST_USER
                        msg['To'] = email
                        msg['Subject'] = "Password Reset for YouTube Clickbait App"
                        
                        body = f"Hi {user['username']},\n\nClick the link below to reset your password:\n\n{reset_url}\n\nThis link will expire in 30 minutes.\n\nRegards,\nYouTube Clickbait App Team"
                        msg.attach(MIMEText(body, 'plain'))
                        
                        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
                        if EMAIL_USE_TLS:
                            server.starttls()
                        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
                        server.send_message(msg)
                        server.quit()
                        
                        st.success(f"Password reset instructions sent to {email}")
                    except Exception as e:
                        pass
                        
                else:
                    # We still show this message even if the email doesn't exist for security
                    st.success(f"If your email is registered, you will receive reset instructions.")
        else:
            st.warning("Please enter your email address")
    
    if st.button("Back to Login"):
        st.session_state['page'] = 'login'
        st.experimental_rerun()

def reset_password_form(token):
    """Handle password reset form"""
    st.title("Reset Password")
    
    # Validate token
    user_id = validate_reset_token(token)
    
    if user_id:
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.button("Reset Password"):
            if new_password and confirm_password:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                    return
                
                if reset_password(user_id, new_password):
                    st.success("Password has been reset successfully! Please log in.")
                    st.session_state['page'] = 'login'
                    st.experimental_rerun()
                else:
                    st.error("An error occurred. Please try again.")
            else:
                st.warning("Please enter and confirm your new password")
    else:
        st.error("Invalid or expired reset token. Please request a new password reset.")
        
        if st.button("Back to Login"):
            st.session_state['page'] = 'login'
            st.experimental_rerun()

def logout_user():
    """Log out the current user"""
    if st.button("Logout"):
        for key in ['logged_in', 'username', 'user_id', 'is_admin']:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state['page'] = 'login'
        st.experimental_rerun()