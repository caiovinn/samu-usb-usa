"""Busca local com o hipercubo (fase 4). Retomavel: pula tarefas ja gravadas.

    uv run python -m fase4_hipercubo.experimentos.roda_busca --teste
    uv run python -m fase4_hipercubo.experimentos.roda_busca --workers 6

Tarefas (lam, K, semente) a partir de "hoje", e (lam, K=livre) a partir de cada
solucao ja otimizada na fase 3 (para ver se reotimizar com o hipercubo a muda).
Cada tarefa grava dados/fase4/h_busca/<nome>.json; o resumo vai a h_busca.json.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse                                    # noqa: E402
import json                                        # noqa: E402
import time                                        # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402

import numpy as np                                 # noqa: E402

from fase3_vidas.experimentos import vidas as V    # noqa: E402
from fase3_vidas.modelo import busca as BU         # noqa: E402

from ..caminhos import DADOS                       # noqa: E402
from ..modelo import hc_real as HR                 # noqa: E402
from ..modelo.busca_hc import BuscaHC              # noqa: E402

S_MIN = 70.0                      # servico central; sensibilidade fica para depois
VARIANTE = "larson75"
SAIDA = DADOS / "h_busca"
TESTE = {"ativo": os.environ.get("FASE4_TESTE") == "1"}
if TESTE["ativo"]:
    SAIDA = DADOS / "_teste"
SEMENTES = (0, 1, 2)
KS = (20, 40, None)
LAMS = (0.0, 1.0)
PARTIDAS_F3 = (("vidas lam=0 K=40", 0.0, 40), ("vidas lam=0 K=livre", 0.0, None),
               ("vidas lam=1 K=livre", 1.0, None), ("p-median", 0.0, None))

_B = {}


def busca():
    if not _B:
        D = HR.dados()
        f, a = V.fator()
        qb, qa = V.qs()
        C, G = BU.coberturas(D["Ts"] if "Ts" in D else D["T"].T, f, a)
        bz = BuscaHC(C, G, D["pop"], qb, qa, D["x0B"], D["x0A"], fator=f, atraso=a,
                     s_min=S_MIN, taxas=HR.taxas_sia(), variante=VARIANTE)
        base = bz.medidas(bz.estado(D["x0B"], D["x0A"]))
        _B.update(bz=bz, base=base, viz=__import__("fase2_sao_paulo.experimentos.roda",
                                                  fromlist=["vizinhos"]).vizinhos(D["cd"]))
    return _B["bz"], _B["base"]


def nome(lam, K, partida, s):
    return f"lam{lam:g}_K{'livre' if K is None else K}_{partida}_s{s}".replace(" ", "_").replace("=", "")


def tarefa(args):
    lam, K, partida, s = args
    arq = SAIDA / f"{nome(lam, K, partida, s)}.json"
    if arq.exists():
        return json.load(open(arq))
    bz, base = busca()
    D = HR.dados()
    if partida == "hoje":
        y0 = (D["x0B"], D["x0A"])
    else:
        y0 = V.finalistas()[partida]
    t0 = time.time()
    n0 = bz.n_aval
    st, md, hist = bz.otimiza(*y0, lam=lam, K=K, base=base, semente=s,
                              max_passos=1 if TESTE["ativo"] else 30)
    yB, yA = st["y"]["B"], st["y"]["A"]
    hc = bz.avalia_hc(yB, yA)
    ok = (md["cob_basico"] >= base["cob_basico"] - 1e-9 and md["cob_grave"] >= base["cob_grave"] - 1e-9
          and (K is None or bz.movidas(st["y"]) <= K))
    out = {"lam": lam, "K": K, "partida": partida, "semente": s, "viavel": bool(ok),
           "hc": {k: v for k, v in hc.items() if k not in ("S", "rho")},
           "movidas": bz.movidas(st["y"]), "avaliacoes": bz.n_aval - n0,
           "passos": len(hist) - 1, "yB": yB.tolist(), "yA": yA.tolist(),
           "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(arq, "w"), default=float)
    return out


CHUTES, TAM_CHUTE = 10, 3          # como a fase 3 (vidas.py)
REFINA = DADOS / "h_refina"
ALVOS_REFINO = ((0.0, 20), (0.0, 40), (0.0, None), (1.0, 40), (1.0, None))


def tarefa_refina(args):
    """Busca local iterada (chutes) a partir da melhor semente viavel de (lam, K)."""
    lam, K, yB, yA, s_ini = args
    arq = REFINA / f"lam{lam:g}_K{'livre' if K is None else K}.json"
    if arq.exists():
        return json.load(open(arq))
    bz, base = busca()
    t0, n0 = time.time(), bz.n_aval
    st, md, ganhos = bz.refina(np.array(yB), np.array(yA), lam=lam, K=K, base=base,
                               chutes=CHUTES, tam=TAM_CHUTE, viz=_B["viz"], semente=s_ini)
    hc = bz.avalia_hc(st["y"]["B"], st["y"]["A"])
    ok = (md["cob_basico"] >= base["cob_basico"] - 1e-9 and md["cob_grave"] >= base["cob_grave"] - 1e-9
          and (K is None or bz.movidas(st["y"]) <= K))
    out = {"lam": lam, "K": K, "viavel": bool(ok), "ganhos_chutes": [float(g) for g in ganhos],
           "hc": {k: v for k, v in hc.items() if k not in ("S", "rho")},
           "movidas": bz.movidas(st["y"]), "avaliacoes": bz.n_aval - n0,
           "yB": st["y"]["B"].tolist(), "yA": st["y"]["A"].tolist(), "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(arq, "w"), default=float)
    return out


def refina(workers):
    REFINA.mkdir(exist_ok=True)
    res = json.load(open(DADOS / "h_busca.json", encoding="utf-8"))
    ts = []
    for lam, K in ALVOS_REFINO:
        g = [r for r in res if r["lam"] == lam and r["K"] == K and r["partida"] == "hoje" and r["viavel"]]
        b = max(g, key=lambda r: r["hc"]["vidas"] + lam * r["hc"]["cvar10"])
        ts.append((lam, K, b["yB"], b["yA"], b["semente"]))
    print(time.strftime("%H:%M:%S"), f"refina: {len(ts)} buscas iteradas ({CHUTES} chutes de {TAM_CHUTE})", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(tarefa_refina, ts):
            print(time.strftime("%H:%M:%S"), f"  lam={r['lam']} K={r['K']}: vidas {r['hc']['vidas']:.2f} "
                  f"movidas {r['movidas']} viavel {r['viavel']} {r['segundos']} s", flush=True)


def tarefas():
    t = [(l, K, "hoje", s) for l in LAMS for K in KS for s in SEMENTES]
    t += [(l, K, p, 0) for p, l, K in PARTIDAS_F3]
    if TESTE["ativo"]:
        t = [(0.0, 20, "hoje", 0)]
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--teste", action="store_true")
    ap.add_argument("--etapa", choices=("busca", "refina"), default="busca")
    a = ap.parse_args()
    if a.etapa == "refina":
        return refina(a.workers)
    if a.teste:
        os.environ["FASE4_TESTE"] = "1"
        TESTE["ativo"] = True
        globals()["SAIDA"] = DADOS / "_teste"
    SAIDA.mkdir(exist_ok=True)
    ts = tarefas()
    print(time.strftime("%H:%M:%S"), f"{len(ts)} buscas, {a.workers} processos", flush=True)
    res = []
    with ProcessPoolExecutor(a.workers) as ex:
        fut = {ex.submit(tarefa, t): t for t in ts}
        for i, fu in enumerate(as_completed(fut), 1):
            r = fu.result()
            res.append(r)
            print(time.strftime("%H:%M:%S"), f"  {i}/{len(ts)} lam={r['lam']} K={r['K']} {r['partida']} "
                  f"s{r['semente']}: vidas {r['hc']['vidas']:.2f} movidas {r['movidas']} "
                  f"viavel {r['viavel']} {r['segundos']} s", flush=True)
    (SAIDA.parent / ("h_busca_teste.json" if a.teste else "h_busca.json")).write_text(
        json.dumps(res, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
