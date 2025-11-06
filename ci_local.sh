#!/usr/bin/env bash
# ci_local.sh — reproduce CI steps locally inside a Python 3.12 Docker container
# Usage: ./ci_local.sh            # runs tests
#        ./ci_local.sh build      # runs tests then builds PyInstaller binary
# This avoids pushing to GitHub and reproduces the CI environment.

set -euo pipefail

MODE=${1:-test}
PWD_HOST=$(pwd)
IMAGE=python:3.12-slim

# Files/dirs that will be created inside container:
# - venv/ (inside container only)
# - dist/ (PyInstaller output) will be written to host
# - wheelhouse/ (optional) will be written to host

echo "Running CI locally in Docker (image: $IMAGE) — mode=$MODE"

docker run --rm -it \
  -v "$PWD_HOST":/src \
  -w /src \
  $IMAGE \
  bash -lc "\
    set -euo pipefail && \
    apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config libsndfile1 ffmpeg libasound2-dev portaudio19-dev libportaudio2 && \
    python -m pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt || (echo 'pip install failed; try pip wheel to inspect build errors' && exit 2) && \
    echo 'Running unit tests...' && python -m unittest discover -v && \
    if [ '$MODE' = 'build' ]; then \
      pip install pyinstaller && python build_app.py && echo 'Build complete — see dist/'; \
    fi"

echo "Done. If you ran build, check ./dist for binaries."