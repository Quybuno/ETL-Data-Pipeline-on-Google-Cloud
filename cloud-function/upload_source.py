"""
Script Python để upload Cloud Function source code lên GCS
Không cần quyền admin như gsutil CLI
"""
import os
import zipfile
from google.cloud import storage

# Configuration
PROJECT_ID = "etl-gcp-200501"
REGION = "asia-southeast1"
BUCKET_NAME = "etl-gcp-200501-cf-src"
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

print(f"✅ Zip file created: {zip_path}")

# Upload lên GCS
print(f"\nUploading to gs://{BUCKET_NAME}/{ZIP_NAME}...")
client = storage.Client(project=PROJECT_ID)

# Tạo bucket nếu chưa có
try:
    bucket = client.get_bucket(BUCKET_NAME)
    print(f"✅ Bucket {BUCKET_NAME} already exists")
except Exception:
    print(f"Creating bucket {BUCKET_NAME}...")
    bucket = client.create_bucket(BUCKET_NAME, location=REGION)
    print(f"✅ Bucket {BUCKET_NAME} created at location {REGION}")

# Upload zip file
blob = bucket.blob(ZIP_NAME)
blob.upload_from_filename(zip_path)
print(f"✅ Uploaded {ZIP_NAME} to gs://{BUCKET_NAME}/{ZIP_NAME}")

print("\n✅ Done! Source code uploaded successfully.")
print(f"   Update terraform.tfvars with:")
print(f"   cf_source_bucket = \"{BUCKET_NAME}\"")
print(f"   cf_source_object = \"{ZIP_NAME}\"")

