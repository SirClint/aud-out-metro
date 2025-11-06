"""
Build script for creating distributable versions of the metronome application
"""
import PyInstaller.__main__
import os
import platform

def build_app():
    # Determine current OS
    current_os = platform.system().lower()
    
    # Base PyInstaller arguments
    # Set platform-specific name and extension
    platform_config = {
        'windows': {'suffix': '-windows', 'ext': '.exe'},
        'darwin': {'suffix': '-macos', 'ext': ''},
        'linux': {'suffix': '-linux', 'ext': ''}
    }.get(current_os, {'suffix': '', 'ext': ''})
    
    args = [
        'main.py',
        '--onefile',
        '--windowed',  # Don't show console window on Windows
        f'--name=aud-out-metro{platform_config["suffix"]}{platform_config["ext"]}',
        '--add-data=metronome_config.ini:.',  # Include config file
        '--clean',  # Clean PyInstaller cache
        '--noconfirm',  # Replace existing build without asking
    ]

    # OS-specific configurations
    if current_os == 'windows':
        args.extend([
            '--icon=resources/metronome.ico',  # Add this icon file if you have one
        ])
    elif current_os == 'darwin':  # macOS
        args.extend([
            '--icon=resources/metronome.icns',  # Add this icon file if you have one
        ])

    # Run PyInstaller
    PyInstaller.__main__.run(args)

if __name__ == "__main__":
    build_app()