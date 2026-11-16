"""Liga o Superset à camada semântica (Cube) e cria os dashboards.

O Superset é a segunda superfície de consumo da camada semântica: ele fala com
o Cube pela SQL API (protocolo Postgres), então enxerga cada view do Cube
(`titles_overview`, `catalog_overview`) como uma tabela e as medidas/dimensões
governadas como colunas. Nenhum SQL ad-hoc é escrito em gráfico nenhum — as
definições vivem no Cube (cube/model).

Tudo o que aparece no Superset (dataset, métrica, gráfico, dashboard) nasce
aqui, e não pela interface: o que se cria clicando fica só no banco de metadados
e some quando o volume é recriado.

Este script usa a REST API pública do Superset (a mesma que o `curl` do aluno
usa) em vez das models internas do Flask, que mudam a cada versão. É
idempotente: rodar de novo só atualiza o que já existe.

Roda dentro do container do Superset (ver o serviço `superset-bootstrap` no
docker-compose.yml).
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from urllib.parse import quote_plus

import requests

SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://superset:8088")
SUPERSET_ADMIN_USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
SUPERSET_ADMIN_PASSWORD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "secret")

# A credencial da SQL API do Cube é a mesma que o Cube lê (cube/.env), para não
# existirem duas verdades sobre a mesma senha.
CUBE_SQL_USER = os.environ["CUBEJS_SQL_USER"]
CUBE_SQL_PASSWORD = os.environ["CUBEJS_SQL_PASSWORD"]
CUBE_SQL_PORT = os.environ["CUBEJS_PG_SQL_PORT"]

DATABASE_NAME = "Cube — camada semântica"
DATASET_SCHEMA = "public"


@dataclass(frozen=True)
class DatasetSpec:
    """Uma view do Cube vista como tabela, com as métricas que o Superset oferece."""

    table: str
    metrics: list[dict]


# Medidas do Cube vistas pelo Superset. A forma canônica na SQL API é envolver a
# medida com `MEASURE(...)`: funciona com medida de qualquer tipo e deixa o Cube
# escolher a agregação. (As alternativas `AVG(...)`/`COUNT(DISTINCT ...)` também
# existem, mas precisam casar com o tipo da medida — ver
# docs.cube.dev/reference/core-data-apis/sql-api/query-format.)
TITLES_OVERVIEW = DatasetSpec(
    table="titles_overview",
    metrics=[
        {
            "metric_name": "count_titles",
            "verbose_name": "Títulos",
            "expression": "MEASURE(count_titles)",
            "metric_type": "count_distinct",
            "description": "Quantidade de títulos distintos.",
        },
        {
            "metric_name": "avg_rating",
            "verbose_name": "Nota média",
            "expression": "MEASURE(avg_rating)",
            "metric_type": "avg",
            "description": "Nota média da crítica.",
        },
        {
            "metric_name": "total_votes",
            "verbose_name": "Total de votos",
            "expression": "MEASURE(total_votes)",
            "metric_type": "sum",
            "description": "Soma dos votos recebidos.",
        },
    ],
)

# Duas populações, dois nomes (Aula 4: "8807 × 1813, dê nome à métrica"): o
# catálogo inteiro e só os títulos com nota da crítica. O `verbose_name` é o que
# aparece no gráfico, então ele também precisa dizer qual é a população.
CATALOG_OVERVIEW = DatasetSpec(
    table="catalog_overview",
    metrics=[
        {
            "metric_name": "count_catalog_titles",
            "verbose_name": "Títulos do catálogo",
            "expression": "MEASURE(count_catalog_titles)",
            "metric_type": "count_distinct",
            "description": "Títulos do catálogo inteiro da Netflix (8802).",
        },
        {
            "metric_name": "count_titles",
            "verbose_name": "Títulos com nota da crítica",
            "expression": "MEASURE(count_titles)",
            "metric_type": "count_distinct",
            "description": "Só os títulos com nota da crítica (1813): a amostra da nota.",
        },
        {
            "metric_name": "avg_rating",
            "verbose_name": "Nota média da crítica",
            "expression": "MEASURE(avg_rating)",
            "metric_type": "avg",
            "description": "Nota média da crítica, só dos títulos que a têm.",
        },
        {
            "metric_name": "total_votes",
            "verbose_name": "Total de votos",
            "expression": "MEASURE(total_votes)",
            "metric_type": "sum",
            "description": "Soma dos votos recebidos (títulos com nota da crítica).",
        },
    ],
)

DATASETS = [TITLES_OVERVIEW, CATALOG_OVERVIEW]


def cube_sqlalchemy_uri() -> str:
    user = quote_plus(CUBE_SQL_USER)
    password = quote_plus(CUBE_SQL_PASSWORD)
    return f"postgresql+psycopg2://{user}:{password}@cube:{CUBE_SQL_PORT}/cube"


@dataclass(frozen=True)
class ChartSpec:
    name: str
    description: str
    viz_type: str
    dataset: DatasetSpec
    form_data: dict


@dataclass(frozen=True)
class MarkdownSpec:
    """Bloco de texto do dashboard (componente MARKDOWN do `position_json`)."""

    key: str
    text: str


@dataclass(frozen=True)
class DashboardSpec:
    title: str
    # Uma linha de largura cheia por item, na ordem.
    rows: list[ChartSpec | MarkdownSpec]


CHART_COUNTRY_RATING = ChartSpec(
    name="Nota média por país",
    description="Top 10 países por nota média (medida avg_rating do Cube).",
    viz_type="echarts_timeseries_bar",
    dataset=TITLES_OVERVIEW,
    form_data={
        "viz_type": "echarts_timeseries_bar",
        "x_axis": "country",
        "metrics": ["avg_rating"],
        "groupby": [],
        "adhoc_filters": [],
        "row_limit": 10,
        "order_desc": True,
        "timeseries_limit_metric": "avg_rating",
        "y_axis_format": ".2f",
        # barras ordenadas pela própria medida, da maior para a menor
        "x_axis_sort": "avg_rating",
        "x_axis_sort_asc": False,
        "x_axis_label": "País",
        "y_axis_label": "Nota média",
        "show_legend": False,
        "rich_tooltip": True,
    },
)

CHART_TYPE_TABLE = ChartSpec(
    name="Medidas por tipo de título",
    description="Medidas governadas (títulos, nota média, votos) por tipo.",
    viz_type="table",
    dataset=TITLES_OVERVIEW,
    form_data={
        "viz_type": "table",
        "query_mode": "aggregate",
        "groupby": ["title_type"],
        "metrics": ["count_titles", "avg_rating", "total_votes"],
        "adhoc_filters": [],
        "row_limit": 100,
        "order_desc": True,
        "timeseries_limit_metric": "count_titles",
    },
)

# --- Crescimento do catálogo por gênero -------------------------------------
# A pergunta do trabalho: quais gêneros mais cresceram no catálogo a partir de
# 2015, e a nota da crítica acompanhou? Os gráficos olham o mesmo recorte:
# entrada no catálogo de 2015 em diante e os 10 gêneros com mais títulos nesse
# período.

FIRST_YEAR = 2015

# Os 10 gêneros com mais títulos do catálogo de 2015 em diante, nesta ordem (a
# tabela "Tamanho do catálogo e amostra com nota" calcula o mesmo top 10 e serve
# de conferência). A lista é fixa, e não o `series_limit` do Superset, porque o
# gráfico de nota precisaria escolher as séries por uma medida que ele não
# mostra (`count_catalog_titles`). Com o SQL que o Superset gera para isso, a
# SQL API do Cube ou recusa o `ORDER BY` por medida fora do SELECT, ou ignora em
# silêncio a subconsulta do top 10 e devolve todos os gêneros (ver o README,
# "Por que o Superset vê um banco").
# A fonte é um CSV estático; se ela mudar, a tabela mostra a lista nova.
TOP_GENRES = [
    "International Movies",
    "Dramas",
    "Comedies",
    "International TV Shows",
    "Documentaries",
    "Action & Adventure",
    "Independent Movies",
    "TV Dramas",
    "Children & Family Movies",
    "Romantic Movies",
]

# Filtros simples do Superset viram WHERE sobre as dimensões; quem resolve o
# join com a ponte e a deduplicação continua sendo o Cube.
SINCE_FIRST_YEAR = {
    "expressionType": "SIMPLE",
    "subject": "year_added",
    "operator": ">=",
    "comparator": FIRST_YEAR,
    "clause": "WHERE",
}
IN_TOP_GENRES = {
    "expressionType": "SIMPLE",
    "subject": "genre",
    "operator": "IN",
    "comparator": TOP_GENRES,
    "clause": "WHERE",
}


def growth_line_form_data(
    metric: str, y_label: str, y_format: str, y_bounds: list | None = None
) -> dict:
    """Linhas por gênero ao longo do ano de entrada. O eixo X é uma dimensão
    numérica (`year_added`), e não temporal: o Superset a trata como categoria."""
    return {
        "viz_type": "echarts_timeseries_line",
        "x_axis": "year_added",
        "xAxisForceCategorical": True,
        "x_axis_sort_asc": True,
        "metrics": [metric],
        "groupby": ["genre"],
        "adhoc_filters": [SINCE_FIRST_YEAR, IN_TOP_GENRES],
        "row_limit": 1000,
        "x_axis_title": "Ano de entrada no catálogo",
        "x_axis_title_margin": 30,
        "y_axis_title": y_label,
        "y_axis_title_margin": 40,
        "y_axis_format": y_format,
        "markerEnabled": True,
        "show_legend": True,
        "legendOrientation": "right",
        "rich_tooltip": True,
        "tooltipSortByMetric": True,
        # Sem limites, o eixo Y começa no zero. Para a nota (0 a 10, quase tudo
        # entre 5 e 8) isso achata as diferenças entre os gêneros.
        "truncateYAxis": y_bounds is not None,
        "y_axis_bounds": y_bounds or [None, None],
    }


CHART_GROWTH_BY_GENRE = ChartSpec(
    name="Títulos adicionados por ano e gênero",
    description=(
        "Títulos do catálogo (count_catalog_titles) por ano de entrada, nos 10 "
        "gêneros com mais títulos a partir de 2015. 2021 vai só até setembro."
    ),
    viz_type="echarts_timeseries_line",
    dataset=CATALOG_OVERVIEW,
    form_data=growth_line_form_data(
        "count_catalog_titles", "Títulos adicionados", ",d"
    ),
)

CHART_RATING_BY_GENRE = ChartSpec(
    name="Nota média da crítica por gênero e ano de entrada",
    description=(
        "Nota média da crítica (avg_rating) dos títulos que entraram em cada ano, "
        "nos mesmos 10 gêneros. Só os títulos com nota entram na média."
    ),
    viz_type="echarts_timeseries_line",
    dataset=CATALOG_OVERVIEW,
    form_data=growth_line_form_data(
        "avg_rating", "Nota média da crítica", ".2f", y_bounds=[5, 8]
    ),
)

CHART_GENRE_SAMPLE = ChartSpec(
    name="Tamanho do catálogo e amostra com nota, por gênero",
    description=(
        "Por gênero, a partir de 2015: títulos do catálogo, quantos têm nota da "
        "crítica (a amostra da média) e a nota média."
    ),
    viz_type="table",
    dataset=CATALOG_OVERVIEW,
    form_data={
        "viz_type": "table",
        "query_mode": "aggregate",
        "groupby": ["genre"],
        "metrics": ["count_catalog_titles", "count_titles", "avg_rating"],
        "adhoc_filters": [SINCE_FIRST_YEAR],
        "row_limit": len(TOP_GENRES),
        "order_desc": True,
        "timeseries_limit_metric": "count_catalog_titles",
        "column_config": {
            "count_catalog_titles": {"d3NumberFormat": ",d"},
            "count_titles": {"d3NumberFormat": ",d"},
            "avg_rating": {"d3NumberFormat": ".2f"},
        },
        "show_cell_bars": True,
    },
)

NOTE_POPULATIONS = MarkdownSpec(
    key="populacoes",
    text=(
        "**Duas populações.** *Títulos do catálogo* conta o catálogo inteiro da "
        "Netflix (8802 títulos). A *nota média da crítica* só existe para os 1813 "
        "títulos com nota no Metacritic, então cada ponto do gráfico de nota se "
        "apoia em menos títulos do que o de contagem (ver a tabela). "
        "Recorte: entrada no catálogo a partir de 2015; 2021 vai só até setembro."
    ),
)

DASHBOARDS = [
    DashboardSpec(
        title="Camada semântica — títulos",
        rows=[CHART_COUNTRY_RATING, CHART_TYPE_TABLE],
    ),
    DashboardSpec(
        title="Crescimento do catálogo por gênero",
        rows=[
            NOTE_POPULATIONS,
            CHART_GROWTH_BY_GENRE,
            CHART_RATING_BY_GENRE,
            CHART_GENRE_SAMPLE,
        ],
    ),
]


class SupersetApi:
    """Cliente mínimo da REST API do Superset (login, CSRF e CRUD)."""

    def __init__(self, base_url: str, user: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.user = user
        self.password = password
        self.access_token = ""
        self.csrf_token = ""

    def wait_until_ready(self, timeout: int = 300) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if self.session.get(f"{self.base_url}/health", timeout=5).ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(3)
        raise SystemExit(f"Superset não respondeu em {self.base_url} a tempo")

    def login(self) -> None:
        response = self.session.post(
            f"{self.base_url}/api/v1/security/login",
            json={
                "username": self.user,
                "password": self.password,
                "provider": "db",
                "refresh": True,
            },
        )
        response.raise_for_status()
        self.access_token = response.json()["access_token"]
        csrf = self.session.get(
            f"{self.base_url}/api/v1/security/csrf_token/", headers=self.headers()
        )
        csrf.raise_for_status()
        self.csrf_token = csrf.json()["result"]

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    def write_headers(self) -> dict:
        return {
            **self.headers(),
            "X-CSRFToken": self.csrf_token,
            "Referer": self.base_url,
        }

    def list(self, resource: str) -> list[dict]:
        response = self.session.get(
            f"{self.base_url}/api/v1/{resource}/",
            params={"q": "(page_size:200)"},
            headers=self.headers(),
        )
        response.raise_for_status()
        return response.json().get("result", [])

    def get(self, resource: str, pk: int) -> dict:
        response = self.session.get(
            f"{self.base_url}/api/v1/{resource}/{pk}", headers=self.headers()
        )
        response.raise_for_status()
        return response.json()["result"]

    def create(self, resource: str, payload: dict) -> int:
        response = self.session.post(
            f"{self.base_url}/api/v1/{resource}/",
            json=payload,
            headers=self.write_headers(),
        )
        if not response.ok:
            raise SystemExit(f"Falha ao criar {resource}: {response.text}")
        return response.json()["id"]

    def update(self, resource: str, pk: int, payload: dict) -> None:
        response = self.session.put(
            f"{self.base_url}/api/v1/{resource}/{pk}",
            json=payload,
            headers=self.write_headers(),
        )
        if not response.ok:
            raise SystemExit(f"Falha ao atualizar {resource}/{pk}: {response.text}")

    def delete(self, resource: str) -> None:
        response = self.session.delete(
            f"{self.base_url}/api/v1/{resource}", headers=self.write_headers()
        )
        if not response.ok:
            raise SystemExit(f"Falha ao remover {resource}: {response.text}")

    def refresh_dataset(self, pk: int) -> None:
        """Relê as colunas da tabela na origem (o "Sync columns" da interface)."""
        response = self.session.put(
            f"{self.base_url}/api/v1/dataset/{pk}/refresh",
            headers=self.write_headers(),
        )
        if not response.ok:
            raise SystemExit(f"Falha ao sincronizar dataset/{pk}: {response.text}")


def ensure_database(api: SupersetApi) -> int:
    uri = cube_sqlalchemy_uri()
    for database in api.list("database"):
        if database["database_name"] == DATABASE_NAME:
            print(f"database: usando a existente ({uri})")
            return database["id"]
    database_id = api.create(
        "database",
        {
            "database_name": DATABASE_NAME,
            "sqlalchemy_uri": uri,
            "expose_in_sqllab": True,
            "allow_file_upload": False,
        },
    )
    print(f"database: criada id={database_id} ({uri})")
    return database_id


def ensure_dataset(api: SupersetApi, database_id: int, spec: DatasetSpec) -> int:
    for dataset in api.list("dataset"):
        if (
            dataset["table_name"] == spec.table
            and dataset["database"]["id"] == database_id
        ):
            dataset_id = dataset["id"]
            print(f"dataset {spec.table}: usando o existente id={dataset_id}")
            break
    else:
        dataset_id = api.create(
            "dataset",
            {
                "database": database_id,
                "schema": DATASET_SCHEMA,
                "table_name": spec.table,
            },
        )
        print(f"dataset {spec.table}: criado id={dataset_id}")
    # As colunas vêm do Cube: sincronizar a cada execução faz uma dimensão nova
    # do modelo (ex.: `year_added`) aparecer no Superset sem clicar em nada.
    api.refresh_dataset(dataset_id)
    trim_internal_columns(api, dataset_id, spec.table)
    metrics = with_existing_metric_ids(api, dataset_id, spec.metrics)
    api.update("dataset", dataset_id, {"metrics": metrics})
    return dataset_id


def with_existing_metric_ids(
    api: SupersetApi, dataset_id: int, wanted: list[dict]
) -> list[dict]:
    """A API recusa criar uma métrica com nome já usado; mandar o `id` faz o
    PUT atualizar a métrica em vez de tentar criá-la de novo."""
    existing = {
        metric["metric_name"]: metric["id"]
        for metric in api.get("dataset", dataset_id)["metrics"]
    }
    return [
        {**metric, "id": existing[metric["metric_name"]]}
        if metric["metric_name"] in existing
        else metric
        for metric in wanted
    ]


def trim_internal_columns(api: SupersetApi, dataset_id: int, table: str) -> None:
    """Remove as colunas internas que o Cube anexa a toda tabela da SQL API
    (`__user`, `__cubeJoinField`): não são dimensões governadas."""
    dataset = api.get("dataset", dataset_id)
    for column in dataset["columns"]:
        if column["column_name"].startswith("__"):
            api.delete(f"dataset/{dataset_id}/column/{column['id']}")
            print(f"dataset {table}: coluna interna removida ({column['column_name']})")


def chart_payload(spec: ChartSpec, dataset_id: int, dashboard_id: int) -> dict:
    return {
        "slice_name": spec.name,
        "description": spec.description,
        "viz_type": spec.viz_type,
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps({**spec.form_data, "datasource": f"{dataset_id}__table"}),
        # É este campo que popula o vínculo dashboard↔gráfico (`dashboard_slices`).
        "dashboards": [dashboard_id],
    }


def ensure_chart(
    api: SupersetApi, spec: ChartSpec, dataset_id: int, dashboard_id: int
) -> int:
    payload = chart_payload(spec, dataset_id, dashboard_id)
    for chart in api.list("chart"):
        if chart["slice_name"] == spec.name:
            api.update("chart", chart["id"], payload)
            print(f"chart: atualizado id={chart['id']} ({spec.name})")
            return chart["id"]
    chart_id = api.create("chart", payload)
    print(f"chart: criado id={chart_id} ({spec.name})")
    return chart_id


def dashboard_position(title: str, rows: list[tuple[str, dict]]) -> str:
    """Layout do dashboard no formato do `position_json` do Superset.

    `rows` traz, na ordem, o id de cada componente e o seu dicionário (gráfico ou
    markdown). Cada um ocupa uma linha de largura cheia."""
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": title}},
        "GRID_ID": {
            "id": "GRID_ID",
            "type": "GRID",
            "children": [f"ROW-{component_id}" for component_id, _ in rows],
            "parents": ["ROOT_ID"],
        },
    }
    for component_id, component in rows:
        row_id = f"ROW-{component_id}"
        position[row_id] = {
            "id": row_id,
            "type": "ROW",
            "children": [component_id],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        position[component_id] = {
            "id": component_id,
            "children": [],
            "parents": ["ROOT_ID", "GRID_ID", row_id],
            **component,
        }
    return json.dumps(position)


def chart_component(chart_id: int) -> tuple[str, dict]:
    return (
        f"CHART-{chart_id}",
        {"type": "CHART", "meta": {"chartId": chart_id, "height": 50, "width": 12}},
    )


def markdown_component(spec: MarkdownSpec) -> tuple[str, dict]:
    return (
        f"MARKDOWN-{spec.key}",
        {"type": "MARKDOWN", "meta": {"code": spec.text, "height": 12, "width": 12}},
    )


def ensure_dashboard(api: SupersetApi, title: str) -> int:
    for dashboard in api.list("dashboard"):
        if dashboard["dashboard_title"] == title:
            print(f"dashboard: usando o existente id={dashboard['id']} ({title})")
            return dashboard["id"]
    dashboard_id = api.create("dashboard", {"dashboard_title": title, "published": True})
    print(f"dashboard: criado id={dashboard_id} ({title})")
    return dashboard_id


def publish_dashboard(
    api: SupersetApi, spec: DashboardSpec, dataset_ids: dict[str, int]
) -> int:
    """Cria (ou atualiza) os gráficos do dashboard e grava o layout. Sem
    `json_metadata` no payload: mandar metadata dispara o `set_dash_metadata`,
    que reescreve chaves de estilo sobre as quais não temos opinião."""
    dashboard_id = ensure_dashboard(api, spec.title)
    components = []
    for item in spec.rows:
        if isinstance(item, MarkdownSpec):
            components.append(markdown_component(item))
        else:
            dataset_id = dataset_ids[item.dataset.table]
            chart_id = ensure_chart(api, item, dataset_id, dashboard_id)
            components.append(chart_component(chart_id))
    api.update(
        "dashboard",
        dashboard_id,
        {"position_json": dashboard_position(spec.title, components)},
    )
    print(f"dashboard: layout atualizado id={dashboard_id} ({spec.title})")
    return dashboard_id


def main() -> None:
    api = SupersetApi(SUPERSET_URL, SUPERSET_ADMIN_USER, SUPERSET_ADMIN_PASSWORD)
    api.wait_until_ready()
    api.login()
    database_id = ensure_database(api)
    dataset_ids = {
        spec.table: ensure_dataset(api, database_id, spec) for spec in DATASETS
    }
    for spec in DASHBOARDS:
        dashboard_id = publish_dashboard(api, spec, dataset_ids)
        print(f"pronto: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
    print(f"(login: {SUPERSET_ADMIN_USER})")


if __name__ == "__main__":
    try:
        main()
    except KeyError as error:
        raise SystemExit(f"variável de ambiente ausente: {error}") from error
    sys.exit(0)
