#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python requirements
pip install -r requirements.txt

# Create directories for local fluidsynth binaries
mkdir -p fluidsynth_unpacked

echo "Downloading fluidsynth deb packages..."
# Download fluidsynth and its direct unique libraries
apt-get download fluidsynth || true
apt-get download libfluidsynth3 || apt-get download libfluidsynth2 || true
apt-get download libinstpatch-1.0-2 || true

echo "Extracting deb packages..."
for deb in *.deb; do
  if [ -f "$deb" ]; then
    echo "Extracting $deb..."
    dpkg -x "$deb" fluidsynth_unpacked
    rm "$deb"
  fi
done

echo "Local fluidsynth setup complete."
