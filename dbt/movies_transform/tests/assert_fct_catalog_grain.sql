-- Grão do catálogo: um título por linha, e todos os títulos da origem.
--
-- 1. `count(*) = count(distinct title_key)`: nenhum título aparece duas vezes (o dedupe
--    por `show_id` funcionou).
-- 2. O catálogo tem tantos títulos quanto a trusted tem títulos distintos: o dedupe não
--    perdeu nenhum título no caminho.
-- 3. Os títulos marcados com `has_critic_rating` são exatamente os do `fct_titles`.
-- Se qualquer uma das três falhar, o teste retorna a linha com os números e falha.

with catalog as (

    select
        count(*) as n_rows,
        count(distinct title_key) as n_keys,
        count_if(has_critic_rating) as n_rated
    from {{ ref('fct_catalog') }}

),

source as (

    select count(distinct lower(trim(title))) as n_titles
    from {{ ref('netflix_titles') }}

),

rated as (

    select count(*) as n_rated from {{ ref('fct_titles') }}

)

select
    c.n_rows,
    c.n_keys,
    s.n_titles as source_titles,
    c.n_rated as catalog_rated,
    r.n_rated as fct_titles_rows
from catalog c
cross join source s
cross join rated r
where c.n_rows <> c.n_keys
   or c.n_rows <> s.n_titles
   or c.n_rated <> r.n_rated
