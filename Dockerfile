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

# Pre-create the outputs and static dirs with correct permissions
# HF Docker Spaces run as a non-root user (uid 1000), /app is writable
RUN mkdir -p /app/outputs /app/static

# HF Docker Spaces expose port 7860
EXPOSE 7860

# Run uvicorn directly — serves backend_app (FastAPI + static HTML frontend)
CMD ["uvicorn", "backend_app:app", "--host", "0.0.0.0", "--port", "7860"]
