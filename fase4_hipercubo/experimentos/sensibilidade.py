"""Sensibilidades do hipercubo (fase 4).

A  hipotese de servico: simulacao com servico Gamma (fase 3) e Exponencial, contra o
   hipercubo, em quatro configuracoes. Separa quanto do vies residual vem do servico.
B  tempo de servico 45 / 70 / 100 min: hipercubo e simulacao nas solucoes da busca
   e nas da fase 3 (ganho pareado por servico).
C  truncagem das listas de preferencia (12 x 20 USB mais proximas).

Uso: uv run python -m fase4_hipercubo.experimentos.sensibilidade --workers 6
Saida: dados/fase4/h_sensibilidade.json
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
from ..modelo import hc_real as HR                 # noqa: E402
from . import simula_hc as SH                      # noqa: E402

SEM = (1, 2, 3)
CFG_A = ("hoje", "p-median", "vidas lam=0 K=livre", "vidas lam=1 K=livre")


def _sim(args):
    nome, yB, yA, serv, sem, modo = args
    D = V.dados()
    f, a = V.fator()
    U = D["U"]
    taxas = (U["por_ano_12m"]["usa"] / 8760.0, U["por_ano_12m"]["usb"] / 8760.0)
    x = V.x_de(yB, yA)
    r, _, _ = SH.simula(D["T"], D["pop"], x, int(D["x0B"].sum()), *taxas, V.SERVICOS[serv], sem,
                        fator=f, atraso=a, servico=modo)
    return {"config": nome, "servico": serv, "semente": sem, "modo": modo, **r}


def _media(rs, **filtro):
    sel = [r for r in rs if all(r[k] == v for k, v in filtro.items())]
    return {k: float(np.mean([r[k] for r in sel])) for k in ("vidas", "et_grave", "cob_grave", "cob_basico", "q_usb", "q_usa")}


def melhores_hc():
    """Solucoes da busca com hipercubo: refinadas se existirem, senao a melhor semente."""
    out = {}
    refina = DADOS / "h_refina"
    for lam, K in ((0.0, 20), (0.0, 40), (0.0, None), (1.0, 40), (1.0, None)):
        nome = f"hc lam={lam:g} K={'livre' if K is None else K}"
        arq = refina / f"lam{lam:g}_K{'livre' if K is None else K}.json"
        if arq.exists():
            r = json.load(open(arq))
            out[nome] = (np.array(r["yB"]), np.array(r["yA"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    fin = V.finalistas()
    f, at = V.fator()
    tx = HR.taxas_sia()
    out = {}

    # ---------------- A: servico gamma x exponencial
    tarefas = [(c, *fin[c], "central", s, m) for c in CFG_A for s in SEM for m in ("gamma", "exp")]
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        rs = list(ex.map(_sim, tarefas))
    A = {}
    for c in CFG_A:
        h = HR.avalia(*fin[c], f, at, 70.0, tx, variante="larson75")
        A[c] = {"hipercubo": {k: h[k] for k in ("vidas", "et_grave", "cob_grave", "cob_basico", "q_usb", "q_usa")},
                "sim_gamma": _media(rs, config=c, modo="gamma"), "sim_exp": _media(rs, config=c, modo="exp")}
    out["A_servico"] = A
    print(time.strftime("%H:%M:%S"), f"A pronto ({time.time() - t0:.0f} s)", flush=True)

    # ---------------- B: tempo de servico (solucoes da busca refinada x fase 3)
    hc = melhores_hc()
    pares = {"hc lam=0 K=20": "vidas lam=0 K=20", "hc lam=0 K=40": "vidas lam=0 K=40",
             "hc lam=0 K=livre": "vidas lam=0 K=livre", "hc lam=1 K=40": "vidas lam=1 K=40",
             "hc lam=1 K=livre": "vidas lam=1 K=livre"}
    cfg = {**{k: v for k, v in hc.items()}, **{b: fin[b] for k, b in pares.items() if k in hc}}
    B = {}
    if hc:
        ts = [(c, *y, sv, s, "gamma") for c, y in cfg.items() for sv in V.SERVICOS for s in SEM]
        with ProcessPoolExecutor(a.workers) as ex:
            rs = list(ex.map(_sim, ts))
        for sv in V.SERVICOS:
            for k, b in pares.items():
                if k not in hc:
                    continue
                d = [r1["vidas"] - r2["vidas"] for r1, r2 in zip(
                    sorted([r for r in rs if r["config"] == k and r["servico"] == sv], key=lambda r: r["semente"]),
                    sorted([r for r in rs if r["config"] == b and r["servico"] == sv], key=lambda r: r["semente"]))]
                hm = HR.avalia(*hc[k], f, at, V.SERVICOS[sv], tx, variante="larson75")["vidas"]
                hb = HR.avalia(*fin[b], f, at, V.SERVICOS[sv], tx, variante="larson75")["vidas"]
                B[f"{k} | {sv}"] = {"dif_sim": float(np.mean(d)), "dif_sim_min": float(min(d)), "dif_sim_max": float(max(d)),
                                    "dif_hipercubo": hm - hb}
    out["B_tempo_servico"] = B
    print(time.strftime("%H:%M:%S"), "B pronto", flush=True)

    # ---------------- C: truncagem das listas
    C = {}
    for kB in (8, 12, 20):
        HR.listas.__defaults__ = (kB, HR.L_USA, HR.L_USB_RESTO)
        C[str(kB)] = {c: HR.avalia(*fin[c], f, at, 70.0, tx, variante="larson75")["vidas"] for c in CFG_A}
    HR.listas.__defaults__ = (HR.L_USB, HR.L_USA, HR.L_USB_RESTO)
    out["C_truncagem_usb"] = C
    (DADOS / "h_sensibilidade.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("pronto")


if __name__ == "__main__":
    main()
