FROM n8nio/n8n:latest
USER root
RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir pillow numpy opencv-python-headless sentence-transformers requests
USER node