"""Figuras da fase 4 (dados lidos dos JSON; nenhum numero digitado)."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402
import pandas as pd              # noqa: E402

from ..caminhos import DADOS, FIG  # noqa: E402

C_F3, C_HC = "#7a7a7a", "#d95f02"      # modelo da fase 3 (cinza), hipercubo (laranja)


def fig_validacao():
    d = pd.DataFrame(json.load(open(DADOS / "v_real_vs_sim.json", encoding="utf-8"))["linhas"])
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
    a = ax[0]
    lo, hi = d.sim_vidas.min() - 2, d.sim_vidas.max() + 2
    a.plot([lo, hi], [lo, hi], color="k", lw=0.8)
    a.scatter(d.sim_vidas, d.fase3_vidas, s=22, color=C_F3, label="modelo da fase 3 (ocupação igual)")
    a.scatter(d.sim_vidas, d.larson75_vidas, s=22, color=C_HC, label="hipercubo (ocupação endógena)")
    a.set_xlabel("vidas por 1.000 PCR, simulação")
    a.set_ylabel("vidas por 1.000 PCR, modelo")
    a.set_title("Modelo contra simulação (39 casos)")
    a.legend(frameon=False, loc="upper left")
    b = ax[1]
    e3 = (d.fase3_vidas - d.sim_vidas)
    eh = (d.larson75_vidas - d.sim_vidas)
    b.hist(e3, bins=np.linspace(-4, 4, 33), color=C_F3, alpha=0.8, label="fase 3")
    b.hist(eh, bins=np.linspace(-4, 4, 33), color=C_HC, alpha=0.8, label="hipercubo")
    b.axvline(0, color="k", lw=0.8)
    b.set_xlabel("erro do modelo (modelo − simulação), vidas por 1.000 PCR")
    b.set_ylabel("número de casos")
    b.set_title("O hipercubo corrige o viés otimista do modelo da fase 3")
    b.legend(frameon=False)
    fig.savefig(FIG / "h01_validacao.png", dpi=150)


def fig_busca():
    r = json.load(open(DADOS / "h_resumo.json", encoding="utf-8"))["pares"]
    nomes = [k for k in r if k.startswith("hc")]
    fig, a = plt.subplots(figsize=(8.5, 4.2), constrained_layout=True)
    x = np.arange(len(nomes))
    ganho = [r[k]["dif_pareada_media"] for k in nomes]
    lo = [r[k]["dif_pareada_media"] - r[k]["dif_min"] for k in nomes]
    hi = [r[k]["dif_max"] - r[k]["dif_pareada_media"] for k in nomes]
    a.bar(x, ganho, color=[C_HC if g >= 0 else "#555" for g in ganho], yerr=[lo, hi], capsize=3)
    a.axhline(0, color="k", lw=0.8)
    a.set_xticks(x, [k[3:] for k in nomes])
    a.set_ylabel("vidas por 1.000 PCR, hipercubo − fase 3\n(simulação, mesmos chamados)")
    a.set_title("Busca com hipercubo contra fase 3, na simulação\n"
                "(barras: faixa das 3 sementes da simulação; não inclui a variação da busca)", fontsize=10)
    fig.savefig(FIG / "h02_busca.png", dpi=150)


if __name__ == "__main__":
    fig_validacao()
    fig_busca()
    print("figuras em", FIG)
