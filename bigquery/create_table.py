"""
Script Python để tạo BigQuery dataset và table từ schema.sql
Không cần quyền admin như bq CLI
"""
from google.cloud import bigquery
import os

# Set project và location
project_id = "etl-gp-200501"  # Match với Airflow DAG
dataset_id = "hanoi_real_estate"
location = "asia-southeast1"  # Phải match với region của các services khác

client = bigquery.Client(project=project_id)

# Tạo dataset trước nếu chưa có
print(f"Checking dataset {dataset_id} in project {project_id}...")
try:
    dataset = client.get_dataset(dataset_id)
    print(f"[OK] Dataset {dataset_id} already exists at location {dataset.location}")
except Exception as e:
    if "not found" in str(e).lower():
        print(f"Creating dataset {dataset_id} at location {location}...")
        dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
        dataset.location = location
        dataset.description = "Dataset cho dữ liệu bất động sản Hà Nội"
        dataset = client.create_dataset(dataset, exists_ok=False)
        print(f"[OK] Dataset {dataset_id} created successfully at {location}")
    else:
        raise

# Đọc SQL từ file
script_dir = os.path.dirname(os.path.abspath(__file__))
schema_file = os.path.join(script_dir, "schema.sql")

with open(schema_file, "r", encoding="utf-8") as f:
    sql = f.read()

# Đảm bảo SQL có đúng location nếu cần
# Chạy query để tạo table
print(f"\nCreating table properties in dataset {dataset_id}...")
job = client.query(sql, location=location)  # Specify location để tránh lỗi
job.result()  # Đợi job hoàn thành

print("[OK] Table created successfully!")
print(f"Dataset: {dataset_id}")
print(f"Table: properties")
print(f"Location: {location}")

