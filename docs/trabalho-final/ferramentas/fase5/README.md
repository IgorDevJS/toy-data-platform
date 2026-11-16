# Scripts das evidências da Fase 5

Geram `evidencias/5-01` a `5-05` a partir da SQL API do Cube e do Trino (stack no ar).
Rodar a partir desta pasta, nesta ordem (o 2º lê o `top10.json` do 1º, e o 3º reusa o IC do 2º):

    python3 f5_12.py . ../../evidencias    # 5-01 definição/janelas, 5-02 ranking
    python3 f5_34.py . ../../evidencias    # 5-03 nota por janela (Cube), 5-04 IC 95% (Trino)
    python3 f5_5.py  . ../../evidencias    # 5-05 sensibilidade da janela inicial

`ev.py` tem os atalhos (psql no Cube via `postgres:16` na `platform-net`; `docker exec` no
Trino). Só biblioteca padrão; o quantil do t de Student é calculado por integração numérica.
