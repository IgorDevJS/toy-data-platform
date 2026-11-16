# Camada semântica — Cube Core

Modelo semântico como código (YAML) sobre o catálogo `refined.ml` no Trino. Declara
**medidas** e **dimensões** governadas e as serve por REST, por SQL API (protocolo
Postgres) e pelo Playground. É a mesma definição que o Superset e o agente MCP consomem.

## Subir

Sobe junto do stack:

```bash
docker compose up -d
```

| Interface | Endereço |
| - | - |
| REST (`/v1/*`) | `http://localhost:4000/cubejs-api/v1` |
| Playground | `http://localhost:4000` |
| SQL API (Postgres) | `localhost:15432` — usuário/senha em `cube/.env` |

A configuração (fonte Trino, credenciais da SQL API) fica em `cube/.env`. A senha do
Trino é intencionalmente vazia: o Trino local não usa TLS e recusa senha em HTTP
(`Password not allowed for insecure authentication`).

## Modelo

`model/cubes/` declara os cubos; `model/views/` a fachada plana que os consumidores usam.

| Cubo | Papel |
| - | - |
| `titles` | Fato no grão de um título **com nota da crítica** (`fct_titles`, 1813). Define as medidas da crítica. |
| `catalog` | Fato no grão de um título **do catálogo inteiro** (`fct_catalog`, 8802). Define `count_catalog_titles`. |
| `title_genre` | Ponte título ↔ gênero (dimensão multi-valor). |
| `title_country` | Ponte título ↔ país (dimensão multi-valor). |
| `titles_overview` (view) | Raiz `titles`: medidas da crítica por `release_year`, `year_added`, `title_type`, `genre`, `country`. |
| `catalog_overview` (view) | Raiz `catalog`: o catálogo e a crítica lado a lado, pelas mesmas dimensões e `has_critic_rating`. |

| Medida | Cubo | População |
| - | - | - |
| `count_catalog_titles` | `catalog` | títulos do catálogo inteiro (8802) |
| `count_titles` | `titles` | títulos com nota da crítica (1813) |
| `avg_rating` | `titles` | nota média da crítica |
| `total_votes` | `titles` | total de votos da crítica |

Dimensões: `release_year`, `year_added` (ano de entrada no catálogo; nulo para 10
títulos, e 2021 é parcial porque a fonte vai até setembro), `title_type`, `genre`,
`country` e, só no `catalog_overview`, `has_critic_rating`.

**Duas contagens, dois nomes.** "Quantos títulos" tem duas respostas: 8802 no
catálogo e 1813 com nota da crítica. Em vez de uma métrica que muda de valor
conforme o join, são duas medidas, cada uma definida uma vez no seu cubo. O
`catalog` liga no `titles` (`one_to_one`, LEFT JOIN), então a `catalog_overview`
conta o catálogo e, na mesma linha, mostra a nota dos títulos que a têm. A
`titles_overview` não mudou de raiz: os números dela (dashboard original, agente)
continuam os mesmos.

Fatiar por uma dimensão multi-valor **não** infla as medidas: o `primary_key:
title_key` no fato faz o Cube deduplicar pelo grão ao atravessar a ponte.

A dimensão de ponte entra por **LEFT JOIN** — é o que permite fatiar sem perder o
fato. Como país é parcial na origem, os títulos sem país aparecem numa linha
`country = null` (36 dos 1813). Quem pergunta por país filtra
`{"member": "titles_overview.country", "operator": "set"}`; é o que o demo do MCP
faz (`mcp/README.md`).

## Consultar

REST:

```bash
curl -sG http://localhost:4000/cubejs-api/v1/load \
  --data-urlencode 'query={
    "measures": ["titles_overview.count_titles", "titles_overview.avg_rating"],
    "dimensions": ["titles_overview.genre"]
  }'
```

SQL API (protocolo Postgres):

```bash
PGPASSWORD=cubecubecube psql -h localhost -p 15432 -U cube -d cube \
  -c "SELECT genre, MEASURE(count_titles), MEASURE(avg_rating)
      FROM titles_overview GROUP BY 1"
```

Catálogo por ano de entrada e gênero, com a nota da crítica ao lado:

```bash
PGPASSWORD=cubecubecube psql -h localhost -p 15432 -U cube -d cube \
  -c "SELECT year_added, genre, MEASURE(count_catalog_titles) AS catalogo,
             MEASURE(count_titles) AS com_nota, MEASURE(avg_rating) AS nota
      FROM catalog_overview WHERE year_added >= 2015 GROUP BY 1, 2 ORDER BY 1, 2"
```

Sem dimensão, a `catalog_overview` dá `8802` títulos no catálogo, `1813` com nota,
nota `6.625` e `322914` votos: os mesmos da `titles_overview`.

Fazer essa conta à mão no Trino, juntando o fato com a ponte e usando `count(*)`,
infla: em 2019 dá 4504 linhas para 2015 títulos, porque cada título conta uma vez
por gênero. O Cube faz `COUNT(DISTINCT)` e calcula a média por uma subconsulta de
chaves (ver `/cubejs-api/v1/sql`).
