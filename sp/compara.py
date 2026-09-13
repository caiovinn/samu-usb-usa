"""Compara o planejamento classico com o planejamento sob Huff.

A pergunta do artigo: se voce planeja supondo que todo setor e atendido pela
unidade MAIS PROXIMA (p-median, o que o prototipo atual faz), mas a demanda se
reparte segundo Huff, quanto voce perde? E o contrario: a solucao desenhada sob
Huff perde muito na metrica classica?

Avalia as tres configuracoes (atual, p-median, Huff) nas DUAS metricas.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import huff2sfca as H
import mudanca
import pmedian
from otimiza import joelho
from roda import DADOS, carrega


def classico(T, pop, sel_usb, sel_usa):
    """Metrica classica: tempo ate a mais proxima, ponderado por populacao."""
    w = pop / pop.sum()
    t_usa = T[np.unique(sel_usa)].min(axis=0)
    t_qq = T[np.unique(np.concatenate([sel_usb, sel_usa]))].min(axis=0)
    return {"t_usa_medio": float((t_usa * w).sum()),
            "t_usa_mediana": float(np.median(t_usa)),
            "t_qualquer_medio": float((t_qq * w).sum()),
            "pop_usa_20min": float(100 * w[t_usa <= 20].sum()),
            "pop_usb_10min": float(100 * w[t_qq <= 10].sum())}


def main():
    st, cd, T = carrega()
    pop = st["pop"].values.astype(float)
    n_usb, n_usa = int(cd.n_usb.sum()), int(cd.n_usa.sum())
    p = n_usb + n_usa
    x0 = np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                         np.repeat(cd.id.values, cd.n_usa.values)])
    D = mudanca.matriz_km(cd.lat.values, cd.lon.values)

    print(f"p-median com p = {p} locais (hipotese classica)...", flush=True)
    sel, custo = pmedian.resolve(T, pop, p, verbose=True)
    print(f"  custo p-median: {custo:.4f} min ate a mais proxima")

    # o planejador classico distribui as USA entre os locais escolhidos,
    # tambem pela regra da mais proxima
    sub = T[sel]
    pos, _ = pmedian.resolve(sub, pop, n_usa)
    sel_usa_pm = sel[pos]
    sel_usb_pm = np.array([s for s in sel if s not in set(map(int, sel_usa_pm))])
    # o p-median escolhe locais distintos; sobram p - n_usa para as USB
    x_pm = np.concatenate([sel_usb_pm, sel_usa_pm])

    # melhor solucao sob Huff (lambda = 0.1, o joelho da varredura). O joelho
    # sai no MESMO espaco que o otimizador usou — tempo + preco da mudanca —
    # senao esta figura e a de Lorenz apontam solucoes diferentes.
    LAM = 0.1
    X = np.load(DADOS / f"sp_pareto_x_lam{LAM:g}.npy")
    pf = pd.read_parquet(DADOS / f"sp_pareto_lam{LAM:g}.parquet")
    obj = (pf["f_obj"].values if "f_obj" in pf
           else pf.f_tempo.values + LAM * pf.km_total.values / len(x0))
    x_huff = X[joelho(np.c_[obj, pf.f_gini.values])]

    casos = {"atual": x0, "p-median (classico)": x_pm, "Huff+2SFCA": x_huff}
    linhas = []
    for nome, x in casos.items():
        x = np.asarray(x)
        r = H.avalia(T, pop, x[:n_usb], x[n_usb:], f=None)
        c = classico(T, pop, x[:n_usb], x[n_usb:])
        linhas.append({
            "config": nome,
            "huff_tempo": r["f_tempo"], "huff_gini": r["f_gini"],
            "huff_usa20": r["pct_pop_usa_20min"],
            "classico_t_usa": c["t_usa_medio"],
            "classico_t_qualquer": c["t_qualquer_medio"],
            "classico_usa20": c["pop_usa_20min"],
            "km_mudanca": mudanca.custo(x, x0, D, n_usb),
            "movidas": mudanca.movidas(x, x0, n_usb),
            "locais": int((np.bincount(x) > 0).sum())})
    df = pd.DataFrame(linhas)
    df.to_parquet(DADOS / "sp_comparacao.parquet")

    print("\n== avaliado sob Huff (a demanda se reparte) ==")
    print(f"{'config':>22}{'E[T] min':>10}{'Gini USA':>10}{'USA<=20min':>12}")
    for _, r in df.iterrows():
        print(f"{r.config:>22}{r.huff_tempo:10.3f}{r.huff_gini:10.4f}"
              f"{r.huff_usa20:11.1f}%")
    print("\n== avaliado pela regra classica (sempre a mais proxima) ==")
    print(f"{'config':>22}{'t USA':>10}{'t qualquer':>12}{'USA<=20min':>12}")
    for _, r in df.iterrows():
        print(f"{r.config:>22}{r.classico_t_usa:10.3f}{r.classico_t_qualquer:12.3f}"
              f"{r.classico_usa20:11.1f}%")
    print("\n== custo de mudanca ==")
    for _, r in df.iterrows():
        print(f"{r.config:>22}  {r.movidas:3.0f} unidades, {r.km_mudanca:6.0f} km, "
              f"{r.locais:.0f} locais")

    a, pm, hf = linhas[0], linhas[1], linhas[2]
    perda = 100 * (pm["huff_tempo"] / hf["huff_tempo"] - 1)
    preco = 100 * (hf["classico_t_usa"] / pm["classico_t_usa"] - 1)
    print(f"\nplanejar pela regra classica custa {perda:+.1f}% de tempo esperado "
          f"quando a demanda se reparte")
    print(f"planejar sob Huff custa {preco:+.1f}% na metrica classica")
    json.dump(linhas, open(DADOS / "sp_comparacao.json", "w"), indent=2, default=float)


if __name__ == "__main__":
    main()
