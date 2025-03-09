from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.endpoints import router

# Create FastAPI app
app = FastAPI(
    title="YouTube Clickbait Data API",
    description="API for accessing YouTube clickbait data",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)

@app.get("/")
async def root():
    return {
        "message": "YouTube Clickbait Data API",
        "endpoints": [
            "/api/auth",
            "/api/export-data",
            "/api/stats"
        ],
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)