"""Figuras da fase 3. Gera figs/fase3/v0*.png a partir de dados/fase3/*.json.

    uv run python -m fase3_vidas.experimentos.figuras

Cores (validadas com o validador de paleta do skill de dataviz):
  rampa azul ordinal = limite K de unidades movidas (grandeza ordenada);
  laranja = p-median classico e cinza = rede de hoje (mesmas cores da fase 2);
  agua = solucoes da equidade por Gini (fases 2 e 2b) — abaixo de 3:1 de
  contraste, por isso sempre com rotulo direto.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
import numpy as np                                   # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from fase3_vidas.caminhos import DADOS, FIG          # noqa: E402

plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 130,
                     "font.size": 9, "axes.grid": True, "grid.alpha": .25,
                     "axes.spines.top": False, "axes.spines.right": False})

RAMPA_K = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]   # K: 10..livre
C_PM, C_HOJE, C_GINI = "#eb6834", "#52514e", "#1baf7a"
TINTA, TINTA2 = "#0b0b0b", "#52514e"
SEQ = LinearSegmentedColormap.from_list(
    "azul", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])


def le(nome):
    return json.load(open(DADOS / nome, encoding="utf-8"))


def bonito(k):
    """Nome legivel de uma configuracao (o mesmo do relatorio)."""
    k = k.replace("fase2b central_r25", "fase 2b c/ restrição").replace("fase2b central", "fase 2b")
    k = k.replace("fase2 ", "fase 2 ").replace("lam=", "λ=").replace("vidas ", "vidas: ")
    return k.replace("K=livre", "sem limite").replace(" G=pm", " · piso p-median")


def _rot_k(K):
    return "livre" if K is None else str(K)


def fronteira():
    b = le("v3_busca.json")
    re = le("v2_reavaliacao.json")["configs"]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    for cor, K in zip(RAMPA_K, b["Ks"]):
        pts = sorted([v for v in b["solucoes"].values() if v["K"] == K and v["guarda"] == "hoje"],
                     key=lambda v: v["lam"])
        x = [p["exato"]["cvar10"] for p in pts]
        y = [p["exato"]["vidas"] for p in pts]
        ax.plot(x, y, "-", color=cor, lw=2, zorder=2)
        ax.scatter(x, y, s=40, color=cor, edgecolor="#fcfcfb", lw=1.5, zorder=3,
                   label=f"K = {_rot_k(K)}")
        if K is not None:
            ax.annotate(f"K={_rot_k(K)}", (x[0], y[0]), xytext=(6, 2), textcoords="offset points",
                        fontsize=8, color=TINTA2)
    # piso do chamado grave no nivel do p-median (so sem limite K)
    for k, v in b["solucoes"].items():
        if v["guarda"] != "pm":
            continue
        e = v["exato"]
        ax.scatter(e["cvar10"], e["vidas"], s=60, marker="s", facecolor="#fcfcfb",
                   edgecolor=RAMPA_K[-1], lw=1.8, zorder=5)
        dx, dy = (-8, 10) if v["lam"] == 0 else (-6, -16)
        ax.annotate(f"λ={v['lam']:g}, piso p-median", (e["cvar10"], e["vidas"]),
                    xytext=(dx, dy), textcoords="offset points", fontsize=7.5, color=TINTA2,
                    ha="left" if v["lam"] == 0 else "right")
    for nome, v in re.items():
        if nome == "hoje":
            cor, txt = C_HOJE, "hoje"
        elif nome == "p-median":
            cor, txt = C_PM, "p-median"
        elif v["movidas"] > 60:                     # so os redesenhos da equidade por Gini
            cor, txt = C_GINI, ""
        else:
            continue
        ax.scatter(v["cvar10"], v["vidas"], s=48, marker="D", color=cor,
                   edgecolor="#fcfcfb", lw=1.5, zorder=4)
        if txt:
            dx, dy, ha = (-8, 6, "right") if nome == "p-median" else (9, -3, "left")
            ax.annotate(txt, (v["cvar10"], v["vidas"]), xytext=(dx, dy), textcoords="offset points",
                        fontsize=7.5, color=TINTA2, ha=ha)
    gini = [v for k, v in re.items() if k.startswith("fase2") and v["movidas"] > 60]
    g = min(gini, key=lambda v: v["cvar10"])
    ax.annotate("mapas da equidade por Gini\n(fases 2 e 2b)", (g["cvar10"], g["vidas"]),
                xytext=(-10, -26), textcoords="offset points", fontsize=7.5, color=TINTA2, ha="center")
    ax.set_xlabel("sobreviventes por 1.000 PCR nos 10% piores (CVaR10)", color=TINTA2)
    ax.set_ylabel("sobreviventes por 1.000 PCR (cidade)", color=TINTA2)
    ax.set_title("Vidas × equidade: cada linha é um limite K de unidades movidas; "
                 "pontos = peso λ do CVaR", loc="left", fontsize=9.5, color=TINTA)
    ax.text(0.99, 0.02, "K livre = sem limite de unidades movidas", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=7.5, color=TINTA2)
    ax.legend(frameon=False, fontsize=8, loc="lower right", ncols=1, bbox_to_anchor=(1, 0.06))
    fig.tight_layout()
    fig.savefig(FIG / "v01_fronteira.png")
    plt.close(fig)


def robustez():
    r = le("v6_robustez.json")
    pc = sorted(r["por_config"], key=lambda d: d["arrep_max"], reverse=True)
    fig, ax = plt.subplots(figsize=(7.6, 0.42 * len(pc) + 1.0))
    y = np.arange(len(pc))
    v = [d["arrep_max"] for d in pc]
    ax.barh(y, v, height=0.55, color="#2a78d6")
    for yi, vi, d in zip(y, v, pc):
        ax.text(vi, yi, f"  {vi:.1f} ({100*d['arrep_rel_max']:.0f}%)", va="center",
                fontsize=8, color=TINTA)
    ax.set_yticks(y)
    ax.set_yticklabels([bonito(d["config"]) for d in pc], fontsize=8)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("pior perda contra o melhor mapa do cenário (sobreviventes por 1.000 PCR)",
                  color=TINTA2)
    ax.set_title(f"Arrependimento máximo em {len(r['cenarios'])} cenários\n"
                 "(tempo por saída × trânsito × carga)", loc="left", fontsize=9.5, color=TINTA)
    ax.set_xlim(0, max(v) * 1.25 + 0.5)
    fig.tight_layout()
    fig.savefig(FIG / "v02_robustez.png")
    plt.close(fig)


def mapa():
    import pandas as pd
    from fase3_vidas.caminhos import DADOS_FASE2
    from fase3_vidas.experimentos import vidas as VI
    from fase3_vidas.modelo import sobrevida as SV
    st = pd.read_parquet(DADOS_FASE2 / "sp_setores.parquet")
    cd = pd.read_parquet(DADOS_FASE2 / "sp_candidatos.parquet")
    escolha = le("v6_robustez.json")["minimax_arrependimento"]
    fin = VI.finalistas()
    f, a = VI.fator()
    D = VI.dados()
    qb, qa = VI.qs()
    painel = [("hoje", fin["hoje"]), (escolha, fin[escolha])]
    Ss = []
    for _, (yB, yA) in painel:
        iB, iA = VI.indices(yB, yA)
        Ss.append(1000 * SV.avalia_vidas(D["T"], D["pop"], iB, iA, qb, qa, fator=f,
                                         atraso=a, detalhe=True)["S"])
    vmax = np.percentile(np.concatenate(Ss), 99)
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 5.0), sharex=True, sharey=True)
    for ax, (nome, (yB, yA)), S in zip(axs, painel, Ss):
        sc = ax.scatter(st.lon, st.lat, c=S, s=1.2, cmap=SEQ, vmin=0, vmax=vmax, linewidths=0)
        for y, mk, cor, rot in ((yB, "o", TINTA, "USB"), (yA, "^", C_PM, "USA")):
            j = np.nonzero(y)[0]
            ax.scatter(cd.lon.values[j], cd.lat.values[j], s=10 + 8 * y[j], marker=mk,
                       facecolor="none" if mk == "o" else cor, edgecolor=cor, lw=0.9, label=rot)
        ax.set_title(bonito(nome), loc="left", fontsize=9.5, color=TINTA)
        ax.set_aspect(1 / np.cos(np.radians(st.lat.mean())))
        ax.grid(False)
        ax.set_xticks([]); ax.set_yticks([])
        for e in ("left", "bottom"):
            ax.spines[e].set_visible(False)
    axs[0].legend(frameon=False, fontsize=8, loc="lower left")
    cb = fig.colorbar(sc, ax=axs, shrink=0.7, pad=0.02)
    cb.set_label("sobreviventes por 1.000 PCR no setor", color=TINTA2)
    fig.suptitle("Sobrevida a PCR por setor: rede de hoje × mapa escolhido", x=0.02, ha="left",
                 fontsize=10, color=TINTA)
    fig.savefig(FIG / "v03_mapa.png", bbox_inches="tight")
    plt.close(fig)


def mapa4():
    """Quatro mapas para deck_evolucao.js: hoje, Huff + 2SFCA (Gini) e despacho +
    vidas com lambda 0 e 1. Mesmo estilo de mapa(). Grava v05_mapa4.png e
    v05_mapa4.json (vidas, CVaR10 e locais de cada painel, conferidos contra
    deck_evolucao.json)."""
    import pandas as pd
    from fase3_vidas.caminhos import DADOS_FASE2
    from fase3_vidas.experimentos import vidas as VI
    from fase3_vidas.modelo import sobrevida as SV
    st = pd.read_parquet(DADOS_FASE2 / "sp_setores.parquet")
    cd = pd.read_parquet(DADOS_FASE2 / "sp_candidatos.parquet")
    ev = le("deck_evolucao.json")["mapas"]
    f, a = VI.fator()
    D = VI.dados()
    qb, qa = VI.qs()
    painel = [("hoje", "v2_y_hoje", "Rede de hoje"),
              ("fase2 lam=0.1", "v2_y_fase2_lam0.1", "Huff + 2SFCA (Gini)"),
              ("vidas lam=0 K=livre G=pm", "v3_y_lam0_Klivre_Gpm", "despacho + vidas, λ = 0"),
              ("vidas lam=1 K=livre G=pm", "v3_y_lam1_Klivre_Gpm", "despacho + vidas, λ = 1")]
    ys, Ss, res = [], [], {}
    for chave, arq, rot in painel:
        yB, yA = np.load(DADOS / f"{arq}.npy")
        iB, iA = VI.indices(yB, yA)
        r = SV.avalia_vidas(D["T"], D["pop"], iB, iA, qb, qa, fator=f, atraso=a, detalhe=True)
        assert abs(r["vidas"] - ev[chave]["vidas"]) < 1e-6, (chave, r["vidas"], ev[chave]["vidas"])
        ys.append((yB, yA))
        Ss.append(1000 * r["S"])
        res[chave] = {"rotulo": rot, "vidas": r["vidas"], "cvar10": r["cvar10"],
                      "locais": int(((yB + yA) > 0).sum()),
                      "locais_usa": int((yA > 0).sum())}
    vmax = np.percentile(np.concatenate(Ss), 99)
    fig, axs = plt.subplots(1, 4, figsize=(13.0, 4.7), sharex=True, sharey=True,
                            gridspec_kw={"wspace": 0.08})
    for ax, (chave, _, rot), (yB, yA), S in zip(axs, painel, ys, Ss):
        sc = ax.scatter(st.lon, st.lat, c=S, s=0.8, cmap=SEQ, vmin=0, vmax=vmax, linewidths=0)
        for y, mk, cor, nome in ((yB, "o", TINTA, "USB"), (yA, "^", C_PM, "USA")):
            j = np.nonzero(y)[0]
            ax.scatter(cd.lon.values[j], cd.lat.values[j], s=8 + 7 * y[j], marker=mk,
                       facecolor="none" if mk == "o" else cor, edgecolor=cor, lw=0.8, label=nome)
        v = res[chave]
        ax.set_title(rot, loc="left", fontsize=10.5, color=TINTA, fontweight="bold", pad=18)
        ax.text(0, 1.015, f"vidas {v['vidas']:.1f} · 10% piores {v['cvar10']:.1f}".replace(".", ","),
                transform=ax.transAxes, fontsize=9.5, color=TINTA2, va="bottom")
        ax.set_aspect(1 / np.cos(np.radians(st.lat.mean())))
        ax.grid(False)
        ax.set_xticks([]); ax.set_yticks([])
        for e in ("left", "bottom"):
            ax.spines[e].set_visible(False)
    axs[0].legend(frameon=False, fontsize=9, loc="lower left")
    cb = fig.colorbar(sc, ax=axs, shrink=0.75, pad=0.01)
    cb.set_label("sobreviventes por 1.000 PCR no setor", color=TINTA2)
    fig.savefig(FIG / "v05_mapa4.png", bbox_inches="tight", dpi=220)
    plt.close(fig)
    (DADOS / "v05_mapa4.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def validacao():
    s = le("v5_simulacao.json")
    med = [m for m in s["medias"] if m["servico"] == "central"]
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    x = [m["an_vidas_mean"] for m in med]
    y = [m["sim_vidas_mean"] for m in med]
    lo = [m["sim_vidas_mean"] - m["sim_vidas_min"] for m in med]
    hi = [m["sim_vidas_max"] - m["sim_vidas_mean"] for m in med]
    a, b = min(x + y) - 2, max(x + y) + 2
    ax.plot([a, b], [a, b], "-", color="#c3c2b7", lw=1, zorder=1)
    ax.errorbar(x, y, yerr=[lo, hi], fmt="o", color="#2a78d6", ms=6, mec="#fcfcfb",
                mew=1.5, elinewidth=1, capsize=0, zorder=3)
    for m in med:
        if m["config"] in ("hoje", "p-median"):
            ax.annotate(m["config"], (m["an_vidas_mean"], m["sim_vidas_mean"]),
                        xytext=(6, -10), textcoords="offset points", fontsize=8, color=TINTA2)
    ax.set_xlabel("previsto pelo modelo (por 1.000 PCR)", color=TINTA2)
    ax.set_ylabel("simulado (por 1.000 PCR)", color=TINTA2)
    ax.set_title("Modelo × simulação, tempo de serviço central\n"
                 "(barra = faixa de 3 sementes; na diagonal o modelo acerta)",
                 loc="left", fontsize=9.5, color=TINTA)
    fig.tight_layout()
    fig.savefig(FIG / "v04_validacao.png")
    plt.close(fig)


def main():
    import sys
    # sem argumentos: as figuras de sempre; com nomes: so essas (ex.: mapa4)
    fns = [globals()[a] for a in sys.argv[1:]] or [fronteira, robustez, mapa, validacao]
    for fn in fns:
        fn()
        print(f"ok {fn.__name__}")


if __name__ == "__main__":
    main()
