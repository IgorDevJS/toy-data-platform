FROM python:3.11.11-slim
RUN pip install dbt-core==1.12.6 dbt-trino==1.10.6

# O projeto vai dentro da imagem para a DAG `movies_daily` do Airflow: o DockerOperator
# fala com o Docker do host pelo socket, e um bind mount precisaria do caminho do host.
# A imagem fica imutável (roda o que foi construído, não a working copy); depois de mudar
# o dbt, `make build`. Os alvos do Makefile montam o projeto por cima deste COPY, então o
# fluxo de desenvolvimento continua lendo os arquivos do host.
WORKDIR /usr/app/movies_transform
COPY movies_transform/ .
