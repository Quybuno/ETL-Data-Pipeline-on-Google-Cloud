"""
Airflow DAG cho ETL pipeline
Chạy trong Cloud Composer (Apache Airflow managed service)
"""
from datetime import datetime, timedelta
import os
import time
import urllib.parse
import urllib.request
import urllib.error

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.models import Variable
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'etl-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,  # Tăng retries lên 3 lần
    'retry_delay': timedelta(minutes=2),  # Retry sau 2 phút (đủ thời gian cho cold start)
}

dag = DAG(
    'hanoi_real_estate_etl',
    default_args=default_args,
    description='ETL pipeline cho bất động sản Hà Nội',
    schedule_interval='@daily',
    start_date=datetime(2025, 10, 25),   
    catchup=True,  # Tắt catchup - chỉ chạy từ hôm nay trở đi, không chạy lại các ngày đã qua
    tags=['etl', 'real-estate', 'hanoi'],
)

def _call_cloud_run(**context):
    """Trigger Cloud Run crawler service qua HTTP với retry logic cho 503/504 và cold start handling."""
    cloud_run_url = Variable.get(
        "cloud_run_crawler_url",
        default_var=os.getenv("CLOUD_RUN_URL", "")
    )
    if not cloud_run_url:
        raise AirflowException(
            "Cloud Run URL chưa được cấu hình (Airflow Variable 'cloud_run_crawler_url' hoặc env CLOUD_RUN_URL)."
        )

    # Đảm bảo URL không có trailing slash (trừ khi là root)
    cloud_run_url = cloud_run_url.rstrip('/')
    
    dag_conf = context.get('dag_run').conf if context.get('dag_run') else {}
    raw_bucket = dag_conf.get('raw_bucket', 'hanoi-bds-raw-data-f')
    source = dag_conf.get('source', 'mogi')
    max_pages = dag_conf.get('max_pages', 40)
    run_date = dag_conf.get('run_date', context['ds'])

    params = {
        'raw_bucket': raw_bucket,
        'source': source,
        'max_pages': max_pages,
        'run_date': run_date,
    }
    url = f"{cloud_run_url}?{urllib.parse.urlencode(params)}"
    
    # Warm-up: Thử gọi health endpoint nhiều lần để đảm bảo service đã sẵn sàng
    health_url = f"{cloud_run_url}/health"
    max_warmup_attempts = 5
    warmup_delay = 10  # seconds
    
    print(f"[WARM-UP] Bắt đầu warm-up Cloud Run service tại {health_url}")
    service_ready = False
    for warmup_attempt in range(1, max_warmup_attempts + 1):
        try:
            health_request = urllib.request.Request(health_url, method='GET')
            with urllib.request.urlopen(health_request, timeout=15) as response:
                if response.status == 200:
                    print(f"[WARM-UP] Health check passed (attempt {warmup_attempt}/{max_warmup_attempts}): {health_url}")
                    service_ready = True
                    break
        except Exception as e:
            print(f"[WARM-UP] Health check failed (attempt {warmup_attempt}/{max_warmup_attempts}): {str(e)}")
            if warmup_attempt < max_warmup_attempts:
                print(f"[WARM-UP] Đợi {warmup_delay} giây cho cold start...")
                time.sleep(warmup_delay)
                warmup_delay = min(warmup_delay * 1.5, 30)  # Tăng delay nhưng tối đa 30 giây
    
    if not service_ready:
        print(f"[WARNING] Health check không thành công sau {max_warmup_attempts} attempts, nhưng vẫn tiếp tục gọi main endpoint...")
    
    # Gọi main endpoint với retry logic được cải thiện
    max_retries = 6  # Tăng từ 3 lên 6 để xử lý cold start tốt hơn
    initial_retry_delay = 30  # Tăng initial delay từ 10 lên 30 giây (cold start thường 20-60s)
    retry_delay = initial_retry_delay
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[ATTEMPT {attempt}/{max_retries}] Calling Cloud Run at {url}")
            request = urllib.request.Request(url, method='POST')
            with urllib.request.urlopen(request, timeout=900) as response:  # Timeout 15 phút
                body = response.read().decode('utf-8')
                status = response.status
                
            if status >= 400:
                error_msg = f"Cloud Run trả về lỗi {status}: {body[:500]}"
                # Retry nếu là 503 (Service Unavailable) hoặc 504 (Gateway Timeout)
                if status in [503, 504] and attempt < max_retries:
                    print(f"[ERROR] {error_msg} - Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 120)  # Exponential backoff, tối đa 120 giây
                    continue
                raise AirflowException(error_msg)
            
            print(f"[SUCCESS] Cloud Run call successful: {status}")
            return body
            
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            # Retry nếu là 503 (Service Unavailable) hoặc 504 (Gateway Timeout)
            if e.code in [503, 504] and attempt < max_retries:
                print(f"[ERROR] {error_msg} - Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 120)  # Exponential backoff, tối đa 120 giây
                continue
            raise AirflowException(f"Gọi Cloud Run thất bại sau {attempt} attempts: {error_msg}") from e
        except urllib.error.URLError as e:
            # Xử lý connection errors (có thể do cold start)
            error_msg = f"URL Error: {str(e)}"
            if attempt < max_retries:
                print(f"[ERROR] {error_msg} - Có thể service đang cold start. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 120)
                continue
            raise AirflowException(f"Gọi Cloud Run thất bại sau {attempt} attempts: {error_msg}") from e
        except Exception as exc:  # noqa: BLE001
            if attempt < max_retries:
                print(f"[ERROR] {str(exc)} - Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 120)
                continue
            raise AirflowException(f"Gọi Cloud Run thất bại sau {attempt} attempts: {exc}") from exc
    
    raise AirflowException(f"Gọi Cloud Run thất bại sau {max_retries} attempts")


def log_pipeline_start(**context):
    """Log bắt đầu pipeline"""
    print(f"Starting ETL pipeline at {datetime.now()}")
    return "Pipeline started"


def load_clean_data_to_bigquery(**context):
    """
    Load dữ liệu đã clean từ GCS lên BigQuery
    Tìm file clean data trong clean bucket và load vào BigQuery
    """
    from google.cloud import bigquery, storage
    
    dag_conf = context.get('dag_run').conf if context.get('dag_run') else {}
    clean_bucket = dag_conf.get('clean_bucket', 'hanoi-bds-clean-data-f')
    source = dag_conf.get('source', 'mogi')
    run_date = dag_conf.get('run_date', context['ds'])
    
    project_id = "etl-gp-200501"
    dataset_id = "hanoi_real_estate"
    table_id = "properties"
    staging_table_id = f"{table_id}_staging"
    location = "asia-southeast1"
    
    # Tìm file clean data trong GCS
    gcs_client = storage.Client(project=project_id)
    bucket = gcs_client.bucket(clean_bucket)
    
    # Pattern: clean/dt=YYYY-MM-DD/part-*.jsonl hoặc clean/source=mogi/dt=YYYY-MM-DD/part-*.jsonl
    # Thử nhiều pattern để tìm file
    prefix_patterns = [
        f"clean/dt={run_date}/",
        f"clean/source={source}/dt={run_date}/",
        f"clean/",  # Tìm tất cả trong clean/
        "",  # Tìm tất cả trong bucket
    ]
    
    print(f"[INFO] Tim file clean data trong bucket: {clean_bucket}")
    print(f"[INFO] Run date: {run_date}")
    print(f"[INFO] Source: {source}")
    
    blobs = []
    for prefix in prefix_patterns:
        print(f"   [INFO] Dang tim voi pattern: '{prefix}'")
        try:
            found = list(bucket.list_blobs(prefix=prefix))
            # Lọc chỉ lấy file .jsonl và LOẠI BỎ file test
            jsonl_files = [b for b in found if b.name.endswith('.jsonl') and 'test' not in b.name.lower()]
            if jsonl_files:
                # Ưu tiên file part-*.jsonl (file thật từ crawler)
                part_files = [b for b in jsonl_files if 'part-' in b.name]
                if part_files:
                    blobs = part_files
                elif run_date in prefix:
                    # Nếu có run_date trong pattern, lấy tất cả file không phải test
                    blobs = jsonl_files
                else:
                    # Tìm file có run_date trong path
                    dated_files = [b for b in jsonl_files if run_date in b.name]
                    if dated_files:
                        blobs = dated_files
                    elif not blobs:  # Chỉ dùng nếu chưa tìm thấy gì
                        blobs = jsonl_files[:5]  # Lấy tối đa 5 file đầu tiên
                
                if blobs:
                    print(f"   [OK] Tim thay {len(blobs)} file(s) voi pattern '{prefix}'")
                    break
        except Exception as e:
            print(f"   [WARNING] Loi khi tim voi pattern '{prefix}': {e}")
            continue
    
    if not blobs:
        print(f"[ERROR] Khong tim thay file clean data trong gs://{clean_bucket}/")
        print(f"   Da thu cac pattern: {prefix_patterns}")
        print("   Co the Cloud Function chua xu ly xong hoac file o path khac")
        print("   => Kiem tra Cloud Function logs hoac clean bucket truc tiep")
        print("   => Kiem tra xem task 'wait_for_clean_file' co chay thanh cong khong")
        return "No clean data found"
    
    print(f"[OK] Tim thay {len(blobs)} file(s) clean data")
    
    # Schema
    schema = [
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
    
    bq_client = bigquery.Client(project=project_id)
    
    # Đảm bảo tables tồn tại
    target_table_ref = f"{project_id}.{dataset_id}.{table_id}"
    staging_table_ref = f"{project_id}.{dataset_id}.{staging_table_id}"
    
    try:
        bq_client.get_table(target_table_ref)
    except Exception:
        print(f"[INFO] Tao table {target_table_ref}")
        table = bigquery.Table(target_table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(field='ngay_dang')
        bq_client.create_table(table)
    
    try:
        bq_client.get_table(staging_table_ref)
    except Exception:
        print(f"[INFO] Tao staging table {staging_table_ref}")
        table = bigquery.Table(staging_table_ref, schema=schema)
        bq_client.create_table(table)
    
    # Load từng file vào staging table
    total_records = 0
    for blob in blobs:
        if not blob.name.endswith('.jsonl'):
            continue
        
        gcs_uri = f"gs://{clean_bucket}/{blob.name}"
        print(f"[INFO] Loading {gcs_uri} vao staging table...")
        
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            ignore_unknown_values=True,
        )
        
        load_job = bq_client.load_table_from_uri(
            gcs_uri,
            staging_table_ref,
            job_config=job_config,
            location=location
        )
        load_job.result()
        
        staging_table = bq_client.get_table(staging_table_ref)
        total_records = staging_table.num_rows
        print(f"[OK] Da load {gcs_uri} ({staging_table.num_rows} total rows trong staging)")
    
    if total_records == 0:
        print("[WARNING] Khong co records nao duoc load")
        return "No records loaded"
    
    # MERGE từ staging vào target table
    print(f"[INFO] MERGE {total_records} records vao table chinh...")
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
            INSERT (ma_bds, dien_tich_su_dung_m2, gia_ty, title, phap_ly, ngay_dang, 
                    phuong_xa, quan_huyen, thanh_pho, nha_tam, phong_ngu, 
                    dien_tich_dat_m2, chieu_dai_m, chieu_rong_m, loai_hinh)
            VALUES (source.ma_bds, source.dien_tich_su_dung_m2, source.gia_ty, 
                    source.title, source.phap_ly, source.ngay_dang, 
                    source.phuong_xa, source.quan_huyen, source.thanh_pho, 
                    source.nha_tam, source.phong_ngu, source.dien_tich_dat_m2, 
                    source.chieu_dai_m, source.chieu_rong_m, source.loai_hinh)
    """
    
    merge_job = bq_client.query(merge_query, location=location)
    merge_job.result()
    
    # Xóa staging table
    truncate_query = f"TRUNCATE TABLE `{staging_table_ref}`"
    truncate_job = bq_client.query(truncate_query, location=location)
    truncate_job.result()
    
    # Lấy số rows cuối cùng
    final_table = bq_client.get_table(target_table_ref)
    print(f"[OK] Hoan thanh! Tong so rows trong {target_table_ref}: {final_table.num_rows}")
    
    return f"Loaded {total_records} records, total: {final_table.num_rows}"


# Task 1: Trigger Cloud Run crawler
trigger_crawler = PythonOperator(
    task_id='trigger_crawler',
    python_callable=_call_cloud_run,
    dag=dag,
)

# Task 2: Đợi file xuất hiện trong raw bucket (optional sensor - soft fail nếu không tìm thấy)
wait_for_raw_file = GCSObjectExistenceSensor(
    task_id='wait_for_raw_file',
    bucket='hanoi-bds-raw-data-f',  # Cloud Storage bucket name
    object='source=mogi/dt={{ ds }}/part-00001.jsonl',  # ds là execution_date
    timeout=7200,  # Đợi tối đa 2 giờ (tăng từ 1 giờ)
    poke_interval=120,  # Kiểm tra mỗi 2 phút (giảm số lần check)
    soft_fail=True,  # Không fail DAG nếu sensor timeout, chỉ skip task này
    dag=dag,
)

# Task 2.5: Đợi file clean data xuất hiện (file thật, không phải test)
# Cloud Function cần thời gian để xử lý raw data và ghi vào clean bucket
# Ưu tiên đợi file part-*.jsonl (file thật từ crawler)
wait_for_clean_file = GCSObjectExistenceSensor(
    task_id='wait_for_clean_file',
    bucket='hanoi-bds-clean-data-f',
    object='clean/dt={{ ds }}/part-00001.jsonl',  # Pattern: clean/dt=YYYY-MM-DD/part-00001.jsonl (file thật)
    timeout=3600,  # Đợi tối đa 1 giờ
    poke_interval=30,  # Kiểm tra mỗi 30 giây (Cloud Function thường xử lý trong vài phút)
    soft_fail=True,  # Soft fail để task load_to_bigquery có thể tự tìm file
    dag=dag,
)

# Task 3: Load clean data lên BigQuery
load_to_bigquery = PythonOperator(
    task_id='load_to_bigquery',
    python_callable=load_clean_data_to_bigquery,
    dag=dag,
    trigger_rule='none_failed',  # Chạy ngay cả khi sensor bị skip
)

# Task 4: Log completion
log_completion = PythonOperator(
    task_id='log_completion',
    python_callable=lambda: print(f"ETL pipeline completed at {datetime.now()}"),
    dag=dag,
    trigger_rule='none_failed',  # Chạy ngay cả khi sensor bị skip (không fail DAG)
)

# Dependencies
# Flow: trigger_crawler -> wait_for_raw_file -> wait_for_clean_file -> load_to_bigquery -> log_completion
# wait_for_clean_file phải chạy SAU wait_for_raw_file để đảm bảo Cloud Function đã được trigger
trigger_crawler >> wait_for_raw_file >> wait_for_clean_file >> load_to_bigquery >> log_completion

