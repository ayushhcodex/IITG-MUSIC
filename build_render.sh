#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python requirements
pip install -r requirements.txt

# Create directories for local fluidsynth binaries
mkdir -p fluidsynth_unpacked

echo "Setting up local non-root apt-get cache..."
# Setup a custom writable path for apt-get
APT_DIR="/tmp/apt-local"
mkdir -p "$APT_DIR/lists/partial"
mkdir -p "$APT_DIR/cache/archives/partial"
touch "$APT_DIR/status"

APT_OPTS="-o Dir::State::lists=$APT_DIR/lists -o Dir::Cache=$APT_DIR/cache -o Dir::State::status=$APT_DIR/status"

echo "Updating package lists (non-root)..."
apt-get $APT_OPTS update || echo "apt-get update failed, trying direct downloads..."

echo "Downloading fluidsynth deb packages..."
# Attempt apt-get download first
apt-get $APT_OPTS download fluidsynth libinstpatch-1.0-2 || true
apt-get $APT_OPTS download libfluidsynth3 || apt-get $APT_OPTS download libfluidsynth2 || true

# If no deb files downloaded, fallback to direct download from Debian CDN
if [ -z "$(ls *.deb 2>/dev/null)" ]; then
  echo "No deb files downloaded via apt-get. Falling back to direct curl downloads from debian.org mirror..."
  # Download Debian 12 Bookworm pool binaries as default
  curl -L -O http://ftp.debian.org/debian/pool/main/f/fluidsynth/fluidsynth_2.3.1-2_amd64.deb || true
  curl -L -O http://ftp.debian.org/debian/pool/main/f/fluidsynth/libfluidsynth3_2.3.1-2_amd64.deb || true
  curl -L -O http://ftp.debian.org/debian/pool/main/libi/libinstpatch/libinstpatch-1.0-2_1.1.6-1_amd64.deb || true
fi

echo "Extracting deb packages..."
for deb in *.deb; do
  if [ -f "$deb" ]; then
    echo "Extracting $deb..."
    dpkg -x "$deb" fluidsynth_unpacked
    rm "$deb"
  fi
done

echo "Local fluidsynth setup complete."
