-- Ponte título ↔ país: uma linha por par (título, país).
--
-- `country` também é multi-valor ("United States, India"). Como a ponte de gênero, parte
-- do catálogo inteiro (`fct_catalog`), que contém os títulos do `fct_titles`. Títulos sem
-- país na origem (831 no catálogo) não entram, por isso a ponte não cobre necessariamente
-- todo o fato — os `relationships` garantem que toda linha da ponte aponta para um título
-- existente.

select
    f.title_key,
    trim(c.country) as country_key,
    f.title_key || '|' || trim(c.country) as title_country_key
from {{ ref('fct_catalog') }} f
inner join {{ ref('int_titles_attributes') }} t on t.title_key = f.title_key
cross join unnest(split(t.country, ',')) as c (country)
where trim(c.country) <> ''
