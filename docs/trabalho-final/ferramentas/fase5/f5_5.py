import sys; sys.path.insert(0, sys.argv[1]); from ev import *
E = sys.argv[2]
src = open(sys.argv[1]+"/f5_34.py").read()
exec(src[src.index("def tpdf"):src.index("o = [\"# Fase 5 · Intervalo")])
TOP3 = ["International Movies", "Dramas", "Comedies"]
o = ["# Fase 5 · Sensibilidade: e se a janela inicial fosse 2015–2017 (mais títulos com nota)?\n",
     "# Mesmo cálculo de 5-04 (Trino, IC 95%, Welch), só os 3 gêneros que mais cresceram e o catálogo.",
     "# 2017 sozinho tem 1188 títulos e 192 com linha no fct_titles, mais que 2015–16 juntos (77).\n"]
def run(early, late, tag):
    jan = f"case when c.added_year between {early[0]} and {early[1]} then 'inicial' else 'final' end"
    per = f"(c.added_year between {early[0]} and {early[1]} or c.added_year between {late[0]} and {late[1]})"
    agg = "count(t.rating) as n, round(avg(t.rating), 3) as media, round(stddev_samp(t.rating), 3) as dp"
    sql = (f"select b.genre_key as genre, {jan} as janela, {agg} from refined.ml.fct_catalog c "
           "join refined.ml.bridge_title_genre b on b.title_key = c.title_key "
           "left join refined.ml.fct_titles t on t.title_key = c.title_key "
           f"where {per} and b.genre_key in ('International Movies', 'Dramas', 'Comedies') group by 1, 2 "
           f"union all select 'CATALOGO_INTEIRO', {jan}, {agg} from refined.ml.fct_catalog c "
           f"left join refined.ml.fct_titles t on t.title_key = c.title_key where {per} group by 1, 2 order by 1, 2 desc")
    o.append(f"## {tag}: inicial {early[0]}–{early[1]} × final {late[0]}–{late[1]}")
    trino(sql, o)
    st = {(r["genre"].replace('CATALOGO_INTEIRO', '(catálogo inteiro)'), r["janela"]): r for r in trino_rows(sql)}
    for g in TOP3 + ["(catálogo inteiro)"]:
        a, b = st[(g, "inicial")], st[(g, "final")]
        n1, m1, s1 = int(a["n"]), float(a["media"]), float(a["dp"]); n2, m2, s2 = int(b["n"]), float(b["media"]), float(b["dp"])
        se = math.sqrt(s1*s1/n1 + s2*s2/n2); df = se**4/((s1*s1/n1)**2/(n1-1) + (s2*s2/n2)**2/(n2-1)); h = tq(df)*se; d = m2-m1
        concl = "subiu" if d-h > 0 else "caiu" if d+h < 0 else "sem diferença clara"
        o.append(f"  {g:<22} n {n1:>3} → {n2:>3}   {m1:.3f} → {m2:.3f}   Δ {d:+.3f}  IC95 [{d-h:+.2f}; {d+h:+.2f}]  {concl}")
    o.append("")
run((2015, 2016), (2019, 2020), "definição escolhida (confere com 5-04)")
run((2015, 2017), (2019, 2020), "sensibilidade")
open(f"{E}/5-05-sensibilidade-janela.txt", "w").write("\n".join(o) + "\n")
print("\n".join(l for l in o if l.startswith("  ") or l.startswith("##")))
