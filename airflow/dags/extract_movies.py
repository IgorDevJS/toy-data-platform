from __future__ import annotations

from datetime import datetime

from airflow import models
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.models.baseoperator import chain

DAG_ID = "extract_movies"

DATASETS = ["imdb_top_1000", "meta_critic", "netflix_titles"]


# As variáveis do dlt vêm do mesmo `dlt/.env.docker` do `make dlt-run`, montado no
# Airflow em /opt/airflow/env (ver docker-compose.yml). Antes era um dict fixo aqui, que
# ficou sem a NORMALIZE__PARQUET_NORMALIZER__ADD_DLT_LOAD_ID da source freshness.
ENV_DIR = "/opt/airflow/env"

with models.DAG(
    DAG_ID,
    schedule="@once",
    start_date=datetime(2025, 2, 1),
    catchup=False,
    tags=["movies", "full"],
    template_searchpath=[ENV_DIR],
) as dag:
    tasks = []
    for dataset in DATASETS:
        task = DockerOperator(
            docker_url="unix://var/run/docker.sock",
            image="my-dlt-pipeline:latest",
            command=["python", "filesystem_pipeline.py", "-t", dataset],
            network_mode="container:airflow_scheduler",
            task_id=f"ingestion-movies-{dataset}",
            auto_remove="force",
            dag=dag,
            env_file="dlt.env",
            mount_tmp_dir=False,
        )
        tasks.append(task)

chain(*tasks)
