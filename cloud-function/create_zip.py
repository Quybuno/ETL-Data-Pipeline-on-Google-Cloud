"""
Script đơn giản để tạo file zip từ Cloud Function source code
"""
import os
import zipfile

# Configuration
ZIP_NAME = "cf-src.zip"

# Get current directory
script_dir = os.path.dirname(os.path.abspath(__file__))
zip_path = os.path.join(script_dir, "..", ZIP_NAME)

# Tạo zip file từ source code
print(f"Creating zip file from source code...")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add Python files
    for file in ['main.py', 'requirements.txt']:
        file_path = os.path.join(script_dir, file)
        if os.path.exists(file_path):
            zipf.write(file_path, os.path.basename(file_path))
            print(f"  Added {file}")
        else:
            print(f"  Warning: {file} not found")

print(f"\nZip file created: {zip_path}")
print(f"File size: {os.path.getsize(zip_path) / 1024:.2f} KB")

