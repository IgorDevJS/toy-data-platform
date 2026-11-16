"""Pipeline diário do catálogo: CSV → raw (dlt) → trusted → refined (dbt).

    ingest-imdb_top_1000 ─┐
    ingest-meta_critic ───┼─► dbt-source-freshness ─► dbt-build
    ingest-netflix_titles ┘

- As três ingestões são independentes e rodam em paralelo.
- `dbt source freshness` confere, pelo `_dlt_load_id` de cada linha, que a carga do
  dia chegou na raw antes de transformar (erro com mais de 7 dias, ver o `schema.yml`).
- `dbt build` roda seeds, models, o snapshot `titles_snapshot` (logo depois do
  `fct_titles`) e os testes, na ordem do grafo do dbt. Um teste que falha para o build
  e pula o que depende do model com problema.

Cada tarefa é um container na rede `platform-net`, como no Makefile: a imagem
`my-dlt-pipeline` (`make dlt-build`) e a `movies_transform` (`make build`), que leva o
projeto dbt dentro. As variáveis vêm dos mesmos arquivos do Makefile
(`dlt/.env.docker` e `dbt/.env`), montados no Airflow em /opt/airflow/env.

Idempotente: o dlt faz `replace`, os models do dbt são recriados (ou `merge`, no
incremental) e o snapshot só abre versão nova se a nota ou os votos mudarem. Rodar duas
vezes no mesmo dia deixa as mesmas contagens.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import models
from airflow.providers.docker.operators.docker import DockerOperator

DAG_ID = "movies_daily"

DATASETS = ["imdb_top_1000", "meta_critic", "netflix_titles"]

# Onde o compose monta os .env (ver `x-airflow-common` no docker-compose.yml). O
# `env_file` do DockerOperator é um template: o nome é procurado nesta pasta.
ENV_DIR = "/opt/airflow/env"

DOCKER_DEFAULTS = dict(
    docker_url="unix://var/run/docker.sock",
    network_mode="platform-net",
    # O Airflow roda em container: a pasta temporária dele não existe no host, então
    # não dá para montá-la no container da tarefa.
    mount_tmp_dir=False,
    auto_remove="force",
)

default_args = {
    "owner": "data-platform",
    # Falha passageira (Trino reiniciando, MinIO lento) não deve derrubar o dia.
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}

with models.DAG(
    DAG_ID,
    description="Ingestão dos 3 CSVs em paralelo, frescor da raw e dbt build",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    # Uma DAG diária que nasce pausada não roda sozinha; esta já entra ligada.
    is_paused_upon_creation=False,
    default_args=default_args,
    template_searchpath=[ENV_DIR],
    tags=["movies", "daily", "dlt", "dbt"],
) as dag:
    ingestions = [
        DockerOperator(
            task_id=f"ingest-{dataset}",
            image="my-dlt-pipeline:latest",
            command=["python", "filesystem_pipeline.py", "-t", dataset],
            env_file="dlt.env",
            **DOCKER_DEFAULTS,
        )
        for dataset in DATASETS
    ]

    freshness = DockerOperator(
        task_id="dbt-source-freshness",
        image="movies_transform:latest",
        command=["dbt", "source", "freshness"],
        env_file="dbt.env",
        **DOCKER_DEFAULTS,
    )

    build = DockerOperator(
        task_id="dbt-build",
        image="movies_transform:latest",
        command=["dbt", "build"],
        env_file="dbt.env",
        **DOCKER_DEFAULTS,
    )

    ingestions >> freshness >> build
