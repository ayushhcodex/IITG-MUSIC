FROM python:3.10-slim

# Install system dependencies (fluidsynth, libsndfile1 for scipy WAV writing, curl)
RUN apt-get update && apt-get install -y \
    fluidsynth \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (UID 1000 required by Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Copy requirements and install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=user . .

# Ensure runtime directories exist with full user permissions
RUN mkdir -p outputs pdb_cache static

# Expose default port (Hugging Face Spaces uses 7860; Render passes PORT env var)
EXPOSE 7860

# Shell-wrapped launch respecting $PORT if provided (Render) or defaulting to 7860 (Hugging Face)
CMD ["sh", "-c", "uvicorn backend_app:app --host 0.0.0.0 --port ${PORT:-7860}"]
