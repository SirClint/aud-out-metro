#!/bin/bash
# Script to create releases for different platforms

# Ensure we're in a clean virtual environment
echo "Creating fresh virtual environment..."
python3 -m venv build_venv
source build_venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install --upgrade pip
pip install -e .
pip install pyinstaller

# Create directories
mkdir -p releases

# Build the application
echo "Building application..."
python build_app.py

# Create checksums
echo "Creating checksums..."
cd dist
sha256sum aud-out-metro* > SHA256SUMS.txt
cd ..

# Move files to releases directory
echo "Moving files to releases directory..."
mv dist/* releases/

# Clean up build artifacts
echo "Cleaning up..."
rm -rf build dist *.spec build_venv

echo "Release files have been created in the releases directory"
echo "Please test the binary before publishing!"