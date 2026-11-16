-- Ponte título ↔ gênero: uma linha por par (título, gênero).
--
-- `listed_in` é multi-valor ("Dramas, Comedies, ..."): o `unnest` transforma a lista
-- em linhas. Um título com N gêneros aparece exatamente N vezes — então uma métrica
-- fatiada por gênero conta cada título uma vez por gênero que ele tem, e nunca duas
-- vezes pelo mesmo gênero.
--
-- A ponte parte do catálogo inteiro (`fct_catalog`), e não só dos títulos com nota:
-- assim a mesma regra serve aos dois fatos. O `fct_titles` é um subconjunto do catálogo,
-- e quem consulta a partir dele (o cubo `titles`) só alcança os pares dos seus títulos,
-- porque o join parte do fato.

select
    f.title_key,
    trim(g.genre) as genre_key,
    f.title_key || '|' || trim(g.genre) as title_genre_key
from {{ ref('fct_catalog') }} f
inner join {{ ref('int_titles_attributes') }} t on t.title_key = f.title_key
cross join unnest(split(t.listed_in, ',')) as g (genre)
where trim(g.genre) <> ''
