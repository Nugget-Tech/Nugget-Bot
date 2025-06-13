FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and yt-dlp in one step to reduce layers
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libopus-dev \
        mpv \
        wget \
        git \
        python-is-python3 && \
    apt-get remove -y youtube-dl && \
    wget https://github.com/yt-dlp/yt-dlp/releases/download/2025.04.30/yt-dlp_linux -O /usr/local/bin/youtube-dl && \
    chmod a+rx /usr/local/bin/youtube-dl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
