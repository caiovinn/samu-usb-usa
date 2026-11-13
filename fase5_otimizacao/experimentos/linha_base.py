"""Linha de base da fase 5: todos os mapas ja produzidos, pela MESMA regua.

    uv run python -m fase5_otimizacao.experimentos.linha_base

Regua: o hipercubo (Larson 1975, variante larson75) com desempate fixo
(modelo/avaliador.py), servico central de 70 min, taxas do SIA -- o avaliador
de aceitacao da busca da fase 4. Mapas: hoje, p-median, os finalistas da fase 3
e os resultados da busca da fase 4 (todas as sementes, as reotimizacoes que
partem da fase 3 e o refino iterado). Para cada mapa: vidas e CVaR10 por 1.000
PCR, objetivo J = vidas + lam * CVaR10 (lam = 0 e 1), guardas (coberturas >=
as de hoje), unidades movidas e km, e quantas avaliacoes a busca gastou.

Saida: dados/fase5/linha_base.json (uma linha por mapa).
"""
import json
import time

import numpy as np

from fase3_vidas.experimentos import vidas as V
from fase4_hipercubo.modelo import hc_real as HR

from ..caminhos import DADOS, DADOS_FASE3, DADOS_FASE4
from ..modelo.avaliador import Avaliador

S_MIN = 70.0


def mapas():
    """[(rotulo, origem, lam, K, semente, yB, yA, avaliacoes)]"""
    out = []
    # mapas salvos pela fase 3 (le os .npy direto: V.finalistas() refaz os joelhos da
    # fase 2b a partir de dados/fase2/varredura_q, que nao esta no repositorio)
    for arq in sorted(DADOS_FASE3.glob("v2_y_*.npy")):
        nome = arq.stem[len("v2_y_"):]
        y = np.load(arq)
        out.append((nome, "anterior", 0.0, None, None, y[0], y[1], None))
    for lam in (0.0, 1.0):
        for K in (20, 40, "livre"):
            for g in ("", "_Gpm"):
                arq = DADOS_FASE3 / f"v3_y_lam{lam:g}_K{K}{g}.npy"
                if arq.exists():
                    y = np.load(arq)
                    out.append((f"fase3 lam={lam:g} K={K}{' (partida p-median)' if g else ''}",
                                "fase 3", lam, None if K == "livre" else K, None, y[0], y[1], None))
    for r in json.load(open(DADOS_FASE4 / "h_busca.json", encoding="utf-8")):
        K = "livre" if r["K"] is None else r["K"]
        if r["partida"] == "hoje":
            rot = f"fase4 busca lam={r['lam']:g} K={K} s{r['semente']}"
        else:
            rot = f"fase4 reotimiza [{r['partida']}] lam={r['lam']:g} K={K}"
        out.append((rot, "fase 4", r["lam"], r["K"], r["semente"], np.array(r["yB"]),
                    np.array(r["yA"]), r["avaliacoes"]))
    for arq in sorted((DADOS_FASE4 / "h_refina").glob("*.json")):
        r = json.load(open(arq, encoding="utf-8"))
        K = "livre" if r["K"] is None else r["K"]
        out.append((f"fase4 refino lam={r['lam']:g} K={K}", "fase 4", r["lam"], r["K"], None,
                    np.array(r["yB"]), np.array(r["yA"]), r["avaliacoes"]))
    return out


def main():
    t0 = time.time()
    f, a = V.fator()
    av = Avaliador(f, a, S_MIN, HR.taxas_sia())
    D = av.D
    hoje = av.avalia(D["x0B"], D["x0A"])
    linhas = []
    for rot, origem, lam, K, s, yB, yA, n_aval in mapas():
        r = av.avalia(yB, yA)
        mov, km = V.mudanca(yB, yA)
        guarda = (r["cob_basico_usb"] >= hoje["cob_basico_usb"] - 1e-9 and
                  r["cob_grave"] >= hoje["cob_grave"] - 1e-9)
        linhas.append({
            "rotulo": rot, "origem": origem, "lam": lam, "K": K, "semente": s,
            "vidas": r["vidas"], "cvar10": r["cvar10"],
            "J0": r["vidas"], "J1": r["vidas"] + r["cvar10"],
            "cob_grave": r["cob_grave"], "cob_basico_usb": r["cob_basico_usb"],
            "et_grave": r["et_grave"], "q_usb": r["q_usb"], "q_usa": r["q_usa"],
            "guardas_ok": bool(guarda), "movidas": mov, "km": km,
            "avaliacoes_busca": n_aval})
    out = {"regua": {"avaliador": "hipercubo larson75, desempate fixo (fase5 avaliador.py)",
                     "s_min": S_MIN, "fator": f, "atraso": a, "taxas": HR.taxas_sia()},
           "hoje": {k: v for k, v in hoje.items() if k not in ("S", "rho")},
           "mapas": linhas, "segundos": round(time.time() - t0, 1)}
    (DADOS / "linha_base.json").write_text(json.dumps(out, indent=1, default=float),
                                           encoding="utf-8")
    print(f"{len(linhas)} mapas em {out['segundos']} s -> dados/fase5/linha_base.json")
    print(f"{'mapa':48s}{'vidas':>8s}{'CVaR10':>8s}{'J1':>8s}{'mov':>5s}{'guarda':>7s}{'aval':>7s}")
    for l in linhas:
        print(f"{l['rotulo'][:48]:48s}{l['vidas']:8.2f}{l['cvar10']:8.2f}{l['J1']:8.2f}"
              f"{l['movidas']:5d}{'ok' if l['guardas_ok'] else 'NAO':>7s}"
              f"{'' if l['avaliacoes_busca'] is None else l['avaliacoes_busca']:>7}")


if __name__ == "__main__":
    main()
