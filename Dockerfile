FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Setup cron job for video processing
RUN apt-get update && apt-get -y install cron
RUN echo "*/15 * * * * cd /app && python scripts/process_videos.py >> /var/log/cron.log 2>&1" > /etc/cron.d/process_videos
RUN chmod 0644 /etc/cron.d/process_videos
RUN crontab /etc/cron.d/process_videos

# Create a script to start both services
RUN echo '#!/bin/bash\n\
service cron start\n\
(cd /app && uvicorn api.main:app --host 0.0.0.0 --port 8000 &)\n\
cd /app && streamlit run app.py --server.port 8501 --server.address 0.0.0.0\n'\
> /app/start.sh

RUN chmod +x /app/start.sh

# Expose ports for Streamlit and FastAPI
EXPOSE 8501 8000

# Start the application
CMD ["/app/start.sh"]