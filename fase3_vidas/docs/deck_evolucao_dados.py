"""Avaliacao cruzada para a apresentacao "evolucao do metodo".

    uv run python -m fase3_vidas.docs.deck_evolucao_dados

Cada mapa (rede de hoje, p-median, fases 2, 2b e 3) e medido pelas duas
reguas: a da fase 2 (tempo esperado e Gini da acessibilidade, Huff com
beta = 4,5 em transito livre, exatamente como publicado) e a do despacho
(fase 2b), alem das metricas da fase 3 (vidas, CVaR10, cobertura grave),
que sao lidas dos JSONs v2/v3 e nao recalculadas. A fase 3 nunca mediu o
Gini dos proprios mapas; e so isso que este script acrescenta.

Le os mapas gravados em dados/fase3/v2_y_*.npy e v3_y_*.npy; grava
dados/fase3/deck_evolucao.json (derivado, regeneravel). Confere que a rede
de hoje reproduz o numero publicado da fase 2 (7,435 min; Gini 0,224).
"""
import json

import numpy as np

from fase2_sao_paulo.modelo import huff2sfca as H
from fase3_vidas.caminhos import DADOS
from fase3_vidas.experimentos import vidas as VI

# nome no deck -> (arquivo do mapa, origem das metricas da fase 3)
MAPAS = {
    "hoje": ("v2_y_hoje", ("v2", "hoje")),
    "p-median": ("v2_y_p-median", ("v2", "p-median")),
    "fase2 lam=0.1": ("v2_y_fase2_lam0.1", ("v2", "fase2 lam=0.1")),
    "fase2 lam=1": ("v2_y_fase2_lam1", ("v2", "fase2 lam=1")),
    "fase2b central lam=0.1": ("v2_y_fase2b_central_lam0.1", ("v2", "fase2b central lam=0.1")),
    "fase2b central lam=1": ("v2_y_fase2b_central_lam1", ("v2", "fase2b central lam=1")),
    "vidas lam=0 K=20": ("v3_y_lam0_K20", ("v3", "lam=0 K=20")),
    "vidas lam=0 K=40": ("v3_y_lam0_K40", ("v3", "lam=0 K=40")),
    "vidas lam=0 K=livre G=pm": ("v3_y_lam0_Klivre_Gpm", ("v3", "lam=0 K=livre G=pm")),
    "vidas lam=1 K=livre G=pm": ("v3_y_lam1_Klivre_Gpm", ("v3", "lam=1 K=livre G=pm")),
}
REF_HOJE = (7.435, 0.2242)        # fase 2 publicada (CONTEXTO_PROJETO.md, secao 5.1)


def main():
    D = VI.dados()
    qb, qa = VI.qs()
    th = D["U"]["theta_dados"]
    v2 = json.load(open(DADOS / "v2_reavaliacao.json", encoding="utf-8"))["configs"]
    v3 = json.load(open(DADOS / "v3_busca.json", encoding="utf-8"))["solucoes"]
    out = {}
    pmB, pmA = np.load(DADOS / f"{MAPAS['p-median'][0]}.npy")
    for nome, (arq, (fonte, chave)) in MAPAS.items():
        yB, yA = np.load(DADOS / f"{arq}.npy")
        iB, iA = VI.indices(yB, yA)
        hu = H.avalia(D["T"], D["pop"], iB, iA, modelo="huff")
        de = H.avalia(D["T"], D["pop"], iB, iA, modelo="despacho", q_usb=qb, q_usa=qa, theta=th)
        if fonte == "v2":
            r = v2[chave]
            novo = {k: r[k] for k in ("vidas", "cvar10", "cob_grave", "cob_basico")}
            mv, km = r["movidas"], r["km"]
            # o Gini do despacho ja estava no v2: tem de bater
            assert abs(r["gini_usa"] - de["f_gini"]) < 1e-6, (nome, r["gini_usa"], de["f_gini"])
        else:
            r = v3[chave]
            novo = {k: r["exato"][k] for k in ("vidas", "cvar10", "cob_grave", "cob_basico")}
            mv, km = r["movidas"], r["km"]
        out[nome] = dict(
            huff_tempo=float(hu["f_tempo"]), huff_gini=float(hu["f_gini"]),
            desp_tempo=float(de["f_tempo"]), desp_gini=float(de["f_gini"]),
            desp_p10_usa10=float(de["cob_usa_10_p10"]), desp_p10_usa15=float(de["cob_usa_15_p10"]),
            movidas=int(mv), km=float(km),
            # unidades em local diferente do p-median (cada troca conta uma vez)
            dif_pm_usb=int(np.abs(yB - pmB).sum() // 2), dif_pm_usa=int(np.abs(yA - pmA).sum() // 2),
            **novo)
        print(f"{nome:26s} Huff {hu['f_tempo']:.3f} min  Gini {hu['f_gini']:.3f} | "
              f"desp Gini {de['f_gini']:.3f}  p10<=10 {de['cob_usa_10_p10']:5.1f}% | "
              f"vidas {novo['vidas']:5.1f}  CVaR10 {novo['cvar10']:5.1f}  movidas {mv}")

    h = out["hoje"]
    assert abs(h["huff_tempo"] - REF_HOJE[0]) < 5e-4 and abs(h["huff_gini"] - REF_HOJE[1]) < 5e-4, \
        f"rede de hoje nao reproduz a fase 2: {h['huff_tempo']:.4f} / {h['huff_gini']:.4f}"
    destino = DADOS / "deck_evolucao.json"
    destino.write_text(json.dumps({"beta": H.BETA, "theta_huff": H.THETA, "theta_desp": th,
                                   "q_usb": qb, "q_usa": qa, "mapas": out},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {destino}")


if __name__ == "__main__":
    main()
