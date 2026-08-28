# Use a lightweight, official Python image
FROM python:3.11-slim

# Set System environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Install system dependencies needed by yt-dlp (like ffmpeg if needed later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    gnupg \
    && curl -fsSL https://nodesource.com | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Establish the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY cookies.txt .
COPY . .

# Expose the designated port
EXPOSE 8000

# Run FastAPI using uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
