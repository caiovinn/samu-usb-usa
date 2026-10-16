"""Huff (beta) x despacho (q): ponte, reprodutibilidade e reavaliacao barata.

    uv run python -m fase2_sao_paulo.experimentos.sensib_q

Sem otimizar nada (segundos):

  (A) reproduz a config atual sob Huff beta=4,5 contra o publicado
      (7,435 min / Gini 0,224) — a matriz de tempos pode ter sido refeita
      sobre um OSM mais novo (monta.py --so-tempos)
  (B) ponte beta <-> q: para cada beta, o N_ef mediano do Huff e o q que da o
      mesmo N_ef na geometrica; e o q que da a mesma chance mediana de o
      local mais provavel atender. Inversao de beta(N_ef) por bissecao
  (C) atual, p-median e os joelhos ja gravados (lambda 0; 0,1; 1) avaliados
      sob Huff beta=4,5 e sob despacho nos q de sp_utilizacao.json (ou numa
      grade padrao, se o SIA ainda nao foi processado)

Grava dados/fase2/sp_q_sens.json.
"""
import json

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from fase2_sao_paulo.caminhos import DADOS
from fase2_sao_paulo.experimentos import roda as R
from fase2_sao_paulo.modelo import huff2sfca as H
from fase2_sao_paulo.modelo.otimiza import joelho

PUBLICADO = {"f_tempo": 7.435, "f_gini": 0.224}
BETAS = (1.5, 2.0, 3.0, 4.5, 6.0, 8.5)
LAMBDAS = (0.0, 0.1, 1.0)
METRICAS = ("f_tempo", "f_gini", "gini_basico", "cob_usa_8", "cob_usa_8_p10",
            "cob_usa_10", "cob_usa_10_p10", "cob_usa_15", "cob_usa_15_p10",
            "pct_pop_usa_20min", "n_ef_usa")


def q_do_n_ef(n):
    """Inverte a forma fechada N_ef(q) da geometrica."""
    if n <= 1.0 + 1e-9:
        return 0.0
    return brentq(lambda q: H.n_ef_despacho(q) - n, 1e-9, 0.99)


def beta_do_n_ef(n_alvo, T, pop, x, n_usb):
    """beta(N_ef): N_ef mediano do Huff cresce com beta -> raiz unica."""
    f = lambda b: H.avalia(T, pop, x[:n_usb], x[n_usb:], beta=b)["n_ef_usa"] - n_alvo
    return brentq(f, 0.5, 30.0, xtol=1e-3)


def configuracoes(cd, n_usb):
    x0 = np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                         np.repeat(cd.id.values, cd.n_usa.values)])
    out = {"atual": x0}
    pm = DADOS / "sp_pmedian_x.npy"
    if pm.exists():
        out["p-median"] = np.load(pm)
    for lam in LAMBDAS:
        fr = DADOS / f"sp_pareto_lam{lam:g}.parquet"
        xs = DADOS / f"sp_pareto_x_lam{lam:g}.npy"
        if fr.exists() and xs.exists():
            F = pd.read_parquet(fr)
            out[f"huff lam={lam:g}"] = np.load(xs)[joelho(F[["f_obj", "f_gini"]].values)]
    return out


def grade_q():
    arq = DADOS / "sp_utilizacao.json"
    if arq.exists():
        u = json.load(open(arq))
        return {f"SIA {k}": (v["q_usb"], v["q_usa"]) for k, v in u["q"].items()}, u
    return {f"q={q:g}": (q, q) for q in (0.1, 0.27, 0.4)}, None


def main():
    st, cd, T = R.carrega()
    pop = st["pop"].values.astype(float)
    n_usb = int(cd.n_usb.sum())
    confs = configuracoes(cd, n_usb)
    x0 = confs["atual"]

    # (A)
    a = H.avalia(T, pop, x0[:n_usb], x0[n_usb:])
    print(f"(A) atual sob Huff 4,5: E[T] {a['f_tempo']:.3f} (publicado "
          f"{PUBLICADO['f_tempo']}) | Gini {a['f_gini']:.4f} ({PUBLICADO['f_gini']})")

    # (B)
    ponte = []
    for b in BETAS:
        r = H.avalia(T, pop, x0[:n_usb], x0[n_usb:], beta=b)
        ponte.append({"beta": b, "n_ef_usa": r["n_ef_usa"],
                      "q_mesmo_n_ef": q_do_n_ef(r["n_ef_usa"]),
                      "q_mesma_p_mais_prov": 1 - r["p_mais_prox_usa"],
                      "f_tempo": r["f_tempo"], "f_gini": r["f_gini"]})
    print("(B) beta -> N_ef -> q equivalente: " + "  ".join(
        f"{p['beta']:g}->{p['n_ef_usa']:.2f}->{p['q_mesmo_n_ef']:.2f}" for p in ponte))

    grade, util = grade_q()
    beta_eq = {}
    for nome, (qb, qa) in grade.items():
        try:
            beta_eq[nome] = beta_do_n_ef(float(H.n_ef_despacho(qa)), T, pop, x0, n_usb)
        except ValueError:
            beta_eq[nome] = None

    # (C)
    modelos = {"huff b=4.5": dict(modelo="huff")}
    modelos.update({f"desp {n}": dict(modelo="despacho", q_usb=qb, q_usa=qa)
                    for n, (qb, qa) in grade.items()})
    theta = util["theta_dados"] if util and util.get("theta_dados") else None
    if theta:
        n0, (qb, qa) = next((n, v) for n, v in grade.items() if "central" in n)
        modelos[f"desp {n0} theta={theta:.2f}"] = dict(modelo="despacho", q_usb=qb,
                                                       q_usa=qa, theta=theta)
    tab = []
    for mn, kw in modelos.items():
        for cn, x in confs.items():
            r = H.avalia(T, pop, x[:n_usb], x[n_usb:], **kw)
            tab.append({"modelo": mn, "config": cn,
                        **{m: float(r[m]) for m in METRICAS}})
    df = pd.DataFrame(tab)

    json.dump({"reproducao": {"f_tempo": a["f_tempo"], "f_gini": a["f_gini"],
                              "publicado": PUBLICADO},
               "ponte": ponte, "beta_equivalente": beta_eq,
               "tabela": tab}, open(DADOS / "sp_q_sens.json", "w"), indent=2)
    with pd.option_context("display.width", 200, "display.precision", 3):
        print(df.pivot(index="config", columns="modelo", values="f_gini").to_string())
        print(df.pivot(index="config", columns="modelo", values="cob_usa_8_p10").round(1).to_string())
    print("-> dados/fase2/sp_q_sens.json")


if __name__ == "__main__":
    main()
