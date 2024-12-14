#!/usr/bin/env python3
import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path

def build_extension():
    """Build the extension and return the path to the built binary"""
    subprocess.check_call([sys.executable, 'setup.py', 'build_ext', '--inplace'])
    
    # Find the built extension
    ext_suffix = '.so'  # Linux/Mac
    if platform.system() == 'Windows':
        ext_suffix = '.pyd'
    
    # Look for the built extension
    for file in Path('.').rglob(f'hicstraw*{ext_suffix}'):
        return file
    
    raise FileNotFoundError("Built extension not found")

def get_target_filename():
    """Generate the target filename based on current platform"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    if system == 'windows':
        ext = '.pyd'
    else:
        ext = '.so'
    
    return f"hicstraw.{system}.{machine}.cp{python_version}-{python_version}{ext}"

def main():
    # Create prebuilt directory if it doesn't exist
    prebuilt_dir = Path('prebuilt')
    prebuilt_dir.mkdir(exist_ok=True)
    
    try:
        # Build the extension
        print(f"Building extension for {platform.system()} {platform.machine()} Python {sys.version}")
        built_ext = build_extension()
        
        # Generate target filename
        target_name = get_target_filename()
        target_path = prebuilt_dir / target_name
        
        # Copy the built extension to prebuilt directory
        shutil.copy2(built_ext, target_path)
        print(f"Successfully created pre-built binary: {target_path}")
        
    except Exception as e:
        print(f"Error building extension: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
