import sys; sys.path.insert(0, sys.argv[1]); from ev import *
E = sys.argv[2]; TOP = json.load(open(sys.argv[1]+"/top10.json"))
inlist = ", ".join("'"+g.replace("'","''")+"'" for g in TOP)
W = {"2015-16": "2015 AND 2016", "2019-20": "2019 AND 2020"}
# ---------- 5-03: nota por janela, só Cube
o = ["# Fase 5 · Nota média da crítica dos 10 gêneros que mais cresceram, por janela (SQL API do Cube)\n",
     "# 'com_nota' = MEASURE(count_titles): títulos com linha no fct_titles. Atenção: 155 dos 1813 têm",
     "# rating nulo ('tbd' no Metacritic) e entram nessa contagem, mas não na média (ver 5-04).\n"]
q = ("SELECT genre, MEASURE(count_catalog_titles) AS catalogo, MEASURE(count_titles) AS com_nota, "
     "round(MEASURE(avg_rating)::numeric, 3) AS nota FROM catalog_overview "
     "WHERE year_added BETWEEN {} AND genre IN (" + inlist + ") GROUP BY 1 ORDER BY 2 DESC")
cubev = {}
for w, rng in W.items():
    o.append(f"# janela {w}")
    cube(q.format(rng), o)
    for r in cube_rows(q.format(rng)): cubev[(r["genre"], w)] = r
o.append("# o catálogo inteiro, para comparar:")
for w, rng in W.items():
    cube(f"SELECT MEASURE(count_catalog_titles) AS catalogo, MEASURE(count_titles) AS com_nota, round(MEASURE(avg_rating)::numeric, 3) AS nota FROM catalog_overview WHERE year_added BETWEEN {rng}", o)
o.append("# ano a ano, os 3 que mais cresceram (o que o dashboard mostra):")
cube("SELECT genre, year_added, MEASURE(count_catalog_titles) AS catalogo, MEASURE(count_titles) AS com_nota, round(MEASURE(avg_rating)::numeric, 3) AS nota FROM catalog_overview WHERE year_added BETWEEN 2015 AND 2021 AND genre IN ('Dramas', 'International Movies', 'Comedies') GROUP BY 1, 2 ORDER BY 1, 2", o)
open(f"{E}/5-03-nota-por-janela-cube.txt","w").write("\n".join(o))

# ---------- 5-04: IC 95% no Trino
def tpdf(x, v): return math.exp(math.lgamma((v+1)/2)-math.lgamma(v/2)-0.5*math.log(v*math.pi)-(v+1)/2*math.log1p(x*x/v))
def tcdf(x, v, n=2000):
    h = x/n; s = tpdf(0,v)+tpdf(x,v)
    s += sum((4 if i%2 else 2)*tpdf(i*h,v) for i in range(1,n))
    return 0.5 + s*h/3
def tq(v, p=0.975):
    lo, hi = 0.0, 20.0
    for _ in range(60):
        m = (lo+hi)/2
        lo, hi = (m, hi) if tcdf(m, v) < p else (lo, m)
    return (lo+hi)/2
o = ["# Fase 5 · Intervalo de confiança de 95% da nota, por gênero e janela (SQL à mão no Trino)\n",
     "# O Cube não tem desvio-padrão; esta consulta é conferência à parte, e a média dela tem de bater",
     "# com a do Cube (5-03), coluna 'cube'. n = títulos com rating NÃO nulo (count(rating)).",
     "# IC da média: m ± t(0,975; n-1)·s/√n. Diferença: Welch, t com graus de liberdade de",
     "# Welch–Satterthwaite (Python, sem bibliotecas). A ponte tem um par (título, gênero) por linha,",
     "# então agrupar por gênero conta cada título uma vez. Com n < 5 numa janela, não há IC.\n"]
sql = ("select b.genre_key as genre, case when c.added_year between 2015 and 2016 then '2015-16' else '2019-20' end as janela, "
       "count(distinct c.title_key) as catalogo, count(t.title_key) as com_linha, count(t.rating) as n, "
       "round(avg(t.rating), 3) as media, round(stddev_samp(t.rating), 3) as dp "
       "from refined.ml.fct_catalog c join refined.ml.bridge_title_genre b on b.title_key = c.title_key "
       "left join refined.ml.fct_titles t on t.title_key = c.title_key "
       "where c.added_year in (2015, 2016, 2019, 2020) and b.genre_key in (" + inlist + ") group by 1, 2 order by 1, 2")
trino(sql, o)
sqlt = ("select case when c.added_year between 2015 and 2016 then '2015-16' else '2019-20' end as janela, "
        "count(distinct c.title_key) as catalogo, count(t.title_key) as com_linha, count(t.rating) as n, "
        "round(avg(t.rating), 3) as media, round(stddev_samp(t.rating), 3) as dp "
        "from refined.ml.fct_catalog c left join refined.ml.fct_titles t on t.title_key = c.title_key "
        "where c.added_year in (2015, 2016, 2019, 2020) group by 1 order by 1")
trino(sqlt, o)
st = {(r["genre"], r["janela"]): r for r in trino_rows(sql)}
for r in trino_rows(sqlt): st[("(catálogo inteiro)", r["janela"])] = r
MIN_N = 5
for w, rng in W.items():
    r = cube_rows(f"SELECT round(MEASURE(avg_rating)::numeric, 3) AS nota FROM catalog_overview WHERE year_added BETWEEN {rng}")[0]
    cubev[("(catálogo inteiro)", w)] = r
o.append("gênero                      janela  linhas    n  média   cube    IC 95% média  | Δ nota   IC 95% da Δ     conclusão")
res = {}
for g in TOP + ["(catálogo inteiro)"]:
    cells = []
    for w in W:
        r = st[(g, w)]; n = int(r["n"]); m = float(r["media"]); s = float(r["dp"]) if r["dp"] else float("nan")
        h = tq(n-1)*s/math.sqrt(n) if n >= MIN_N else float("nan")
        c = cubev.get((g, w), {}).get("nota", "")
        ok = "=" if c and abs(float(c)-m) < 0.0015 else "≠"
        cells.append((w, int(r["com_linha"]), n, m, s, h, c, ok))
    (_, _, n1, m1, s1, _, _, _), (_, _, n2, m2, s2, _, _, _) = cells
    d = m2-m1
    if min(n1, n2) >= MIN_N:
        se = math.sqrt(s1*s1/n1 + s2*s2/n2); df = se**4/((s1*s1/n1)**2/(n1-1) + (s2*s2/n2)**2/(n2-1))
        hd = tq(df)*se; lo, hi = d-hd, d+hd
        concl = "subiu" if lo > 0 else "caiu" if hi < 0 else "sem diferença clara"
    else:
        lo = hi = None; concl = f"amostra insuficiente"
    res[g] = dict(n1=n1, m1=m1, n2=n2, m2=m2, d=d, lo=lo, hi=hi, concl=concl,
                  h1=cells[0][5], h2=cells[1][5],
                  cat1=int(st[(g,'2015-16')]["catalogo"]), cat2=int(st[(g,'2019-20')]["catalogo"]))
    for i, (w, cl, n, m, s, h, c, ok) in enumerate(cells):
        ic = f"[{m-h:.2f}; {m+h:.2f}]" if h == h else "      —     "
        dd = f"[{lo:+.2f}; {hi:+.2f}]" if lo is not None else "      —      "
        tail = f"| {d:+.3f}  {dd}  {concl}" if i == 1 else "|"
        o.append(f"{g if i==0 else '':<26}  {w}  {cl:>6}  {n:>3}  {m:.3f}  {c:>5} {ok}  {ic}  {tail}")
o.append("\n# 'linhas' = títulos com linha no fct_titles (o que count_titles conta); 'n' = com rating não nulo.")
o.append("# '=' : a média do Trino bate com a do Cube (5-03) até a 3ª casa.")
open(f"{E}/5-04-ic95-trino.txt","w").write("\n".join(o)+"\n")
json.dump(res, open(sys.argv[1]+"/res.json","w"), indent=1)
print("\n".join(o[-28:]))
