"""Simulacao (avaliador independente) das melhores solucoes da busca com hipercubo.

Para cada (lam, K) escolhe a melhor semente VIAVEL pelo objetivo do proprio
hipercubo e a simula com a simulacao da fase 3 (fase3_vidas.experimentos.vidas.tarefa_sim),
servico central, sementes 1-3 — as mesmas das solucoes da fase 3, o que da
comparacao pareada (mesmos chamados). Grava dados/fase4/h_simulacao.json.

Uso: uv run python -m fase4_hipercubo.experimentos.simula_solucoes --workers 12
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse                                    # noqa: E402
import json                                        # noqa: E402
import time                                        # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np                                 # noqa: E402

from fase3_vidas.experimentos import vidas as V    # noqa: E402

from ..caminhos import DADOS                       # noqa: E402

ALVOS = ((0.0, 20), (0.0, 40), (0.0, None), (1.0, 40), (1.0, None))   # (lam, K)
SEMENTES = (1, 2, 3)


def escolhe():
    res = json.load(open(DADOS / "h_busca.json", encoding="utf-8"))
    out = {}
    for lam, K in ALVOS:
        g = [r for r in res if r["lam"] == lam and r["K"] == K and r["partida"] == "hoje" and r["viavel"]]
        j = lambda r: r["hc"]["vidas"] + lam * r["hc"]["cvar10"]
        b = max(g, key=j)
        arq = DADOS / "h_refina" / f"lam{lam:g}_K{'livre' if K is None else K}.json"
        if arq.exists():                      # busca iterada (chutes), se feita
            rf = json.load(open(arq))
            if rf["viavel"] and j(rf) >= j(b):
                b = dict(rf, partida="hoje", semente=b["semente"], refinada=True)
        out[f"hc lam={lam:g} K={'livre' if K is None else K}"] = (np.array(b["yB"]), np.array(b["yA"]), b)
    # reotimizacoes: partida = solucao da fase 3; so os movimentos aceitos pelo hipercubo mudam
    for r in res:
        if r["partida"] != "hoje":
            out[f"reot {r['partida']}"] = (np.array(r["yB"]), np.array(r["yA"]), r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    sel = escolhe()
    tarefas = [(n, y[0], y[1], "central", s) for n, y in sel.items() for s in SEMENTES]
    print(time.strftime("%H:%M:%S"), f"{len(tarefas)} rodadas, {a.workers} processos", flush=True)
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(V.tarefa_sim, tarefas))
    linhas = []
    for r in res:
        l = {"config": r["config"], "servico": r["servico"], "semente": r["semente"]}
        l.update({f"sim_{k}": v for k, v in r["sim"].items()})
        l.update({f"an_{k}": v for k, v in r["analitico"].items()})
        linhas.append(l)
    (DADOS / "h_simulacao.json").write_text(json.dumps(dict(
        rodadas=linhas, sementes=SEMENTES,
        hc={n: y[2]["hc"] | {"movidas": y[2]["movidas"], "semente_busca": y[2]["semente"],
                             "refinada": bool(y[2].get("refinada", False)),
                             "yB": y[0].tolist(), "yA": y[1].tolist()}
            for n, y in sel.items()}), indent=1, default=float), encoding="utf-8")
    print(time.strftime("%H:%M:%S"), "pronto", flush=True)


if __name__ == "__main__":
    main()
