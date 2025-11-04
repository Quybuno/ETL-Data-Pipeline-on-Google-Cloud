"""
Cloud Function Gen2 - Event-driven handler
Triggered khi có file mới trong raw bucket (GCS object finalized event)
Xử lý: đọc JSONL từ raw bucket -> transform -> ghi vào clean bucket hoặc nạp BigQuery
"""
import json
import os
import tempfile
from google.cloud import storage, bigquery

# Environment variables từ Terraform
RAW_BUCKET = os.getenv('RAW_BUCKET', '')
CLEAN_BUCKET = os.getenv('CLEAN_BUCKET', '')
DATASET_ID = os.getenv('DATASET_ID', 'hanoi_real_estate')
TABLE_ID = os.getenv('TABLE_ID', 'properties')

gcs_client = storage.Client()
bq_client = bigquery.Client()


def normalize_price(price_str: str) -> float | None:
    """Chuẩn hoá giá từ string 'X tỷ Y triệu' -> số float (tỷ VNĐ)"""
    if not price_str:
        return None
    price_str = price_str.lower().strip()
    # Remove các ký tự không phải số, tỷ, triệu
    price_str = price_str.replace(',', '').replace('.', '')
    
    ty = 0
    trieu = 0
    
    if 'tỷ' in price_str or 'ty' in price_str:
        parts = price_str.split('tỷ' if 'tỷ' in price_str else 'ty')
        if parts[0]:
            try:
                ty = float(''.join(c for c in parts[0] if c.isdigit() or c == '.'))
            except:
                pass
        if len(parts) > 1 and 'triệu' in parts[1]:
            try:
                trieu_str = parts[1].split('triệu')[0]
                trieu = float(''.join(c for c in trieu_str if c.isdigit() or c == '.')) / 1000
            except:
                pass
    elif 'triệu' in price_str:
        try:
            trieu_str = price_str.split('triệu')[0]
            trieu = float(''.join(c for c in trieu_str if c.isdigit() or c == '.')) / 1000
        except:
            pass
    
    total = ty + trieu
    return total if total > 0 else None


def normalize_area(area_str: str) -> float | None:
    """Chuẩn hoá diện tích từ string 'X m²' -> số float (m²)"""
    if not area_str:
        return None
    area_str = area_str.lower().strip()
    # Extract số trước 'm²' hoặc 'm2'
    import re
    match = re.search(r'([\d.,]+)', area_str)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except:
            pass
    return None


def transform_record(record: dict) -> dict:
    """Transform 1 record từ raw -> clean format"""
    clean = {
        'url': record.get('url'),
        'source': record.get('_source', 'mogi'),
        'run_date': record.get('_run_date'),
        'title': record.get('title'),
        'address': record.get('address'),
        'price_raw': record.get('price'),
        'price_billion_vnd': normalize_price(record.get('price', '')),
        'area_raw': record.get('Diện tích'),
        'area_m2': normalize_area(record.get('Diện tích', '')),
        'loai_hinh': record.get('loai_hinh'),
        'phap_ly': record.get('Pháp lý'),
        'phong_ngu': record.get('Phòng ngủ'),
        'phong_tam': record.get('Phòng tắm'),
        'huong_nha': record.get('Hướng nhà'),
        'mo_gioi_ten': record.get('mo_gioi_ten'),
        'mo_gioi_phone': record.get('mo_gioi_phone'),
    }
    # Loại bỏ None values
    return {k: v for k, v in clean.items() if v is not None}


def main(event, context):
    """
    Cloud Function entry point
    event: CloudEvent từ GCS object finalized
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Lấy thông tin file từ event
    bucket_name = event.get('bucket', '')
    file_name = event.get('name', '')
    
    if not bucket_name or not file_name:
        print("Missing bucket or file name in event")
        return
    
    if not file_name.endswith('.jsonl'):
        print(f"Skipping non-JSONL file: {file_name}")
        return
    
    print(f"Processing file: gs://{bucket_name}/{file_name}")
    
    # Đọc file từ GCS
    bucket = gcs_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    
    if not blob.exists():
        print(f"File not found: {file_name}")
        return
    
    # Download và parse JSONL
    records = []
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.jsonl') as tmp:
        blob.download_to_filename(tmp.name)
        
        with open(tmp.name, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    records.append(transform_record(rec))
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    continue
    
    if not records:
        print("No valid records to process")
        return
    
    print(f"Processed {len(records)} records")
    
    # Option 1: Ghi vào clean bucket
    if CLEAN_BUCKET:
        clean_prefix = file_name.replace('source=', 'clean/').replace('/part-', '/part-')
        clean_blob = gcs_client.bucket(CLEAN_BUCKET).blob(clean_prefix)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as tmp_clean:
            for rec in records:
                tmp_clean.write(json.dumps(rec, ensure_ascii=False) + '\n')
            tmp_clean.flush()
            
            clean_blob.upload_from_filename(tmp_clean.name)
            print(f"Uploaded clean data to: gs://{CLEAN_BUCKET}/{clean_prefix}")
    
    # Option 2: Load vào BigQuery
    if DATASET_ID and TABLE_ID:
        dataset_ref = bq_client.dataset(DATASET_ID)
        table_ref = dataset_ref.table(TABLE_ID)
        
        # Stream insert (hoặc dùng load job cho batch lớn)
        errors = bq_client.insert_rows_json(table_ref, records)
        if errors:
            print(f"BigQuery insert errors: {errors}")
        else:
            print(f"Inserted {len(records)} rows into {DATASET_ID}.{TABLE_ID}")
    
    print("Processing completed successfully")

