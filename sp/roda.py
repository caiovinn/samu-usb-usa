"""Roda o experimento da fase 2: baseline, NSGA-II e fronteira de Pareto.

    python sp/roda.py                 # varre todos os lambda
    python sp/roda.py 0.03            # so um lambda
    python sp/roda.py 0.03 --beta 6   # outra ancoragem do Huff

lambda e o preco da mudanca, em MINUTOS de tempo de resposta por KM que cada
unidade precisa se deslocar para assumir a nova base. lambda = 0 e o redesenho
livre; lambda alto congela a rede como esta. Varrer lambda produz a curva
"quanto de ganho cada quilometro de mudanca compra".

Grava em dados/: sp_pareto_lam{..}.parquet, sp_pareto_x_lam{..}.npy e
sp_resultado.json com o resumo de todos os lambda.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import huff2sfca as H
import mudanca
import pmedian
from otimiza import Problema, joelho, nsga2

DADOS = Path(__file__).resolve().parent.parent / "dados"
N_POP, N_GER, CAP_MAX, K_VIZ = 80, 150, 10, 12
LAMBDAS = (0.0, 0.01, 0.03, 0.1, 0.3, 1.0)
ORCAMENTO = 420          # s por lambda


def carrega():
    st = pd.read_parquet(DADOS / "sp_setores.parquet")
    cd = pd.read_parquet(DADOS / "sp_candidatos.parquet")
    # candidatos nas linhas: ver o cabecalho de huff2sfca
    T = np.ascontiguousarray(np.load(DADOS / "sp_tempos.npy").T)
    return st, cd, T


def vizinhos(cd, k=K_VIZ):
    """k candidatos mais proximos de cada candidato, para a mutacao local."""
    la, lo = np.radians(cd.lat.values), np.radians(cd.lon.values)
    dx = (lo[:, None] - lo[None, :]) * np.cos(la.mean())
    dy = la[:, None] - la[None, :]
    return np.argsort(dx * dx + dy * dy, axis=1)[:, 1:k + 1]


def metricas(T, pop, x, n_usb, x0, D, lam=0.0, **kw):
    """Metricas de uma configuracao.

    f_tempo e SEMPRE o tempo puro, para comparar entre lambdas. f_obj e o
    objetivo que o NSGA-II de fato minimizou (tempo + preco da mudanca) — e o
    espaco em que o joelho da fronteira tem de ser escolhido, aqui e nas
    figuras.
    """
    r = H.avalia(T, pop, x[:n_usb], x[n_usb:], **kw)
    conta = np.bincount(x)
    km = mudanca.custo(x, x0, D, n_usb)
    return {"f_tempo": r["f_tempo"], "f_gini": r["f_gini"],
            "f_obj": r["f_tempo"] + lam * km / len(x), "lam": lam,
            "gini_basico": r["gini_basico"],
            "pct_usa_20min": r["pct_pop_usa_20min"],
            "pct_usb_10min": r["pct_pop_usb_10min"],
            "et_usa_mediana": float(np.median(r["T_av"])),
            "et_usa_p90": float(np.percentile(r["T_av"], 90)),
            "n_ef_usa": r["n_ef_usa"],
            "locais": int((conta > 0).sum()), "max_por_local": int(conta.max()),
            "movidas": mudanca.movidas(x, x0, n_usb),
            "km_total": km, "km_por_unidade": km / len(x)}


def semente_pmedian(T, pop, n_usb, n_usa):
    """Solucao do p-median classico, usada para semear o NSGA-II."""
    arq = DADOS / "sp_pmedian_x.npy"
    if arq.exists():
        return np.load(arq)
    sel, _ = pmedian.resolve(T, pop, n_usb + n_usa)
    pos, _ = pmedian.resolve(T[sel], pop, n_usa)
    usa = sel[pos]
    usb = np.array([s for s in sel if s not in set(map(int, usa))])
    x = np.concatenate([usb, usa])
    np.save(arq, x)
    return x


def roda_lambda(lam, T, pop, cd, x0, n_usb, n_usa, D, viz, beta, sementes):
    kw = dict(beta=beta)
    prob = Problema(T, pop, n_usb, n_usa, viz=viz, cap_max=CAP_MAX,
                    x0=x0, d_km=D, lam=lam, **kw)
    ck = DADOS / f"sp_ckpt_lam{lam:g}.npz"
    print(f"\n== lambda = {lam:g} min/km ==", flush=True)
    t0 = time.time()
    X, F, completo = nsga2(prob, n_pop=N_POP, n_ger=N_GER, semente=42,
                           x0=sementes, checkpoint=ck, orcamento=ORCAMENTO)
    print(f"  {time.time()-t0:.0f}s, {len(X)} solucoes nao dominadas"
          f"{'' if completo else '  (PARCIAL — rode de novo)'}", flush=True)

    linhas = [metricas(T, pop, x, n_usb, x0, D, lam=lam, **kw) for x in X]
    pd.DataFrame(linhas).to_parquet(DADOS / f"sp_pareto_lam{lam:g}.parquet")
    np.save(DADOS / f"sp_pareto_x_lam{lam:g}.npy", X)

    V = np.array([[d["f_obj"], d["f_gini"]] for d in linhas])
    return linhas, linhas[joelho(V)], completo


def main(lambdas=LAMBDAS, beta=H.BETA):
    st, cd, T = carrega()
    pop = st["pop"].values.astype(float)
    x0 = np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                         np.repeat(cd.id.values, cd.n_usa.values)])
    n_usb, n_usa = int(cd.n_usb.sum()), int(cd.n_usa.sum())
    D = mudanca.matriz_km(cd.lat.values, cd.lon.values)
    viz = vizinhos(cd)
    print(f"setores {len(st)} | candidatos {len(cd)} | frota {n_usb} USB + "
          f"{n_usa} USA | beta {beta} | pop {pop.sum():,.0f}")

    base = metricas(T, pop, x0, n_usb, x0, D, beta=beta)
    print("\n== configuracao atual ==")
    print(f"  tempo esperado {base['f_tempo']:.3f} min | Gini USA "
          f"{base['f_gini']:.4f} | USA<=20min {base['pct_usa_20min']:.1f}% | "
          f"{base['locais']} locais")

    saida = {"beta": beta, "atual": base, "n_pop": N_POP, "n_ger": N_GER,
             "cap_max": CAP_MAX, "por_lambda": {}}
    arq = DADOS / "sp_resultado.json"
    if arq.exists():
        saida["por_lambda"] = json.load(open(arq)).get("por_lambda", {})

    print("  semente p-median...", flush=True)
    x_pm = semente_pmedian(T, pop, n_usb, n_usa)
    sementes = np.vstack([x0, x_pm])

    for lam in lambdas:
        linhas, joelho, ok = roda_lambda(lam, T, pop, cd, x0, n_usb, n_usa,
                                         D, viz, beta, sementes)
        saida["por_lambda"][f"{lam:g}"] = {"joelho": joelho, "fronteira": linhas,
                                           "completo": bool(ok)}
        print(f"  joelho: tempo {base['f_tempo']:.2f} -> {joelho['f_tempo']:.2f} min "
              f"({100*(joelho['f_tempo']/base['f_tempo']-1):+.1f}%) | "
              f"Gini {base['f_gini']:.4f} -> {joelho['f_gini']:.4f} | "
              f"{joelho['movidas']} movidas, {joelho['km_total']:.0f} km", flush=True)
        json.dump(saida, open(arq, "w"), indent=2, default=float)

    print(f"\n== resumo ==")
    print(f"{'lambda':>8}{'E[T] min':>10}{'Gini':>9}{'movidas':>9}{'km':>9}"
          f"{'km/unid':>9}{'locais':>8}")
    print(f"{'atual':>8}{base['f_tempo']:10.2f}{base['f_gini']:9.4f}"
          f"{0:9d}{0:9d}{0:9.1f}{base['locais']:8d}")
    for lam in sorted(saida["por_lambda"], key=float):
        j = saida["por_lambda"][lam]["joelho"]
        print(f"{lam:>8}{j['f_tempo']:10.2f}{j['f_gini']:9.4f}{j['movidas']:9.0f}"
              f"{j['km_total']:9.0f}{j['km_por_unidade']:9.1f}{j['locais']:8.0f}")
    print(f"\n-> dados/sp_pareto_lam*.parquet, sp_resultado.json")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    beta = H.BETA
    if "--beta" in sys.argv:
        beta = float(sys.argv[sys.argv.index("--beta") + 1])
        args = [a for a in args if a != str(beta)]
    main([float(a) for a in args] if args else LAMBDAS, beta)
