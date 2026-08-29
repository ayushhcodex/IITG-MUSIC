FROM python:3.10-slim

# Install fluidsynth and libsndfile1 (needed for scipy WAV writing)
RUN apt-get update && apt-get install -y \
    fluidsynth \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Pre-create the outputs and static dirs
RUN mkdir -p /app/outputs /app/static

# Expose port (HF Spaces uses 7860; Render provides PORT env var)
EXPOSE 7860

# Run uvicorn — Hugging Face Spaces uses port 7860; Render provides PORT
CMD uvicorn backend_app:app --host 0.0.0.0 --port ${PORT:-7860}
