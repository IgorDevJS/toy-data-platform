-- Fato do catálogo: grão de exatamente um título do catálogo da Netflix (title_key).
--
-- Por que um fato novo, e não ampliar o `fct_titles`: o `fct_titles` só tem os títulos
-- que também estão no Metacritic (inner join com a crítica), 1813 de ~8800. Contar quantos
-- títulos entraram no catálogo por ano precisa de todos. São duas populações diferentes,
-- então são duas métricas com nomes diferentes ("títulos do catálogo" × "títulos com nota
-- da crítica"), e não uma métrica que muda de valor conforme o join (Aula 4, slide 9).
--
-- A regra de deduplicação é a mesma do `fct_titles` e das pontes (`int_titles_attributes`,
-- menor `show_id`). `has_critic_rating` vem do próprio `fct_titles`, e não de um novo join
-- com o Metacritic: a regra de qual título "tem nota" fica num lugar só.

select
    n.title_key,
    n.title,
    n.type as type_key,
    n.release_year as year_key,
    n.date_added,
    -- ano de entrada no catálogo; nulo para os 10 títulos sem data na fonte
    year(n.date_added) as added_year,
    r.title_key is not null as has_critic_rating
from {{ ref('int_titles_attributes') }} n
left join {{ ref('fct_titles') }} r on r.title_key = n.title_key
