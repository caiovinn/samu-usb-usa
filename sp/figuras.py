"""Figuras da fase 2 (São Paulo). Gera figs/sp_*.png.

    python sp/figuras.py

Cores: a rampa azul ordinal codifica lambda (grandeza ordenada); laranja e o
p-median classico; cinza e a configuracao atual, que e referencia e nao serie.
Ambas as paletas passaram no validador (CVD, contraste, degraus).
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import huff2sfca as H
import mudanca
from otimiza import joelho

AQUI = Path(__file__).resolve().parent
DADOS, FIG = AQUI.parent / "dados", AQUI.parent / "figs"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 130,
                     "font.size": 9, "axes.grid": True, "grid.alpha": .25,
                     "axes.spines.top": False, "axes.spines.right": False})

RAMPA = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]   # lambda, claro -> escuro
LAMS_FIG = [0.0, 0.1, 0.3, 1.0]
C_PM, C_ATUAL = "#eb6834", "#52514e"
C_USB, C_USA = "#2a78d6", "#eb6834"
TINTA, TINTA2 = "#0b0b0b", "#52514e"


def carrega():
    res = json.load(open(DADOS / "sp_resultado.json"))
    comp = json.load(open(DADOS / "sp_comparacao.json"))
    st = pd.read_parquet(DADOS / "sp_setores.parquet")
    cd = pd.read_parquet(DADOS / "sp_candidatos.parquet")
    T = np.ascontiguousarray(np.load(DADOS / "sp_tempos.npy").T)
    return res, comp, st, cd, T


def _nao_dominada(f, cols=("f_tempo", "f_gini")):
    """Subconjunto nao dominado NO ESPACO EXIBIDO.

    Para lambda > 0 o NSGA-II ordenou os individuos pelo tempo PENALIZADO, mas
    o grafico mostra o tempo puro. Nesse outro espaco a frente guardada nao e
    mais uma frente — sem filtrar, sai um zigue-zague. O que interessa mostrar
    e a regiao alcancavel sob aquele orcamento de mudanca.
    """
    V = f[list(cols)].values
    manter = [not ((V <= v).all(axis=1) & (V < v).any(axis=1)).any()
              for v in V]
    return f[np.array(manter)].sort_values(list(cols)[0])


def _joelho_lam(f, lam, p=123):
    """Joelho no mesmo espaco que o otimizador usou: tempo + preco da mudanca."""
    obj = (f["f_obj"].values if "f_obj" in f
           else f.f_tempo.values + lam * f.km_total.values / p)
    return joelho(np.c_[obj, f.f_gini.values])


def _vg(x):
    return f"{x:g}".replace(".", ",")


# ------------------------------------------------------ 1 fronteiras de Pareto
def fig_pareto(res):
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for cor, lam in zip(RAMPA, LAMS_FIG):
        d = res["por_lambda"][f"{lam:g}"]["fronteira"]
        f = _nao_dominada(pd.DataFrame(d))
        ax.plot(f.f_tempo, f.f_gini, "-o", color=cor, lw=2, ms=5,
                label=f"λ = {_vg(lam)}", zorder=3)
        p = f.iloc[-1]
        ax.annotate(f"λ={_vg(lam)}", (p.f_tempo, p.f_gini), color=cor,
                    fontsize=8, fontweight="bold",
                    xytext=(6, 0), textcoords="offset points", va="center")

    a = res["atual"]
    ax.plot(a["f_tempo"], a["f_gini"], "*", color=C_ATUAL, ms=16, zorder=5,
            label="configuração atual")
    ax.annotate("atual", (a["f_tempo"], a["f_gini"]), color=C_ATUAL, fontsize=8,
                xytext=(-8, 8), textcoords="offset points", ha="right")

    pm = next(c for c in json.load(open(DADOS / "sp_comparacao.json"))
              if c["config"].startswith("p-median"))
    ax.plot(pm["huff_tempo"], pm["huff_gini"], "s", color=C_PM, ms=9, zorder=5,
            label="p-median clássico")
    ax.annotate("p-median", (pm["huff_tempo"], pm["huff_gini"]), color=C_PM,
                fontsize=8, xytext=(8, 6), textcoords="offset points")

    ax.set_xlabel("tempo esperado de resposta (min)  ←  melhor")
    ax.set_ylabel("Gini da acessibilidade USA  ←  melhor")
    ax.set_title("Preço da mudança desloca a fronteira, não só o ponto sobre ela",
                 fontsize=10, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="center left", ncols=2)
    fig.tight_layout(); fig.savefig(FIG / "sp_01_pareto.png"); plt.close(fig)


# --------------------------------------------------------- 2 ganho x mudanca
def fig_ganho(res):
    lams = sorted(res["por_lambda"], key=float)
    j = pd.DataFrame([res["por_lambda"][l]["joelho"] for l in lams])
    j["lam"] = [float(l) for l in lams]
    a = res["atual"]

    fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.8))
    for ax, col, rotulo, base in (
            (axs[0], "f_gini", "Gini da acessibilidade USA", a["f_gini"]),
            (axs[1], "f_tempo", "tempo esperado de resposta (min)", a["f_tempo"])):
        ax.axhline(base, color=C_ATUAL, ls="--", lw=1.2, zorder=1)
        ax.text(j.km_total.max() * .99, base, " atual", color=C_ATUAL, fontsize=8,
                va="bottom", ha="right")
        o = j.sort_values("km_total")
        ax.plot(o.km_total, o[col], "-", color=RAMPA[2], lw=2, zorder=2)
        ax.scatter(o.km_total, o[col], color=RAMPA[2], s=42, zorder=3)
        # rotulo so nos lambda que marcam o caminho; 0,01 e 0,03 ficam em
        # cima de 0 e viravam um amontoado de texto
        for _, r in o.iterrows():
            if r.lam not in (0.0, 0.1, 0.3, 1.0):
                continue
            ax.annotate(f"λ={_vg(r.lam)}", (r.km_total, r[col]), fontsize=8,
                        color=TINTA2, xytext=(0, 10), textcoords="offset points",
                        ha="center")
        ax.set_xlabel("deslocamento total da frota (km)")
        ax.set_ylabel(rotulo)
        ax.margins(y=.18)
    axs[0].set_title("Equidade", fontsize=9.5, fontweight="bold", loc="left")
    axs[1].set_title("Eficiência", fontsize=9.5, fontweight="bold", loc="left")
    fig.suptitle("Os primeiros quilômetros compram a maior parte do ganho",
                 fontsize=10, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "sp_02_ganho_km.png"); plt.close(fig)


# ------------------------------------------------------------- 3 mapa da troca
def fig_mapa(res, st, cd):
    x0 = np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                         np.repeat(cd.id.values, cd.n_usa.values)])
    n_usb = int(cd.n_usb.sum())
    X = np.load(DADOS / "sp_pareto_x_lam1.npy")
    f = pd.read_parquet(DADOS / "sp_pareto_lam1.parquet")
    x = X[_joelho_lam(f, 1.0)]
    D = mudanca.matriz_km(cd.lat.values, cd.lon.values)

    fig, ax = plt.subplots(figsize=(6.2, 5.8))
    ax.scatter(st.lon, st.lat, s=.6, color="#d8d6d1", lw=0, zorder=1)

    from collections import Counter
    setas = 0
    for ini, fim, cor, nome in ((0, n_usb, C_USB, "USB"),
                                (n_usb, len(x), C_USA, "USA")):
        co, cn = Counter(map(int, x0[ini:fim])), Counter(map(int, x[ini:fim]))
        fica = co & cn
        o = list((co - fica).elements()); n = list((cn - fica).elements())
        if not o:
            continue
        from scipy.optimize import linear_sum_assignment
        C = D[np.ix_(o, n)].astype(float)
        ii, jj = linear_sum_assignment(C)
        for p, q in zip(ii, jj):
            a, b = o[p], n[q]
            ax.annotate("", xy=(cd.lon[b], cd.lat[b]), xytext=(cd.lon[a], cd.lat[a]),
                        arrowprops=dict(arrowstyle="-|>", color=cor, lw=1.6,
                                        shrinkA=3, shrinkB=3, alpha=.9), zorder=4)
            setas += 1
        ax.scatter(cd.lon[o], cd.lat[o], s=46, facecolor="none", edgecolor=cor,
                   lw=1.6, zorder=5, label=f"{nome}: sai de aqui")
        ax.scatter(cd.lon[n], cd.lat[n], s=46, color=cor, lw=0, zorder=5,
                   label=f"{nome}: passa a ficar aqui")

    ax.set_aspect(1 / np.cos(np.radians(-23.6)))
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    km = mudanca.custo(x, x0, D, n_usb)
    ax.set_title(f"λ = 1: as {setas} realocações que mais rendem, {km:.0f} km ao todo\n"
                 "vazado = base atual, cheio = base proposta; seta curta = "
                 "salto para a esquina",
                 fontsize=9.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.grid(alpha=.15)
    fig.tight_layout(); fig.savefig(FIG / "sp_03_mapa_troca.png"); plt.close(fig)
    return setas


# ------------------------------------------------------------------- 4 Lorenz
def _lorenz(A, pop):
    o = np.argsort(A)
    cw = np.cumsum(pop[o]) / pop.sum()
    ca = np.cumsum(A[o] * pop[o]) / (A * pop).sum()
    return np.r_[0, cw], np.r_[0, ca]


def fig_lorenz(st, cd, T):
    pop = st["pop"].values.astype(float)
    n_usb = int(cd.n_usb.sum())
    confs = {
        "atual": (np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                                  np.repeat(cd.id.values, cd.n_usa.values)]), C_ATUAL),
        "p-median clássico": (np.load(DADOS / "sp_pmedian_x.npy"), C_PM),
        "Huff + 2SFCA (λ=0,1)": (None, RAMPA[2]),
    }
    X = np.load(DADOS / "sp_pareto_x_lam0.1.npy")
    f = pd.read_parquet(DADOS / "sp_pareto_lam0.1.parquet")
    confs["Huff + 2SFCA (λ=0,1)"] = (X[_joelho_lam(f, 0.1)], RAMPA[2])

    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    ax.plot([0, 1], [0, 1], color="#b9bdc1", lw=1.2, ls="--", zorder=1)
    ax.text(.55, .60, "igualdade perfeita", color="#8b8f93", fontsize=8, rotation=38)
    for nome, (x, cor) in confs.items():
        r = H.avalia(T, pop, np.asarray(x)[:n_usb], np.asarray(x)[n_usb:])
        cw, ca = _lorenz(r["A_av"], pop)
        ax.plot(cw, ca, color=cor, lw=2.2, zorder=3,
                label=f"{nome}  (Gini {r['f_gini']:.3f})".replace(".", ","))
    ax.set_xlabel("proporção acumulada da população")
    ax.set_ylabel("proporção acumulada da acessibilidade a USA")
    ax.set_title("Quem está no pior quintil ganha o que falta",
                 fontsize=10, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.tight_layout(); fig.savefig(FIG / "sp_04_lorenz.png"); plt.close(fig)


# -------------------------------------------------------------- 5 comparacao
def fig_comparacao(comp):
    d = pd.DataFrame(comp)
    nomes = ["atual", "p-median (classico)", "Huff+2SFCA"]
    rot = ["atual", "p-median\nclássico", "Huff +\n2SFCA"]
    cores = [C_ATUAL, C_PM, RAMPA[2]]
    d = d.set_index("config").loc[nomes]

    paineis = [("huff_tempo", "tempo esperado sob Huff (min)", "{:.2f}"),
               ("huff_gini", "Gini da acessibilidade USA", "{:.3f}"),
               ("classico_t_usa", "tempo até a USA mais próxima (min)", "{:.2f}"),
               ("km_mudanca", "deslocamento da frota (km)", "{:.0f}")]
    fig, axs = plt.subplots(2, 2, figsize=(8.6, 5.6))
    for ax, (col, rotulo, fmt) in zip(axs.ravel(), paineis):
        v = d[col].values
        ax.bar(range(3), v, color=cores, width=.62)
        ax.set_xticks(range(3)); ax.set_xticklabels(rot, fontsize=8.5)
        for i, y in enumerate(v):
            ax.text(i, y + max(v) * .03, fmt.format(y).replace(".", ","),
                    ha="center", fontsize=8.5, color=TINTA, fontweight="bold")
        ax.set_ylabel(rotulo, fontsize=8.5)
        ax.set_ylim(0, max(v) * 1.22)
        ax.grid(axis="x", alpha=0)
    fig.suptitle("O ganho está na equidade, não na eficiência",
                 fontsize=10, fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "sp_05_comparacao.png"); plt.close(fig)


if __name__ == "__main__":
    res, comp, st, cd, T = carrega()
    fig_pareto(res);      print("figs/sp_01_pareto.png")
    fig_ganho(res);       print("figs/sp_02_ganho_km.png")
    n = fig_mapa(res, st, cd); print(f"figs/sp_03_mapa_troca.png ({n} setas)")
    fig_lorenz(st, cd, T); print("figs/sp_04_lorenz.png")
    fig_comparacao(comp); print("figs/sp_05_comparacao.png")
