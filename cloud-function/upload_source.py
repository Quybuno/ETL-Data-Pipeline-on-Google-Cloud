"""
Script Python để upload Cloud Function source code lên GCS
Không cần quyền admin như gsutil CLI
"""
import os
import zipfile
from google.cloud import storage

# Configuration
PROJECT_ID = "etl-gp-200501"
REGION = "asia-southeast1"
BUCKET_NAME = "etl-gp-200501-cf-src"
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

print(f"Zip file created: {zip_path}")

# Upload lên GCS
print(f"\nUploading to gs://{BUCKET_NAME}/{ZIP_NAME}...")
client = storage.Client(project=PROJECT_ID)

# Tạo bucket nếu chưa có
try:
    bucket = client.get_bucket(BUCKET_NAME)
    print(f"Bucket {BUCKET_NAME} already exists")
except Exception:
    print(f"Creating bucket {BUCKET_NAME}...")
    bucket = client.create_bucket(BUCKET_NAME, location=REGION)
    print(f"Bucket {BUCKET_NAME} created at location {REGION}")

# Upload zip file
try:
    blob = bucket.blob(ZIP_NAME)
    blob.upload_from_filename(zip_path)
    print(f"Uploaded {ZIP_NAME} to gs://{BUCKET_NAME}/{ZIP_NAME}")
    
    print("\nDone! Source code uploaded successfully.")
    print(f"   Source code location: gs://{BUCKET_NAME}/{ZIP_NAME}")
    print(f"   Use this path when creating Cloud Function in GCP Console")
except Exception as e:
    error_msg = str(e)
    if "403" in error_msg or "Forbidden" in error_msg:
        if "billing account" in error_msg.lower() or "accountDisabled" in error_msg:
            print("\n" + "="*70)
            print("ERROR: Billing Account Issue")
            print("="*70)
            print(f"\nThe GCP project '{PROJECT_ID}' has a billing account issue.")
            print("\nTo fix this:")
            print("1. Go to: https://console.cloud.google.com/billing")
            print(f"2. Check if project '{PROJECT_ID}' has a billing account linked")
            print("3. If not, link a billing account to the project")
            print("4. If billing is disabled, enable it")
            print("\nAlternatively, check your project settings:")
            print(f"   https://console.cloud.google.com/cloud-resource-manager?project={PROJECT_ID}")
            print("\nError details:")
            print(f"   {error_msg}")
            print("="*70)
        else:
            print(f"\nERROR: Permission denied (403 Forbidden)")
            print(f"Check that your account has 'Storage Admin' or 'Storage Object Admin' role")
            print(f"on project '{PROJECT_ID}' and bucket '{BUCKET_NAME}'")
            print(f"\nError: {error_msg}")
    else:
        print(f"\nERROR: Failed to upload file")
        print(f"Error: {error_msg}")
    exit(1)

