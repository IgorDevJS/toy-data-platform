# Trabalho final: crescimento do catálogo por gênero

Material de apoio do relatório técnico do trabalho final da disciplina Data Engineering &
Architecture. A pergunta: *quais gêneros mais cresceram no catálogo da Netflix a partir de
2015, e a nota da crítica desses gêneros acompanhou o crescimento?*

As mudanças na plataforma estão nos commits da branch `feat/crescimento-catalogo`
(`dlt`, `dbt`, `cube`, `superset`, `airflow`). Esta pasta guarda só o que prova que elas
funcionam.

## `evidencias/`

Uma evidência por arquivo, com o nome `<fase>-<nº>-<descrição>`. O relatório cita cada uma
pelo código (por exemplo, `1-04` é o teste do dbt pegando o erro de grão).

| Fase | O quê |
|---|---|
| 0 | estado inicial da plataforma, antes de qualquer mudança (a régua de regressão) |
| 1 | dbt: `fct_catalog`, pontes do catálogo, frescor da fonte, snapshot, teste falhando |
| 2 | Cube: cubo `catalog`, view `catalog_overview`, Cube × SQL à mão no Trino |
| 3 | Superset: dashboard novo pelo bootstrap, idempotência, subida limpa |
| 4 | Airflow: DAG `movies_daily`, paralelismo, retries, idempotência |
| 5 | a resposta: ranking de crescimento, nota por janela, IC 95% e sensibilidade |
| 6 | a geração deste relatório (Markdown → DOCX → PDF) e as conferências feitas nela |

Os `.txt` são saídas de terminal, com o comando que as gerou e um comentário dizendo o que
provam. Os `.png` são prints tirados com o Chrome em modo headless.

## `ferramentas/`

- `prints.js`: tira os prints (Superset, Airflow, dbt docs, Cube Playground) com o
  `playwright-core` e o Chrome do host. Uso: `node prints.js <pasta> superset airflow docs`.
  O caminho do `playwright-core`, no início do arquivo, é o do cache do `npx` da máquina onde rodou.
- `fase5/`: scripts das evidências `5-01` a `5-05`, só com a biblioteca padrão do Python.
  Com a stack no ar, rodá-los de novo reproduz os arquivos (ver `fase5/README.md`).
