"""Junta os resultados da fase 4 em dados/fase4/h_resumo.json e imprime o essencial.

Le: v_real_vs_sim.json (hipercubo x simulacao), h_busca.json (buscas), h_simulacao.json
(simulacao das solucoes novas) e, da fase 3, v5_simulacao.json e os mapas v3_y_*.npy.
Nenhum numero e digitado aqui: tudo vem dos arquivos.
"""
import json

import numpy as np
import pandas as pd

from fase3_vidas.experimentos import vidas as V

from ..caminhos import DADOS, DADOS_FASE3

PARES = {"hc lam=0 K=20": "vidas lam=0 K=20", "hc lam=0 K=40": "vidas lam=0 K=40",
         "hc lam=0 K=livre": "vidas lam=0 K=livre", "hc lam=1 K=40": "vidas lam=1 K=40",
         "hc lam=1 K=livre": "vidas lam=1 K=livre",
         "reot vidas lam=0 K=40": "vidas lam=0 K=40", "reot vidas lam=0 K=livre": "vidas lam=0 K=livre",
         "reot vidas lam=1 K=livre": "vidas lam=1 K=livre", "reot p-median": "vidas lam=0 K=livre G=pm"}


def main():
    h = json.load(open(DADOS / "h_simulacao.json", encoding="utf-8"))
    hs = pd.DataFrame(h["rodadas"])
    f3 = pd.DataFrame(json.load(open(DADOS_FASE3 / "v5_simulacao.json", encoding="utf-8"))["rodadas"])
    f3 = f3[f3.servico == "central"]
    busca = json.load(open(DADOS / "h_busca.json", encoding="utf-8"))
    fin = V.finalistas()
    sol = {r["partida"] + f" lam={r['lam']:g} K={r['K']} s{r['semente']}": r for r in busca}
    linhas = {}
    for a, b in PARES.items():
        x = hs[hs.config == a].sort_values("semente")
        y = f3[f3.config == b].sort_values("semente")
        d = x.sim_vidas.values - y.sim_vidas.values
        r = h["hc"][a]
        yB, yA = ((np.array(r["yB"]), np.array(r["yA"])) if a.startswith("hc") else (None, None))
        difpos = None
        if yB is not None:
            yb3, ya3 = fin[b]
            difpos = int((np.abs(yB - yb3).sum() + np.abs(yA - ya3).sum()) // 2)
        linhas[a] = dict(fase3=b, sim_fase3=float(y.sim_vidas.mean()), sim_hc=float(x.sim_vidas.mean()),
                         dif_pareada_media=float(d.mean()), dif_min=float(d.min()), dif_max=float(d.max()),
                         hc_vidas=r["vidas"], movidas_desde_hoje=r["movidas"], unidades_diferentes_da_fase3=difpos)
    # variabilidade entre sementes da busca (so partidas de hoje)
    g = {}
    for q in busca:
        if q["partida"] == "hoje":
            g.setdefault(f"lam={q['lam']:g} K={'livre' if q['K'] is None else q['K']}", []).append(q["hc"]["vidas"])
    var = {k: dict(min=min(v), max=max(v), n=len(v)) for k, v in g.items()}
    out = dict(pares=linhas, vidas_hc_entre_sementes=var)
    (DADOS / "h_resumo.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("config | sim fase3 | sim HC | dif pareada (min..max) | unidades diferentes da solucao fase 3")
    for a, v in linhas.items():
        print(f"{a:26s} {v['sim_fase3']:6.2f} {v['sim_hc']:6.2f} {v['dif_pareada_media']:+.2f} ({v['dif_min']:+.2f}..{v['dif_max']:+.2f})  {v['unidades_diferentes_da_fase3']}")
    print("vidas (hipercubo) entre sementes da busca:", {k: (round(v['min'], 2), round(v['max'], 2)) for k, v in var.items()})


if __name__ == "__main__":
    main()
