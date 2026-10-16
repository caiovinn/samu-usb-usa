"""Orquestrador local e retomavel do modelo despacho (unidade disponivel mais
proxima, ocupacao q estimada do SIA). Feito para rodar sozinho na maquina do
usuario, horas, sem ninguem olhando:

    uv run python -m fase2_sao_paulo.experimentos.roda_tudo           # tudo
    uv run python -m fase2_sao_paulo.experimentos.roda_tudo --workers 8

Etapas — cada uma e pulada se a saida ja existe:
  1. coleta/pull_sia_samu     -> dados/fase2/sp_samu_producao.parquet
  2. demanda_samu             -> dados/fase2/sp_utilizacao.json (theta, q)
  3. testes dos modulos (huff2sfca, otimiza)
  4. sensib_q                 -> dados/fase2/sp_q_sens.json (ponte, reavaliacao)
  5. varredura NSGA-II        -> dados/fase2/varredura_q/*  (um job por cenario,
                                 lambda e semente, em paralelo)
  6. resumo                   -> dados/fase2/sp_q_sweep.json

O NSGA-II e o mesmo de roda.py (N_POP, N_GER, sementes atual + p-median), so
que sem o ORCAMENTO de 420 s: ele existia pelo limite de tempo do shell
remoto, nao por convergencia. Cada job usa uma thread (o gargalo do despacho e
o argpartition, que e serial), entao os jobs rodam lado a lado.
"""
import os

# antes do numpy: um job = uma thread de BLAS, os jobs e que sao paralelos
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse                                     # noqa: E402
import json                                         # noqa: E402
import time                                         # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402

import numpy as np                                  # noqa: E402
import pandas as pd                                 # noqa: E402

from fase2_sao_paulo.caminhos import DADOS          # noqa: E402

VARR = DADOS / "varredura_q"
LAMBDAS = (0.0, 0.1, 1.0)
SEMENTE_BASE = 42
SEMENTES_EXTRA = (1, 2)            # replicas do cenario central, ruido do NSGA-II
LAMBDAS_REPLICA = (0.1, 1.0)
# variante com restricao: no pior decil da populacao, chance >= 25% de a USA
# chegar em ate 10 min (o p-median chega a ~35%; a rede de hoje, 0%). Sem
# ela, minimizar o Gini da acessibilidade deixa esse decil com ~0%
RESTR = {"tau_restr": 10.0, "cob_min": 25.0}
SUF_RESTR = "_r25"
EXTRAS = ("cob_usa_8", "cob_usa_10", "cob_usa_15", "cob_usa_10_p10",
          "cob_usa_15_p10", "pct_pop_usa_20min", "gini_basico", "n_ef_usa")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def cenarios():
    """{nome: kw do modelo}, a partir de sp_utilizacao.json."""
    u = json.load(open(DADOS / "sp_utilizacao.json"))
    out = {n: dict(modelo="despacho", q_usb=v["q_usb"], q_usa=v["q_usa"])
           for n, v in u["q"].items()}
    th = u.get("theta_dados")
    if th:
        out["central_theta"] = dict(out["central"], theta=float(th))
    for n in ("baixo", "central", "alto"):
        out[n + SUF_RESTR] = dict(out[n], **RESTR)
    return out


def _kw_av(kw):
    """kw do cenario sem o que so o otimizador entende."""
    return {k: v for k, v in kw.items() if k != "cob_min"}


def jobs(cen):
    js = []
    for suf in ("", SUF_RESTR):
        js += [(c + suf, lam, SEMENTE_BASE) for c in ("baixo", "central", "alto")
               for lam in LAMBDAS]
        js += [("central" + suf, lam, s) for s in SEMENTES_EXTRA for lam in LAMBDAS_REPLICA]
    if "central_theta" in cen:
        js += [("central_theta", lam, SEMENTE_BASE) for lam in (0.0,) + LAMBDAS_REPLICA]
    return js


def _nome(c, lam, s):
    return f"{c}_lam{lam:g}_s{s}"


def roda_job(c, kw, lam, semente):
    """Um NSGA-II completo. Grava a fronteira e devolve o joelho."""
    from fase2_sao_paulo.experimentos import roda as R
    from fase2_sao_paulo.modelo import huff2sfca as H
    from fase2_sao_paulo.modelo import mudanca
    from fase2_sao_paulo.modelo.otimiza import Problema, joelho, nsga2

    nome = _nome(c, lam, semente)
    st, cd, T = R.carrega()
    pop = st["pop"].values.astype(float)
    x0 = np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                         np.repeat(cd.id.values, cd.n_usa.values)])
    n_usb, n_usa = int(cd.n_usb.sum()), int(cd.n_usa.sum())
    D = mudanca.matriz_km(cd.lat.values, cd.lon.values)
    sementes = np.vstack([x0, R.semente_pmedian(T, pop, n_usb, n_usa)])
    prob = Problema(T, pop, n_usb, n_usa, viz=R.vizinhos(cd), cap_max=R.CAP_MAX,
                    x0=x0, d_km=D, lam=lam, **kw)
    t0 = time.time()
    X, _, completo = nsga2(prob, n_pop=R.N_POP, n_ger=R.N_GER, semente=semente,
                           x0=sementes, checkpoint=VARR / f"ckpt_{nome}.npz",
                           orcamento=None, verbose=False)
    kav = _kw_av(kw)
    linhas = []
    for x in X:
        m = R.metricas(T, pop, x, n_usb, x0, D, lam=lam, **kav)
        r = H.avalia(T, pop, x[:n_usb], x[n_usb:], **kav)
        m.update({e: float(r[e]) for e in EXTRAS})
        m["viavel"] = bool(kw.get("cob_min") is None
                           or r["cob_usa_10_p10"] >= kw["cob_min"] - 1e-9)
        linhas.append(m)
    pd.DataFrame(linhas).to_parquet(VARR / f"pareto_{nome}.parquet")
    np.save(VARR / f"pareto_x_{nome}.npy", X)
    # joelho so entre as viaveis (sem restricao, todas sao)
    ok = [d for d in linhas if d["viavel"]] or linhas
    j = ok[joelho(np.array([[d["f_obj"], d["f_gini"]] for d in ok]))]
    j.update({"cenario": c, "lam": lam, "semente": semente,
              "segundos": time.time() - t0, "completo": bool(completo)})
    json.dump(j, open(VARR / f"joelho_{nome}.json", "w"), indent=2, default=float)
    return nome, j


def referencias(cen):
    """Atual e p-median sob cada cenario: a linha de base muda com q."""
    from fase2_sao_paulo.experimentos import roda as R
    from fase2_sao_paulo.modelo import huff2sfca as H
    st, cd, T = R.carrega()
    pop = st["pop"].values.astype(float)
    n_usb = int(cd.n_usb.sum())
    x0 = np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                         np.repeat(cd.id.values, cd.n_usa.values)])
    xp = np.load(DADOS / "sp_pmedian_x.npy")
    out = {}
    for c, kw in cen.items():
        for nome, x in (("atual", x0), ("p-median", xp)):
            r = H.avalia(T, pop, x[:n_usb], x[n_usb:], **_kw_av(kw))
            out[f"{c}|{nome}"] = {"f_tempo": r["f_tempo"], "f_gini": r["f_gini"],
                                  **{e: float(r[e]) for e in EXTRAS}}
    return out


def resumo(cen):
    js = {}
    for arq in sorted(VARR.glob("joelho_*.json")):
        d = json.load(open(arq))
        js[_nome(d["cenario"], d["lam"], d["semente"])] = d
    ref = referencias(cen)
    linhas = []
    for nome, j in js.items():
        c, lam = j["cenario"], j["lam"]
        a = ref[f"{c}|atual"]
        j0 = js.get(_nome(c, 0.0, SEMENTE_BASE))
        rho_g = rho_t = None
        if j0:
            dg, dt = a["f_gini"] - j0["f_gini"], a["f_tempo"] - j0["f_tempo"]
            rho_g = (a["f_gini"] - j["f_gini"]) / dg if dg else None
            rho_t = (a["f_tempo"] - j["f_tempo"]) / dt if dt else None
        linhas.append({"job": nome, "cenario": c, "lam": lam, "semente": j["semente"],
                       "f_tempo": j["f_tempo"], "f_gini": j["f_gini"],
                       "movidas": j["movidas"], "km_total": j["km_total"],
                       "rho_g": rho_g, "rho_t": rho_t,
                       "cob_usa_10_p10": j.get("cob_usa_10_p10"),
                       "cob_usa_15_p10": j.get("cob_usa_15_p10"),
                       "completo": j["completo"]})
    json.dump({"cenarios": cen, "referencias": ref, "joelhos": linhas},
              open(DADOS / "sp_q_sweep.json", "w"), indent=2, default=float)
    df = pd.DataFrame(linhas).sort_values(["cenario", "lam", "semente"])
    with pd.option_context("display.width", 200, "display.precision", 3):
        print(df.drop(columns=["job", "completo"]).to_string(index=False))
    for c in cen:
        a, p = ref[f"{c}|atual"], ref[f"{c}|p-median"]
        print(f"  {c:>13}: atual E[T] {a['f_tempo']:.2f} Gini {a['f_gini']:.3f} "
              f"p10cob10 {a['cob_usa_10_p10']:.1f}% | p-median {p['f_tempo']:.2f} / "
              f"{p['f_gini']:.3f} / {p['cob_usa_10_p10']:.1f}%")


def main(workers):
    if not (DADOS / "sp_samu_producao.parquet").exists():
        log("[1] SIA")
        from fase2_sao_paulo.coleta import pull_sia_samu
        pull_sia_samu.main()
    if not (DADOS / "sp_utilizacao.json").exists():
        log("[2] utilizacao")
        from fase2_sao_paulo.experimentos import demanda_samu
        demanda_samu.main()
    log("[3] testes")
    from fase2_sao_paulo.modelo import huff2sfca, otimiza
    huff2sfca._teste()
    otimiza._teste()
    log("[4] ponte e reavaliacao barata")
    from fase2_sao_paulo.experimentos import sensib_q
    sensib_q.main()

    VARR.mkdir(exist_ok=True)
    cen = cenarios()
    falta = [(c, lam, s) for c, lam, s in jobs(cen)
             if not (VARR / f"joelho_{_nome(c, lam, s)}.json").exists()]
    log(f"[5] varredura: {len(falta)} jobs em {workers} processos")
    with ProcessPoolExecutor(workers) as ex:
        fut = {ex.submit(roda_job, c, cen[c], lam, s): (c, lam, s) for c, lam, s in falta}
        for f in as_completed(fut):
            try:
                nome, j = f.result()
                log(f"  ok {nome}: E[T] {j['f_tempo']:.2f} Gini {j['f_gini']:.3f} "
                    f"{j['movidas']} movidas {j['km_total']:.0f} km "
                    f"({j['segundos']/60:.0f} min)")
            except Exception as e:
                log(f"  ERRO {fut[f]}: {e!r}")
    log("[6] resumo")
    resumo(cen)
    log("-> dados/fase2/sp_q_sweep.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    main(ap.parse_args().workers)
