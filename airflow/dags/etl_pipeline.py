"""
Airflow DAG cho ETL pipeline
Chạy trong Cloud Composer (Apache Airflow managed service)
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.google.cloud.operators.cloud_run import CloudRunExecuteJobOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'etl-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'hanoi_real_estate_etl',
    default_args=default_args,
    description='ETL pipeline cho bất động sản Hà Nội',
    schedule_interval='0 2 * * *',  # Chạy hàng ngày lúc 2h sáng
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['etl', 'real-estate', 'hanoi'],
)


def log_pipeline_start(**context):
    """Log bắt đầu pipeline"""
    print(f"Starting ETL pipeline at {datetime.now()}")
    return "Pipeline started"


# Task 1: Trigger Cloud Run crawler
trigger_crawler = CloudRunExecuteJobOperator(
    task_id='trigger_crawler',
    job_name='crawler-service',  # Tên Cloud Run service từ Terraform
    region='asia-southeast1',
    project_id='etl-gcp-200501',
    dag=dag,
)

# Task 2: Đợi file xuất hiện trong raw bucket (optional sensor)
wait_for_raw_file = GCSObjectExistenceSensor(
    task_id='wait_for_raw_file',
    bucket='hanoi-bds-raw-data',  # Từ Terraform output
    object='source=mogi/dt={{ ds }}/part-00001.jsonl',  # ds là execution_date
    timeout=3600,  # Đợi tối đa 1 giờ
    poke_interval=60,  # Kiểm tra mỗi phút
    dag=dag,
)

# Task 3: Log completion
log_completion = PythonOperator(
    task_id='log_completion',
    python_callable=lambda: print(f"ETL pipeline completed at {datetime.now()}"),
    dag=dag,
)

# Dependencies
trigger_crawler >> wait_for_raw_file >> log_completion

