FROM python:3.10-slim

# Install fluidsynth and other system dependencies
RUN apt-get update && apt-get install -y \
    fluidsynth \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Command to run the application. 
# Hugging Face Spaces requires port 7860 by default; Render provides PORT.
CMD uvicorn backend_app:app --host 0.0.0.0 --port ${PORT:-7860}
