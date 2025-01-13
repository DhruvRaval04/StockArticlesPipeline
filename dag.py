from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator 
from airflow.utils.dates import days_ago
from datetime import datetime 
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from Extract_script import run_stock_etl

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2020, 11, 8),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1)
}

dag = DAG(
    'stock_data_dag',
    default_args=default_args,
    description = 'etl code for stock news',
    schedule_interval='@once',  # Run only once
    catchup=False,  # Prevent backfilling
    is_paused_upon_creation=True  # Start in paused state

)

run_etl = PythonOperator(
    task_id = 'complete_stockdata_extraction_etl',
    python_callable = run_stock_etl,
    dag =dag
)


s3_prefix = 's3://stock-datanews-etl-bucket'

is_file_in_s3_available = S3KeySensor(
    task_id='tsk_is_file_in_s3_available',
    bucket_key=s3_prefix,
    bucket_name=s3_bucket,
    aws_conn_id='aws_s3_conn',
    wildcard_match=False,  # Set this to True if you want to use wildcards in the prefix
    timeout=60,  # Optional: Timeout for the sensor (in seconds)
    poke_interval=3,  # Optional: Time interval between S3 checks (in seconds)
    )

run_etl

