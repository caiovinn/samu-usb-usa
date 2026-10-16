"""Renderiza as formulas da apresentacao da fase 3 como imagens PNG.

    uv run python -m fase3_vidas.docs.formulas_gera

Mesmo metodo de fase2_sao_paulo/docs/formulas_gera.py (mathtext do
matplotlib, fonte Computer Modern para distinguir i de j, fundo transparente,
recorte justo). Grava em figs/fase3/formulas/<chave>.png e as dimensoes em
dims.json, que o deck_vidas.js le para nao distorcer as imagens. As formulas
de Huff e do despacho sao as da fase 2 e nao sao repetidas aqui.
"""
import json

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["mathtext.fontset"] = "cm"
import matplotlib.pyplot as plt
from PIL import Image

from fase3_vidas.caminhos import FIG as FIG_BASE

FIG = FIG_BASE / "formulas"
FIG.mkdir(parents=True, exist_ok=True)
INK = "#0F2B46"       # constante INK do deck
FONTSIZE = 26

FORMULAS = {
    "t_calib": r"$t'_{ij} \;=\; \mathrm{atraso} \,+\, f \cdot t_{ij}$",
    "sobrev": r"$s(t) \;=\; \dfrac{1}{1 + e^{\,0{,}679 \,+\, 0{,}262\, t}}$",
    "s_setor": r"$S_i \;=\; \sum_j p_{ij}\; s(t'_{ij})$",
    "vidas": r"$\mathrm{vidas} \;=\; 1.000 \sum_i w_i\, S_i$",
    "cvar": r"$\mathrm{CVaR}_{10} \;=\; 1.000 \cdot \dfrac{1}{0{,}10} \sum_i \omega_i\, S_i$",
    "cob": r"$\mathrm{cob} \;=\; \sum_i w_i\, \left(1 - q^{\,n_i}\right)$",
    "objetivo": r"$\max_{y}\;\; \mathrm{vidas}(y) \;+\; \lambda \cdot \mathrm{CVaR}_{10}(y)$",
    # deck_evolucao.js: tempo medio, cobertura e sobrevida como a mesma media
    "g_geral": r"$\mathbb{E}\left[\,g(T_i)\,\right] \;=\; \sum_j P(j \mid i)\; g(t_{ij})$",
}


def renderiza(chave, latex, fontsize=FONTSIZE, cor=INK):
    fig = plt.figure(figsize=(0.1, 0.1))
    fig.text(0.5, 0.5, latex, fontsize=fontsize, color=cor, ha="center", va="center")
    destino = FIG / f"{chave}.png"
    fig.savefig(destino, dpi=200, transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    with Image.open(destino) as im:
        return list(im.size)


if __name__ == "__main__":
    dims = {k: renderiza(k, v) for k, v in FORMULAS.items()}
    (FIG / "dims.json").write_text(json.dumps(dims, indent=1), encoding="utf-8")
    for k, (w, h) in dims.items():
        print(f"  {k:<10} {w}x{h}px")
