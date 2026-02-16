#!/bin/bash
# Setup script for YouTube Title Extractor
# Run this once to install everything you need.

set -e

echo "============================================"
echo " YouTube Title Extractor - Setup"
echo "============================================"
echo ""

# Check for Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "ERROR: Python is not installed."
    echo ""
    echo "Install Python from: https://www.python.org/downloads/"
    echo "After installing, run this script again."
    exit 1
fi

echo "Found Python: $($PYTHON --version)"
echo ""

# Install dependencies
echo "Installing dependencies..."
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install -r requirements.txt
echo ""

# Verify yt-dlp
if command -v yt-dlp &> /dev/null; then
    echo "yt-dlp version: $(yt-dlp --version)"
else
    echo "WARNING: yt-dlp command not found in PATH."
    echo "Try: $PYTHON -m pip install yt-dlp"
fi

echo ""
echo "============================================"
echo " Setup complete!"
echo "============================================"
echo ""
echo "Quick start:"
echo ""
echo "  # Get title from a video URL:"
echo "  $PYTHON youtube_title_extractor.py --url \"https://www.youtube.com/watch?v=VIDEO_ID\""
echo ""
echo "  # Get titles from a search results page:"
echo "  $PYTHON youtube_title_extractor.py --search-url \"https://www.youtube.com/results?search_query=python+tutorial\""
echo ""
echo "  # Search by keyword:"
echo "  $PYTHON youtube_title_extractor.py --keyword \"python tutorial\""
echo ""
echo "  # See all options:"
echo "  $PYTHON youtube_title_extractor.py --help"
echo ""
