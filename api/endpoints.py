from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import os
import datetime

from app.database import get_db_connection, get_all_labeled_data
from app.utils import secure_filename

router = APIRouter()

class AuthRequest(BaseModel):
    username: str
    password: str

class DataResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

@router.post("/api/auth", response_model=DataResponse)
async def authenticate(auth_req: AuthRequest):
    """Authenticate admin for API access"""
    from app.database import authenticate_user
    
    user = authenticate_user(auth_req.username, auth_req.password)
    
    if user and user['is_admin']:
        return {
            "success": True,
            "message": "Authentication successful",
            "data": {"user_id": user['id'], "username": user['username']}
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )

@router.get("/api/export-data")
async def export_data(username: str, password: str):
    """Export labeled data as CSV"""
    from app.database import authenticate_user
    
    # Authenticate
    user = authenticate_user(username, password)
    
    if not user or not user['is_admin']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access",
        )
    
    # Get data
    df = get_all_labeled_data()
    
    if df.empty:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "No data available"}
        )
    
    # Create CSV file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"youtube_clickbait_data_{timestamp}.csv"
    filepath = f"/tmp/{filename}"
    
    df.to_csv(filepath, index=False)
    
    # Return file
    return FileResponse(
        path=filepath, 
        filename=filename,
        media_type="text/csv"
    )

@router.get("/api/stats")
async def get_stats(username: str, password: str):
    """Get system statistics"""
    from app.database import authenticate_user, get_admin_dashboard_stats
    
    # Authenticate
    user = authenticate_user(username, password)
    
    if not user or not user['is_admin']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access",
        )
    
    # Get stats
    stats = get_admin_dashboard_stats()
    
    return {
        "success": True,
        "message": "Statistics retrieved successfully",
        "data": stats
    }