"""Renderiza as formulas em destaque do deck didatico como imagens PNG.

deck_didatico.js usava caixas de texto em fonte monoespacada (S_j, t^2)
para as formulas. Isto troca isso por tipografia matematica de verdade —
fracao empilhada, sub/sobrescrito real, letra grega — via mathtext do
matplotlib (ja e dependencia do projeto; nao precisa de instalacao de LaTeX).

    uv run python -m fase2_sao_paulo.docs.formulas_gera

Grava em figs/fase2/formulas/<chave>.png, fundo transparente, recortado
exatamente no texto (sem sobra de margem) para o addImage do pptxgenjs
posicionar sem precisar descontar padding invisivel.

mathtext tem um subconjunto de comandos LaTeX menor que uma instalacao
completa — restrito aqui a \\frac, _{}, ^{}, letras gregas, \\sum, \\min,
\\mid, \\cdot, \\times, \\qquad e e^{...} no lugar de \\exp(...), que nao e
macro garantido no mathtext. Cada formula e conferida visualmente (tamanho
de arquivo plausivel, sem excecao) antes de entrar no deck.
"""
import matplotlib
matplotlib.use("Agg")
# fontset "cm" (Computer Modern, o padrao do LaTeX) em vez do default
# "dejavusans": testado e confirmado que o dejavusans nao tem glifo italico
# proprio para "j" no mathtext -- ele cai para o MESMO glifo de "i" (digitar
# "ij" produzia "ii" na tela). Como i (setor) e j (base) sao os dois indices
# mais usados neste projeto inteiro, essa ambiguidade e inaceitavel. O "cm"
# distingue os dois com clareza (o "j" tem gancho descendente visivel).
matplotlib.rcParams["mathtext.fontset"] = "cm"
import matplotlib.pyplot as plt

from fase2_sao_paulo.caminhos import FIG as FIG_BASE

FIG = FIG_BASE / "formulas"
FIG.mkdir(parents=True, exist_ok=True)

INK = "#0F2B46"       # mesma cor das caixas de formula no deck (constante INK)
FONTSIZE = 26

FORMULAS = {
    "huff_principal": r"$P(j \mid i) \;=\; \dfrac{S_j^{\alpha}\, f(t_{ij})}"
                      r"{\sum_k S_k^{\alpha}\, f(t_{ik})}$",
    "huff_decaimento": r"$f(t) \;=\; e^{-t^2/2\beta^2}$",
    "beta_subst": r"$2\beta^2 \;=\; 2 \times 4{,}5^2 \;=\; 40{,}5$",
    # exponencial da entropia, como huff2sfca.n_efetivo calcula. A versao
    # anterior (1/soma P^2, inverso de Simpson) dava outro numero: 1,87 e nao
    # 2,2 unidades no dado real com beta=4,5 — o slide mostrava uma formula e
    # imprimia o resultado da outra
    "n_ef": r"$N^{\mathrm{ef}}_i \;=\; e^{H_i}, \qquad "
            r"H_i \;=\; -\sum_j P(j \mid i)\,\ln P(j \mid i)$",
    "sfca_pressao": r"$\mathrm{press\~{a}o}_j \;=\; \sum_i D_i \, P(j \mid i)$",
    "sfca_razao": r"$R_j \;=\; \dfrac{S_j}{\mathrm{press\~{a}o}_j}$",
    "sfca_acessibilidade": r"$A_i \;=\; \sum_j P(j \mid i)\, R_j$",
    "lorenz_xy": r"$X_k \;=\; \dfrac{\sum_{\kappa \leq k} \mathrm{pop}_\kappa}"
                 r"{\sum \mathrm{pop}} \qquad "
                 r"Y_k \;=\; \dfrac{\sum_{\kappa \leq k} \mathrm{pop}_\kappa A_\kappa}"
                 r"{\sum \mathrm{pop}\, A}$",
    "lorenz_gini": r"$\mathrm{Gini} \;=\; 1 - \sum_k (X_k - X_{k-1})(Y_k + Y_{k-1})$",
    "pmedian_obj": r"$\min \;\; \dfrac{1}{N}\sum_i D_i \min_j t_{ij}$",
    "lambda_obj": r"$f_1^{\lambda}(x) \;=\; \mathbb{E}[T](x) \;+\; \lambda\,\dfrac{K(x)}{N}$",
    # --- fase 2b (deck_despacho.js): modelo despacho, ocupacao, cobertura
    # mathtext nao tem \underbrace nem \Big: os termos sao explicados no slide
    "desp_geom": r"$P(k) \;=\; q^{\,k-1} \cdot (1-q)$",
    "desp_local": r"$P(j \mid i) \;=\; \left(\prod_{l\,:\;t_{il} < t_{ij}} q^{S_l}\right)"
                  r"\left(1 - q^{S_j}\right)$",
    "q_def": r"$q \;=\; \dfrac{r \,\cdot\, \bar{s}}{N}$",
    "et_def": r"$\mathbb{E}[T_i] \;=\; \sum_j P(j \mid i)\; t_{ij}$",
    "cob_def": r"$C_i(\tau) \;=\; \sum_j P(j \mid i)\; \mathbf{1}[\,t_{ij} \leq \tau\,]$",
    "rho_g": r"$\rho_G(\beta,\lambda) \;=\; \dfrac{G_{\mathrm{atual}}(\beta) - G_{\lambda}(\beta)}"
             r"{G_{\mathrm{atual}}(\beta) - G_{0}(\beta)}$",
}


def renderiza(chave, latex, fontsize=FONTSIZE, cor=INK):
    """Desenha o texto e deixa o savefig(bbox_inches='tight') recortar.

    Uma primeira versao mediu a caixa do texto com get_window_extent() e
    redimensionou a figura na mao — e cortava fracoes (\\dfrac) na base,
    porque o ancoramento do texto em y=0 nao contava com o denominador
    descendo ABAIXO do ponto de ancoragem. bbox_inches="tight" resolve isso
    corretamente (mede tudo o que foi de fato desenhado, inclusive
    descendentes), e e mais simples.
    """
    fig = plt.figure(figsize=(0.1, 0.1))
    fig.text(0.5, 0.5, latex, fontsize=fontsize, color=cor,
              ha="center", va="center")
    destino = FIG / f"{chave}.png"
    fig.savefig(destino, dpi=200, transparent=True, bbox_inches="tight",
                pad_inches=0.04)
    plt.close(fig)
    from PIL import Image
    with Image.open(destino) as im:
        largura, altura = im.size
    tam = destino.stat().st_size
    print(f"  {chave:<24} {largura}x{altura}px  ({tam/1024:.0f} KB)"
          + ("  !! ARQUIVO SUSPEITO, MUITO PEQUENO" if tam < 800 else ""))


if __name__ == "__main__":
    print(f"gerando {len(FORMULAS)} formulas em {FIG}/ ...")
    for chave, latex in FORMULAS.items():
        renderiza(chave, latex)
    print("ok — confira as proporcoes acima e abra 1-2 PNGs para inspecionar.")
