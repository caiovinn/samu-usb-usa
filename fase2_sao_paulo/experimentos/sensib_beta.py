"""Sensibilidade em beta — prioridade 1 do CONTEXTO_PROJETO.md §7.

Responde duas perguntas, em dois custos bem diferentes:

  (A) barata (segundos, sem otimizar): como a config ATUAL, sem mudar nada,
      e lida sob decaimentos diferentes? E a tabela que matematica_usb_usa.html
      §3.2 ja assume (N_ef, E[T] mediana, Gini) — aqui ela e de fato calculada,
      nao so citada.

  (B) cara (ate ~14 min por beta novo, com ORCAMENTO=420s x 3 lambda): o
      achado "12 unidades e 39 km cortam a maior parte da desigualdade"
      sobrevive fora de beta=4,5? Re-roda o experimento completo (NSGA-II)
      em lambda in {0, 0.1, 1} para cada beta novo, e mede o ganho relativo
      (rho_G, rho_T) de matematica_usb_usa.html (10.1) — a UNICA comparacao
      valida entre beta diferentes, porque a linha de base tambem muda com
      beta (ver a mesma secao).

    python -m fase2_sao_paulo.experimentos.sensib_beta               # betas padrao: 2, 4.5, 8.5
    python -m fase2_sao_paulo.experimentos.sensib_beta 2 6 8.5        # outra lista de beta

Grava dados/fase2/sp_beta_sens.json. beta=huff2sfca.BETA (o padrao) aproveita
o resultado ja gravado em dados/fase2/sp_resultado.json em vez de re-otimizar.
"""
import json
import sys

import numpy as np

from fase2_sao_paulo.caminhos import DADOS
from fase2_sao_paulo.modelo import huff2sfca as H
from fase2_sao_paulo.experimentos import roda as R

BETAS_TABELA = (1.5, 4.5, 8.5, 12.0)     # (A) — so avalia(), nao otimiza
BETAS_SWEEP = (2.0, 4.5, 8.5)            # (B) — reotimiza (4.5 e reaproveitado)
LAMBDAS_SWEEP = (0.0, 0.1, 1.0)


def tabela_barata(betas=BETAS_TABELA):
    """(A): config atual sob cada beta, sem reotimizar. Poucos segundos."""
    st, cd, T = R.carrega()
    pop = st["pop"].values.astype(float)
    x0 = np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                         np.repeat(cd.id.values, cd.n_usa.values)])
    n_usb = int(cd.n_usb.sum())
    linhas = []
    for beta in betas:
        r = H.avalia(T, pop, x0[:n_usb], x0[n_usb:], beta=beta)
        linhas.append({
            "beta": beta, "n_ef_usa_mediana": float(r["n_ef_usa"]),
            "f_tempo": r["f_tempo"], "f_gini": r["f_gini"],
        })
        print(f"  beta={beta:>4g}  N_ef~{r['n_ef_usa']:.1f}  "
              f"E[T]={r['f_tempo']:.2f} min  Gini={r['f_gini']:.4f}", flush=True)
    return linhas


def _carrega_resultado(beta):
    suf = R._sufixo(beta)
    arq = DADOS / f"sp_resultado{suf}.json"
    if arq.exists():
        d = json.load(open(arq))
        if d.get("beta") == beta:
            return d
    return None


def sweep_completo(betas=BETAS_SWEEP, lambdas=LAMBDAS_SWEEP):
    """(B): repete a varredura de lambda (NSGA-II) para cada beta novo.

    beta == huff2sfca.BETA usa o dados/sp_resultado.json ja existente (o run
    base) em vez de reotimizar — e o mesmo experimento, so mudaria o
    checkpoint de RNG por reentrada.
    """
    resultados = {}
    for beta in betas:
        d = _carrega_resultado(beta)
        tem_tudo = d and all(f"{l:g}" in d.get("por_lambda", {}) for l in lambdas)
        if tem_tudo:
            print(f"\n== beta={beta:g}: reaproveitando {('sp_resultado' + R._sufixo(beta))}.json ==",
                  flush=True)
        else:
            print(f"\n== beta={beta:g}: rodando lambda in {lambdas} ==", flush=True)
            R.main(lambdas, beta)
            d = _carrega_resultado(beta)
        resultados[beta] = d
    return resultados


def indicadores(resultados, lambdas=LAMBDAS_SWEEP):
    """rho_G, rho_T de matematica_usb_usa.html (10.1): ganho relativo de
    cada lambda, normalizado pelos DOIS extremos DAQUELE MESMO beta — a
    unica comparacao valida entre betas diferentes, porque G_atual(beta)
    tambem muda com beta (ver a tabela de (A))."""
    linhas = []
    for beta, d in resultados.items():
        atual = d["atual"]
        pl = d["por_lambda"]
        g0, t0 = pl[f"{lambdas[0]:g}"]["joelho"]["f_gini"], pl[f"{lambdas[0]:g}"]["joelho"]["f_tempo"]
        for lam in lambdas:
            j = pl[f"{lam:g}"]["joelho"]
            den_g = atual["f_gini"] - g0
            den_t = atual["f_tempo"] - t0
            linhas.append({
                "beta": beta, "lam": lam,
                "f_tempo": j["f_tempo"], "f_gini": j["f_gini"],
                "movidas": j["movidas"], "km_total": j["km_total"],
                "rho_g": float((atual["f_gini"] - j["f_gini"]) / den_g) if den_g else None,
                "rho_t": float((atual["f_tempo"] - j["f_tempo"]) / den_t) if den_t else None,
                "atual_f_tempo": atual["f_tempo"], "atual_f_gini": atual["f_gini"],
            })
    return linhas


def main(betas_sweep=BETAS_SWEEP, lambdas=LAMBDAS_SWEEP):
    print("== (A) tabela barata: config atual sob cada beta ==", flush=True)
    tabela = tabela_barata()

    print("\n== (B) varredura completa (reotimiza) ==", flush=True)
    resultados = sweep_completo(betas_sweep, lambdas)
    ind = indicadores(resultados, lambdas)

    saida = {"tabela_atual": tabela, "sweep": ind,
             "betas_sweep": list(betas_sweep), "lambdas_sweep": list(lambdas)}
    arq = DADOS / "sp_beta_sens.json"
    json.dump(saida, open(arq, "w"), indent=2, default=float)

    print(f"\n== resumo: o achado sobrevive? (rho_G em lambda=1) ==")
    print(f"{'beta':>6}{'rho_G(lam=1)':>14}{'km(lam=1)/km(lam=0)':>22}")
    for beta in betas_sweep:
        linha1 = next(r for r in ind if r["beta"] == beta and r["lam"] == 1.0)
        linha0 = next(r for r in ind if r["beta"] == beta and r["lam"] == 0.0)
        razao_km = linha1["km_total"] / linha0["km_total"] if linha0["km_total"] else float("nan")
        print(f"{beta:>6g}{linha1['rho_g']:>14.2f}{razao_km:>22.2f}")
    print(f"\n-> {arq}")


if __name__ == "__main__":
    args = [float(a) for a in sys.argv[1:]]
    main(tuple(args) if args else BETAS_SWEEP, LAMBDAS_SWEEP)
