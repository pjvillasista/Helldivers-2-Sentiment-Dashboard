from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def run_extraction():
    exec(open("/mnt/c/Users/PJ/hd2_sentiment_analysis/dags/extraction.py").read())

def run_topical_modeling():
    exec(open("/mnt/c/Users/PJ/hd2_sentiment_analysis/dags/topical_modeling.py").read())

# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'process_data',
    default_args=default_args,
    description='A DAG to run data extraction and modeling scripts',
    schedule_interval=timedelta(days=1),
    catchup=False,
)

# Define the tasks
t1 = PythonOperator(
    task_id='run_extraction',
    python_callable=run_extraction,
    dag=dag,
)

t2 = PythonOperator(
    task_id='run_topical_modeling',
    python_callable=run_topical_modeling,
    dag=dag,
)

t1 >> t2  # Set task dependency; t2 will run after t1 completes
