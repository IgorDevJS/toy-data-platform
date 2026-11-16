-- Cobertura da ponte de gênero: a ponte deduplica os títulos com a mesma regra dos fatos,
-- então todo título do catálogo tem ao menos um gênero (a fonte não tem título sem
-- `listed_in`), e todo título com nota também. Se a ponte e os fatos divergirem no grão
-- (ex.: a ponte parar de deduplicar por `show_id`), este teste retorna linhas e falha.

with bridge as (

    select distinct title_key from {{ ref('bridge_title_genre') }}

),

coverage as (

    select 'fct_catalog' as fato, count(*) as base_count, count(b.title_key) as covered_count
    from {{ ref('fct_catalog') }} f
    left join bridge b on b.title_key = f.title_key

    union all

    select 'fct_titles', count(*), count(b.title_key)
    from {{ ref('fct_titles') }} f
    left join bridge b on b.title_key = f.title_key

)

select *
from coverage
where base_count <> covered_count
