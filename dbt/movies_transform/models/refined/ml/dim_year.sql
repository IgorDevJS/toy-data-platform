-- Dimensão de tempo: um ano do calendário por linha.
--
-- É uma dimensão "role-playing" (Kimball): a mesma tabela de anos serve ao ano de
-- lançamento (`year_key`) e ao ano de entrada no catálogo (`added_year`). Por isso ela é a
-- união dos dois papéis: todo ano que um fato usa existe aqui por construção, mesmo que
-- algum dia apareça um ano de entrada sem nenhum lançamento.

select release_year as year_key
from {{ ref('netflix_titles') }}
where release_year is not null

union

select year(date_added) as year_key
from {{ ref('netflix_titles') }}
where date_added is not null
