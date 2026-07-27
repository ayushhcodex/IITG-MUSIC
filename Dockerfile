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
# Render provides the PORT environment variable.
CMD uvicorn backend_app:app --host 0.0.0.0 --port ${PORT:-8000}
