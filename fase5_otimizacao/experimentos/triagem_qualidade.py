"""Qualidade da triagem: a ordem que cada metodo da aos destinos acerta o hipercubo?

    uv run python -m fase5_otimizacao.experimentos.triagem_qualidade

Para unidades sorteadas em dois mapas (hoje e fase 3 lam=0 K=40), calcula o
ganho aproximado de cada destino pelos metodos "q" (fase 3/4) e "rho" (fase 5),
e avalia no hipercubo (avaliador.py) a variacao REAL de vidas dos destinos
propostos: os 15 melhores de cada metodo + 10 sorteados. Por unidade:
  - correlacao de Spearman entre ganho aproximado e variacao real;
  - "acerto@4": o melhor destino real esta entre os 4 primeiros do metodo
    (a busca da fase 4 so avalia 4 por unidade);
  - "perda@4": melhor variacao real - melhor entre os 4 do metodo.
Objetivo: vidas (lam = 0), sem guardas -- e a qualidade da ORDEM que se mede.

Saida: dados/fase5/triagem_qualidade.json. Retomavel por mapa (--mapa 0 / 1):
cada mapa roda em ~1,5 min e e acrescentado ao JSON existente.
"""
import argparse
import json
import time

import numpy as np
from scipy.stats import spearmanr

from fase3_vidas.experimentos import vidas as V
from fase3_vidas.modelo import mip_vidas as MV
from fase4_hipercubo.modelo import hc_real as HR

from ..caminhos import DADOS, DADOS_FASE3
from ..modelo.avaliador import Avaliador
from ..modelo.triagem import Triagem

N_UNID, TOP, ALEAT, S_MIN = 10, 15, 10, 70.0


def main(n_unid=N_UNID, semente=0, so=None):
    t0 = time.time()
    f, a = V.fator()
    av = Avaliador(f, a, S_MIN, HR.taxas_sia())
    D = av.D
    qb, qa = V.qs()
    tr = Triagem(np.ascontiguousarray(D["T"].T), D["pop"], f, a, qb, qa, D["x0B"], D["x0A"])
    y3 = np.load(DADOS_FASE3 / "v3_y_lam0_K40.npy")
    mapas = {"hoje": (D["x0B"].copy(), D["x0A"].copy()), "fase3 lam=0 K=40": (y3[0], y3[1])}
    arq = DADOS / "triagem_qualidade.json"
    out = {"parametros": {"n_unid": n_unid, "top": TOP, "aleat": ALEAT, "s_min": S_MIN},
           "mapas": {}}
    if arq.exists() and so is not None:
        antigo = json.loads(arq.read_text(encoding="utf-8"))
        if antigo.get("parametros") == out["parametros"]:
            out = antigo
    for k, (nome, (yB, yA)) in enumerate(mapas.items()):
        if so is not None and k != so:
            continue
        rng = np.random.default_rng(semente + 1000 * k)
        base = av.avalia(yB, yA, detalhe=True)
        iB, iA = MV.para_indices(yB, yA)
        nB = len(iB)
        sts = {"q": tr.estado(yB, yA), "rho": tr.estado(yB, yA, base["rho"])}
        unid = rng.choice(len(iB) + len(iA), size=n_unid, replace=False)
        linhas = []
        for u in unid:
            tipo = "B" if u < nB else "A"
            j = int(iB[u] if u < nB else iA[u - nB])
            g = {}
            for met, st in sts.items():
                peso = tr.peso(tr.S(st), 0.0)
                g[met] = tr.ganhos(st, tipo, j, peso, unidade=u)
            cand = set()
            for met in g:
                cand |= set(np.argsort(-g[met])[:TOP].tolist())
            validos = np.nonzero(np.isfinite(g["q"]))[0]
            cand |= set(rng.choice(validos, size=ALEAT, replace=False).tolist())
            cand = np.array(sorted(cand))
            real = np.empty(len(cand))
            for k, jj in enumerate(cand):
                y2B, y2A = yB.copy(), yA.copy()
                y = y2B if tipo == "B" else y2A
                y[j] -= 1
                y[jj] += 1
                real[k] = av.avalia(y2B, y2A)["vidas"] - base["vidas"]
            melhor = real.max()
            lin = {"unidade": int(u), "tipo": tipo, "local": j, "ocupacao": float(base["rho"][u]),
                   "n_avaliados": int(len(cand)), "melhor_real": float(melhor)}
            for met in g:
                gm = g[met][cand]
                top4 = np.argsort(-gm)[:4]
                lin[met] = {"spearman": float(spearmanr(gm, real).statistic),
                            "acerto4": bool(np.argmax(real) in top4),
                            "perda4": float(melhor - real[top4].max()),
                            "real_top1": float(real[np.argmax(gm)])}
            linhas.append(lin)
            print(f"  {nome} u{u:3d} ({tipo}, ocup. {lin['ocupacao']:.2f}): melhor real {melhor:+.3f} | "
                  f"q: rho_s {lin['q']['spearman']:+.2f} perda4 {lin['q']['perda4']:.3f} | "
                  f"rho: rho_s {lin['rho']['spearman']:+.2f} perda4 {lin['rho']['perda4']:.3f}",
                  flush=True)
        res = {met: {"spearman_medio": float(np.mean([l[met]["spearman"] for l in linhas])),
                     "acerto4": float(np.mean([l[met]["acerto4"] for l in linhas])),
                     "perda4_media": float(np.mean([l[met]["perda4"] for l in linhas])),
                     "perda4_max": float(np.max([l[met]["perda4"] for l in linhas]))}
               for met in ("q", "rho")}
        out["mapas"][nome] = {"vidas_base": base["vidas"], "unidades": linhas, "resumo": res}
        print(f"== {nome}: {json.dumps(res)}", flush=True)
        out["mapas"][nome]["segundos"] = round(time.time() - t0, 1)
        out["mapas"][nome]["avaliacoes"] = av.n_aval
    arq.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"-> dados/fase5/triagem_qualidade.json ({round(time.time() - t0, 1)} s, "
          f"{av.n_aval} avaliacoes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapa", type=int, default=None, help="0 = hoje, 1 = fase 3 lam=0 K=40")
    ap.add_argument("--unidades", type=int, default=N_UNID)
    a = ap.parse_args()
    main(n_unid=a.unidades, so=a.mapa)
