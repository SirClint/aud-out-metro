#!/bin/bash

# Navigate to the directory where the script is located
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

# Run the metronome application
./venv/bin/python3 main.py
