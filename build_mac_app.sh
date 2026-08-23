#!/bin/bash
set -e

echo "Building MrFold Music macOS App..."

# PyInstaller command
# We use --windowed to create a .app bundle (no console window)
# We use --add-data to include all necessary data directories and files.
# For macOS/Linux, the separator in --add-data is ':'

pyinstaller --name "MrFold Music" \
    --windowed \
    --noconfirm \
    --add-data "static:static" \
    --add-data "100 pdb with chemmical shift values .csv:." \
    --add-data "6188_simulated_hsqc_backbone_example_music.csv:." \
    --add-data "TimGM6mb.sf2:." \
    desktop.py

echo "Build complete! You can find MrFold Music.app inside the 'dist' directory."
