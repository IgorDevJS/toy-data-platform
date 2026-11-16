import sys; sys.path.insert(0, sys.argv[1]); from ev import *
E = sys.argv[2]
# ---------- 5-01: definição e janelas
o = ["# Fase 5 · Definição de crescimento e as duas janelas (SQL API do Cube, view catalog_overview)\n",
     "# Crescimento de um gênero = títulos dele que ENTRARAM no catálogo (year_added) na janela final",
     "# 2019–2020 menos os que entraram na janela inicial 2015–2016.",
     "# Por que janelas de 2 anos: 2015 sozinho tem 82 títulos e só 9 com nota; 2021 vai até setembro",
     "# (ano parcial); 2019 e 2020 são os dois últimos anos completos.",
     "# Atenção: a base é uma foto do catálogo em set/2021. Título que entrou e saiu antes disso não",
     "# aparece, então os anos antigos estão sub-representados (viés de sobrevivência).\n"]
cube("SELECT year_added, MEASURE(count_catalog_titles) AS catalogo, MEASURE(count_titles) AS com_nota, round(MEASURE(avg_rating)::numeric, 3) AS nota FROM catalog_overview WHERE year_added >= 2014 GROUP BY 1 ORDER BY 1", o)
o.append("# As duas janelas (o Cube conta cada título uma vez, sem agrupar por ano):")
cube("SELECT MEASURE(count_catalog_titles) AS catalogo, MEASURE(count_titles) AS com_nota, round(MEASURE(avg_rating)::numeric, 3) AS nota FROM catalog_overview WHERE year_added BETWEEN 2015 AND 2016", o)
cube("SELECT MEASURE(count_catalog_titles) AS catalogo, MEASURE(count_titles) AS com_nota, round(MEASURE(avg_rating)::numeric, 3) AS nota FROM catalog_overview WHERE year_added BETWEEN 2019 AND 2020", o)
open(f"{E}/5-01-definicao-e-janelas.txt","w").write("\n".join(o))
# ---------- 5-02: ranking
o = ["# Fase 5 · Gêneros que mais cresceram: títulos adicionados em 2015–16 × 2019–20 (SQL API do Cube)\n",
     "# Duas consultas, uma por janela; a tabela no fim junta as duas (Python, só subtração e divisão).",
     "# 'part.' = participação do gênero nos títulos adicionados na janela (510 e 3894). Um título",
     "# tem vários gêneros, então as participações somam mais que 100%.\n"]
q = "SELECT genre, MEASURE(count_catalog_titles) AS catalogo FROM catalog_overview WHERE year_added BETWEEN {} GROUP BY 1 ORDER BY 2 DESC"
cube(q.format("2015 AND 2016"), o); cube(q.format("2019 AND 2020"), o)
a = {r["genre"]: int(r["catalogo"]) for r in cube_rows(q.format("2015 AND 2016"))}
b = {r["genre"]: int(r["catalogo"]) for r in cube_rows(q.format("2019 AND 2020"))}
TA, TB = 510, 3894
rows = []
for g in set(a)|set(b):
    x, y = a.get(g,0), b.get(g,0)
    rows.append((g, x, y, y-x, 100*x/TA, 100*y/TB, 100*y/TB-100*x/TA))
rows.sort(key=lambda r: -r[3])
o.append("rank  gênero                      2015-16  2019-20  aumento   part.15-16  part.19-20   Δ p.p.")
for i,r in enumerate(rows,1):
    o.append(f"{i:>4}  {r[0]:<26}  {r[1]:>7}  {r[2]:>7}  {r[3]:>+7}   {r[4]:>9.1f}%  {r[5]:>9.1f}%  {r[6]:>+7.1f}")
o.append("\n# Maiores ganhos e perdas de participação (cresceram mais / menos que o catálogo):")
for r in sorted(rows, key=lambda r: -r[6])[:6]: o.append(f"  {r[0]:<26} {r[6]:>+5.1f} p.p.")
o.append("  ...")
for r in sorted(rows, key=lambda r: -r[6])[-6:]: o.append(f"  {r[0]:<26} {r[6]:>+5.1f} p.p.")
open(f"{E}/5-02-ranking-crescimento.txt","w").write("\n".join(o)+"\n")
json.dump([r[0] for r in rows[:10]], open(sys.argv[1]+"/top10.json","w"))
print("\n".join(o[-40:]))
