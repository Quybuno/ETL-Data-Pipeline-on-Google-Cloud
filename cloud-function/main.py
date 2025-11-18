"""
Cloud Function Gen2 - Event-driven handler
Triggered khi có file mới trong raw bucket (GCS object finalized event)
Xử lý: đọc JSONL từ raw bucket -> transform -> ghi vào clean bucket hoặc nạp BigQuery
"""
import json
import os
import re
import tempfile
from datetime import datetime
from typing import Optional, Tuple

import functions_framework
from google.cloud import bigquery, storage
from google.cloud.exceptions import NotFound

# Environment variables từ Cloud Function configuration
RAW_BUCKET = os.getenv('RAW_BUCKET', '')
CLEAN_BUCKET = os.getenv('CLEAN_BUCKET', '')
DATASET_ID = os.getenv('DATASET_ID', 'hanoi_real_estate')
TABLE_ID = os.getenv('TABLE_ID', 'properties')
STAGING_TABLE_ID = os.getenv('STAGING_TABLE_ID', f"{TABLE_ID}_staging")
BIGQUERY_LOCATION = os.getenv('BIGQUERY_LOCATION', 'asia-southeast1')

PRICE_TY_RE = re.compile(r'([\d.,]+)\s*(?:tỷ|ty|tỉ)', re.IGNORECASE)
PRICE_TRIEU_RE = re.compile(r'([\d.,]+)\s*(?:triệu|trieu)', re.IGNORECASE)
AREA_RE = re.compile(r'([\d.,]+)')
LISTING_ID_RE = re.compile(r'(\d{5,})')

gcs_client = storage.Client()
bq_client = bigquery.Client()

CLEAN_SCHEMA = [
    bigquery.SchemaField('ma_bds', 'STRING'),
    bigquery.SchemaField('dien_tich_su_dung_m2', 'FLOAT'),
    bigquery.SchemaField('gia_ty', 'FLOAT'),
    bigquery.SchemaField('title', 'STRING'),
    bigquery.SchemaField('phap_ly', 'STRING'),
    bigquery.SchemaField('ngay_dang', 'DATE'),
    bigquery.SchemaField('phuong_xa', 'STRING'),
    bigquery.SchemaField('quan_huyen', 'STRING'),
    bigquery.SchemaField('thanh_pho', 'STRING'),
    bigquery.SchemaField('nha_tam', 'INT64'),
    bigquery.SchemaField('phong_ngu', 'INT64'),
    bigquery.SchemaField('dien_tich_dat_m2', 'FLOAT'),
    bigquery.SchemaField('chieu_dai_m', 'FLOAT'),
    bigquery.SchemaField('chieu_rong_m', 'FLOAT'),
    bigquery.SchemaField('loai_hinh', 'STRING'),
]

RENAME_MAP = {
    'Diện tích sử dụng': 'dien_tich_su_dung_m2',
    'Diện tích sử dụng (m²)': 'dien_tich_su_dung_m2',
    'Diện tích đất': 'dien_tich_dat',
    'Diện tích đất (m²)': 'dien_tich_dat',
    'Mã BĐS': 'ma_bds',
    'price': 'gia_ty',
    'Pháp lý': 'phap_ly',
    'Ngày đăng': 'ngay_dang',
    'Nhà tắm': 'nha_tam',
    'Phòng ngủ': 'phong_ngu',
    'address': 'dia_chi',
}

AREA_BINS = [
    (0, 50, '<50m²'),
    (50, 80, '50-80m²'),
    (80, 120, '80-120m²'),
    (120, 200, '120-200m²'),
    (200, float('inf'), '>200m²'),
]

DATE_KEYS = ['Ngày đăng', 'Ngày cập nhật', 'Ngày đăng tin']
AREA_KEYS = ['Diện tích', 'Diện tích sử dụng', 'Diện tích sử dụng (m²)', 'Diện tích sử dụng m2']
LAND_AREA_KEYS = ['Diện tích đất', 'Diện tích đất (m²)', 'Diện tích đất m2']
LENGTH_KEYS = ['Chiều dài', 'Chiều dài (m)', 'Chiều dài m']
WIDTH_KEYS = ['Chiều rộng', 'Chiều rộng (m)', 'Chiều rộng m']
BATH_KEYS = ['Phòng tắm', 'Số phòng tắm']
BED_KEYS = ['Phòng ngủ', 'Số phòng ngủ']


def _to_float(raw: str | None) -> Optional[float]:
    if not raw:
        return None
    raw = str(raw).strip()
    if not raw:
        return None

    normalized = raw
    if ',' in raw and '.' in raw:
        normalized = raw.replace('.', '').replace(',', '.')
    elif ',' in raw:
        normalized = raw.replace(',', '.')
    else:
        normalized = raw.replace(',', '')

    try:
        return float(normalized)
    except (ValueError, TypeError):
        return None


def _to_int(raw: str | int | None) -> Optional[int]:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    raw = str(raw).strip()
    if not raw:
        return None

    # Remove decimal part if present
    if '.' in raw:
        raw = raw.split('.')[0]
    
    normalized = raw.replace(',', '').replace('.', '')

    try:
        return int(normalized)
    except (ValueError, TypeError):
        return None


def _first_numeric(record: dict, keys) -> Optional[float]:
    for key in keys:
        value = record.get(key)
        if not value:
            continue
        match = AREA_RE.search(str(value))
        candidate = match.group(1) if match else str(value)
        number = _to_float(candidate)
        if number is not None:
            return number
    return None


def _first_int(record: dict, keys) -> Optional[int]:
    number = _first_numeric(record, keys)
    if number is None:
        return None
    try:
        return int(number)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value  # giữ nguyên nếu không parse được


def _split_address(address: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not address:
        return None, None, None
    parts = [p.strip() for p in address.split(',') if p.strip()]
    if not parts:
        return None, None, None
    city = parts[-1] if parts else None
    district = parts[-2] if len(parts) >= 2 else None
    ward = parts[0] if parts else None
    return ward, district, city


def _extract_listing_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    match = LISTING_ID_RE.search(url)
    return match.group(1) if match else None


def normalize_price(price_str: str | None) -> Optional[float]:
    """Chuẩn hoá giá từ string 'X tỷ Y triệu' -> số float (tỷ VNĐ)."""
    if not price_str:
        return None

    price = price_str.lower()
    if any(keyword in price for keyword in ['thoả thuận', 'thỏa thuận', 'liên hệ', 'call']):
        return None

    ty_val = None
    trieu_val = None

    ty_match = PRICE_TY_RE.search(price)
    if ty_match:
        ty_val = _to_float(ty_match.group(1))

    trieu_match = PRICE_TRIEU_RE.search(price)
    if trieu_match:
        trieu_val = _to_float(trieu_match.group(1))

    total = 0.0
    if ty_val:
        total += ty_val
    if trieu_val:
        total += trieu_val / 1000.0

    return total if total > 0 else None


def normalize_area(area_str: str | None) -> Optional[float]:
    """Chuẩn hoá diện tích từ string 'X m²' -> số float (m²)."""
    if not area_str:
        return None

    match = AREA_RE.search(area_str.lower())
    if not match:
        return None

    value = _to_float(match.group(1))
    return value


def _clean_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _apply_aliases(record: dict) -> dict:
    """Ánh xạ các tên cột raw sang schema clean."""
    normalized = dict(record)
    for source, target in RENAME_MAP.items():
        source_value = record.get(source)
        if source_value in (None, '', 'nan'):
            continue
        if target not in normalized or normalized.get(target) in (None, '', 'nan'):
            normalized[target] = source_value
    return normalized


def _extract_area_details(text: str | None) -> dict:
    """Tách diện tích đất và kích thước (nếu có) từ chuỗi."""
    if not text or not isinstance(text, str):
        return {'dien_tich': None, 'chieu_dai': None, 'chieu_rong': None}

    text = text.strip()
    area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m2', text, re.IGNORECASE)
    area_val = float(area_match.group(1).replace(',', '.')) if area_match else None

    size_match = re.search(r'\(([^)]+)\)', text)
    length = width = None
    if size_match:
        numbers = re.findall(r'(\d+(?:[.,]\d+)?)', size_match.group(1))
        if len(numbers) >= 2:
            floats = [float(num.replace(',', '.')) for num in numbers]
            length = max(floats)
            width = min(floats)

    return {'dien_tich': area_val, 'chieu_dai': length, 'chieu_rong': width}


def _clean_surface_value(value) -> Optional[float]:
    if value in (None, '', 'nan'):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r'(\d+(?:[.,]\d+)?)', str(value))
    if not match:
        return None
    return float(match.group(1).replace(',', '.'))


def _clean_room_value(value) -> Optional[float]:
    if value in (None, '', 'nan'):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if text in {'nhà tắm', 'phòng ngủ', 'phong ngu', 'nha tam'}:
        return None
    try:
        return float(text.replace(',', '.'))
    except ValueError:
        return None


def _area_bin_label(area: Optional[float]) -> Optional[str]:
    if area is None:
        return None
    for lower, upper, label in AREA_BINS:
        if lower <= area < upper:
            return label
    return None


def _parse_vietnam_address(address: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not address:
        return None, None, None
    address = str(address)
    street_part = address.split(',')[0].strip()

    ward_match = re.search(r'Phường\s+([^,]+)', address, re.IGNORECASE)
    ward = ward_match.group(1).strip() if ward_match else None

    district_match = re.search(r'(Quận|Huyện)\s+([^,]+)', address, re.IGNORECASE)
    district = district_match.group(2).strip() if district_match else None

    city_match = re.search(r'(Thành phố|TP\.?|Tỉnh)\s+([^,]+)', address, re.IGNORECASE)
    city = city_match.group(2).strip() if city_match else "Hà Nội"

    ward_full = f"{street_part} - Phường {ward}" if ward else street_part or None

    return ward_full, district, city


def _normalize_record(record: dict) -> dict:
    """Chuẩn hoá 1 record raw theo logic trong notebook Transform."""
    normalized = _apply_aliases(record)

    ward, district, city = _parse_vietnam_address(normalized.get('dia_chi') or normalized.get('address'))
    if not ward and not district and not city:
        ward, district, city = _split_address(normalized.get('address'))

    area_details = _extract_area_details(normalized.get('dien_tich_dat') or normalized.get('dien_tich'))

    living_area = normalized.get('dien_tich_su_dung_m2') or _first_numeric(normalized, AREA_KEYS)
    living_area = _clean_surface_value(living_area)

    land_area = normalized.get('dien_tich_dat_m2') or area_details.get('dien_tich') or _first_numeric(normalized, LAND_AREA_KEYS)
    land_area = _clean_surface_value(land_area)

    if living_area is None and land_area is not None:
        living_area = land_area

    length_m = _clean_surface_value(normalized.get('chieu_dai_m') or area_details.get('chieu_dai') or _first_numeric(normalized, LENGTH_KEYS))
    width_m = _clean_surface_value(normalized.get('chieu_rong_m') or area_details.get('chieu_rong') or _first_numeric(normalized, WIDTH_KEYS))

    baths = _clean_room_value(normalized.get('nha_tam') or _first_numeric(normalized, BATH_KEYS))
    beds = _clean_room_value(normalized.get('phong_ngu') or _first_numeric(normalized, BED_KEYS))

    posting_date = None
    for key in DATE_KEYS:
        if normalized.get(key):
            posting_date = _parse_date(normalized.get(key))
            break
    if not posting_date and normalized.get('ngay_dang'):
        posting_date = _parse_date(normalized.get('ngay_dang'))

    price_value = normalized.get('gia_ty') or normalized.get('gia(ty)') or normalized.get('price')
    if isinstance(price_value, str):
        price_clean = normalize_price(price_value)
    else:
        price_clean = _to_float(price_value)

    loai_hinh = normalized.get('loai_hinh')
    if not loai_hinh:
        title = (normalized.get('title') or '').lower()
        if re.search(r'\b(đất|dat|đất thổ cư|lô đất|đất nền)\b', title):
            loai_hinh = 'dat'
        elif re.search(r'\b(nhà|nha|nhà riêng|nhà mặt|nhà tầng|nhà nghỉ|nhà đơn)\b', title):
            loai_hinh = 'nha'
        elif re.search(r'\b(chung cư|chung cu|căn hộ|can ho)\b', title):
            loai_hinh = 'chung_cu'
        else:
            loai_hinh = 'mat_bang'

    return {
        'ma_bds': _clean_string(normalized.get('ma_bds') or _extract_listing_id(normalized.get('url'))),
        'dien_tich_su_dung_m2': living_area,
        'gia_ty': price_clean,
        'title': normalized.get('title'),
        'phap_ly': _clean_string(normalized.get('phap_ly')),
        'ngay_dang': posting_date or normalized.get('_run_date'),
        'phuong_xa': _clean_string(ward or normalized.get('phuong_xa')),
        'quan_huyen': _clean_string(district or normalized.get('quan_huyen')),
        'thanh_pho': _clean_string(city or normalized.get('thanh_pho')),
        'nha_tam': baths,
        'phong_ngu': beds,
        'dien_tich_dat_m2': land_area,
        'chieu_dai_m': length_m,
        'chieu_rong_m': width_m,
        'loai_hinh': loai_hinh,
    }


def _assign_price_bins(records: list[dict], n_bins: int = 10) -> None:
    prices = [rec['gia_ty'] for rec in records if rec.get('gia_ty') is not None]
    if not prices:
        for rec in records:
            rec['_gia_bin'] = None
        return

    min_price = min(prices)
    max_price = max(prices)
    if min_price == max_price:
        for rec in records:
            rec['_gia_bin'] = 0 if rec.get('gia_ty') is not None else None
        return

    bin_size = (max_price - min_price) / n_bins if n_bins > 0 else (max_price - min_price)
    if bin_size <= 0:
        bin_size = max_price - min_price or 1

    for rec in records:
        price = rec.get('gia_ty')
        if price is None:
            rec['_gia_bin'] = None
            continue
        bin_index = int((price - min_price) / bin_size)
        if bin_index >= n_bins:
            bin_index = n_bins - 1
        if bin_index < 0:
            bin_index = 0
        rec['_gia_bin'] = bin_index


def _similarity_key(rec: dict) -> str:
    district = (rec.get('quan_huyen') or 'unknown').strip().lower()
    loai = (rec.get('loai_hinh') or 'unknown').strip().lower()
    gia_bin = rec.get('_gia_bin')
    bin_val = str(gia_bin) if gia_bin is not None else 'unknown'
    return f"{district}|{loai}|{bin_val}"


def _fill_area_by_similarity(records: list[dict]) -> None:
    group_stats: dict[str, dict[str, float]] = {}
    for rec in records:
        area = rec.get('dien_tich_su_dung_m2')
        if area is None:
            continue
        key = _similarity_key(rec)
        stats = group_stats.setdefault(key, {'sum': 0.0, 'count': 0})
        stats['sum'] += area
        stats['count'] += 1

    for rec in records:
        if rec.get('dien_tich_su_dung_m2') is not None:
            continue
        key = _similarity_key(rec)
        stats = group_stats.get(key)
        if stats and stats['count'] > 0:
            rec['dien_tich_su_dung_m2'] = stats['sum'] / stats['count']


def _fill_rooms_by_area_bins(records: list[dict]) -> None:
    bin_stats: dict[str, dict[str, dict[str, float]]] = {}
    for rec in records:
        area = rec.get('dien_tich_su_dung_m2')
        if area is None:
            continue
        bin_label = _area_bin_label(area)
        if not bin_label:
            continue
        stats = bin_stats.setdefault(bin_label, {'nha_tam': {'sum': 0.0, 'count': 0}, 'phong_ngu': {'sum': 0.0, 'count': 0}})
        if rec.get('nha_tam') is not None:
            stats['nha_tam']['sum'] += rec['nha_tam']
            stats['nha_tam']['count'] += 1
        if rec.get('phong_ngu') is not None:
            stats['phong_ngu']['sum'] += rec['phong_ngu']
            stats['phong_ngu']['count'] += 1

    for rec in records:
        area = rec.get('dien_tich_su_dung_m2')
        bin_label = _area_bin_label(area)
        if bin_label:
            stats = bin_stats.get(bin_label)
            if stats:
                if rec.get('nha_tam') is None and stats['nha_tam']['count'] > 0:
                    rec['nha_tam'] = stats['nha_tam']['sum'] / stats['nha_tam']['count']
                if rec.get('phong_ngu') is None and stats['phong_ngu']['count'] > 0:
                    rec['phong_ngu'] = stats['phong_ngu']['sum'] / stats['phong_ngu']['count']


def _finalize_room_values(records: list[dict]) -> None:
    for field in ['nha_tam', 'phong_ngu']:
        values = [rec[field] for rec in records if rec.get(field) is not None]
        mean_value = sum(values) / len(values) if values else None
        for rec in records:
            if rec.get(field) is None and mean_value is not None:
                rec[field] = mean_value
            if rec.get(field) is not None:
                rec[field] = int(round(rec[field]))


def transform_records(raw_records: list[dict]) -> list[dict]:
    """Transform cả file raw -> list record clean theo logic notebook."""
    normalized_records = []
    for record in raw_records:
        clean = _normalize_record(record)
        if clean.get('ma_bds'):
            normalized_records.append(clean)

    if not normalized_records:
        return []

    _assign_price_bins(normalized_records)
    _fill_area_by_similarity(normalized_records)
    _fill_rooms_by_area_bins(normalized_records)
    _finalize_room_values(normalized_records)

    for rec in normalized_records:
        rec.pop('_gia_bin', None)

    return normalized_records


def _ensure_table(table_id: str, schema: list[bigquery.SchemaField]) -> None:
    table_ref = f"{bq_client.project}.{DATASET_ID}.{table_id}"
    try:
        bq_client.get_table(table_ref)
    except NotFound:
        table = bigquery.Table(table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(field='ngay_dang')
        bq_client.create_table(table)
        print(f"Created table {table_ref}")


@functions_framework.cloud_event
def main(cloud_event):
    """
    Cloud Function entry point
    cloud_event: CloudEvent từ GCS object finalized
    """
    data = cloud_event.data or {}
    print(f"Received event: {json.dumps(data)}")
    
    # Lấy thông tin file từ event
    bucket_name = data.get('bucket', '')
    file_name = data.get('name', '')
    
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
    raw_records = []
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.jsonl') as tmp:
        blob.download_to_filename(tmp.name)
        
        with open(tmp.name, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    raw_records.append(rec)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    continue
    
    if not raw_records:
        print("No valid records to process")
        return

    records = transform_records(raw_records)
    if not records:
        print("No records after transform")
        return

    # Deduplicate by ma_bds (bỏ bất động sản không có mã)
    deduped_records = []
    seen_ids = set()
    for rec in records:
        listing_id = rec.get('ma_bds')
        if not listing_id:
            continue
        if listing_id in seen_ids:
            continue
        seen_ids.add(listing_id)
        deduped_records.append(rec)

    if not deduped_records:
        print("No unique records to process")
        return

    print(f"Processed {len(deduped_records)} records (after dedupe)")
    records = deduped_records

    # Option 1: Ghi vào clean bucket
    if CLEAN_BUCKET:
        # Convert: source=mogi/dt=2025-11-14/file.jsonl -> clean/dt=2025-11-14/file.jsonl
        # Hoặc: source=mogi/dt=2025-11-14/part-00001.jsonl -> clean/dt=2025-11-14/part-00001.jsonl
        if file_name.startswith('source='):
            # Remove 'source=mogi/' prefix and replace with 'clean/'
            parts = file_name.split('/', 2)  # ['source=mogi', 'dt=2025-11-14', 'file.jsonl']
            if len(parts) >= 2:
                clean_prefix = f"clean/{parts[1]}"  # clean/dt=2025-11-14
                if len(parts) > 2:
                    clean_prefix += f"/{parts[2]}"  # clean/dt=2025-11-14/file.jsonl
            else:
                clean_prefix = file_name.replace('source=', 'clean/')
        else:
            clean_prefix = file_name.replace('source=', 'clean/').replace('/part-', '/part-')
        clean_blob = gcs_client.bucket(CLEAN_BUCKET).blob(clean_prefix)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as tmp_clean:
            for rec in records:
                tmp_clean.write(json.dumps(rec, ensure_ascii=False) + '\n')
            tmp_clean.flush()

            clean_blob.upload_from_filename(tmp_clean.name)
            print(f"Uploaded clean data to: gs://{CLEAN_BUCKET}/{clean_prefix}")

    # Option 2: Load vào BigQuery với staging + MERGE
    if DATASET_ID and TABLE_ID:
        _ensure_table(TABLE_ID, CLEAN_SCHEMA)
        _ensure_table(STAGING_TABLE_ID, CLEAN_SCHEMA)

        staging_table_ref = f"{bq_client.project}.{DATASET_ID}.{STAGING_TABLE_ID}"
        job_config = bigquery.LoadJobConfig(schema=CLEAN_SCHEMA, write_disposition=bigquery.WriteDisposition.WRITE_APPEND)
        load_job = bq_client.load_table_from_json(records, staging_table_ref, job_config=job_config, location=BIGQUERY_LOCATION)
        load_job.result()
        print(f"Loaded {len(records)} rows into staging table {staging_table_ref}")

        target_table_ref = f"{bq_client.project}.{DATASET_ID}.{TABLE_ID}"
        merge_query = f"""
            MERGE `{target_table_ref}` AS target
            USING `{staging_table_ref}` AS source
            ON target.ma_bds = source.ma_bds
            WHEN MATCHED THEN UPDATE SET
                target.dien_tich_su_dung_m2 = source.dien_tich_su_dung_m2,
                target.gia_ty = source.gia_ty,
                target.title = source.title,
                target.phap_ly = source.phap_ly,
                target.ngay_dang = source.ngay_dang,
                target.phuong_xa = source.phuong_xa,
                target.quan_huyen = source.quan_huyen,
                target.thanh_pho = source.thanh_pho,
                target.nha_tam = source.nha_tam,
                target.phong_ngu = source.phong_ngu,
                target.dien_tich_dat_m2 = source.dien_tich_dat_m2,
                target.chieu_dai_m = source.chieu_dai_m,
                target.chieu_rong_m = source.chieu_rong_m,
                target.loai_hinh = source.loai_hinh
            WHEN NOT MATCHED THEN
                INSERT (ma_bds, dien_tich_su_dung_m2, gia_ty, title, phap_ly, ngay_dang, phuong_xa, quan_huyen, thanh_pho, nha_tam, phong_ngu, dien_tich_dat_m2, chieu_dai_m, chieu_rong_m, loai_hinh)
                VALUES (source.ma_bds, source.dien_tich_su_dung_m2, source.gia_ty, source.title, source.phap_ly, source.ngay_dang, source.phuong_xa, source.quan_huyen, source.thanh_pho, source.nha_tam, source.phong_ngu, source.dien_tich_dat_m2, source.chieu_dai_m, source.chieu_rong_m, source.loai_hinh)
        """
        merge_job = bq_client.query(merge_query, location=BIGQUERY_LOCATION)
        merge_job.result()
        print(f"Merged staging table into {target_table_ref}")

        truncate_job = bq_client.query(f"TRUNCATE TABLE `{staging_table_ref}`", location=BIGQUERY_LOCATION)
        truncate_job.result()
        print(f"Truncated staging table {staging_table_ref}")

    print("Processing completed successfully")

