"""Validacao da aproximacao em hipercubo contra o hipercubo EXATO (instancias pequenas).

Instancias sinteticas com a mesma estrutura do problema real: duas classes
(grave: so USA; basico: USB mais proxima livre e depois USA), unidades e zonas
no quadrado unitario, tempo = distancia. Varia n e a carga (ocupacao media
alvo) e compara a ocupacao independente (Daskin, usada nas fases 2b/3) e a
correcao de Larson com o exato, em: ocupacao por unidade, probabilidade de
despacho e tempo medio de resposta por classe. Varias sementes -> faixas.

Uso: uv run python -m fase4_hipercubo.experimentos.valida_exato
Saida: dados/fase4/v_exato_vs_aprox.json
"""
import json
import time

import numpy as np

from ..caminhos import DADOS
from ..modelo.hipercubo_aprox import aprox, aprox_larson75, matriz_p
from ..modelo.hipercubo_exato import exato

SEMENTES = range(8)
NS = (6, 10, 14)
CARGAS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)  # ocupacao media alvo (exato)
THETA = 0.10
VARIANTES = ("daskin", "local", "larson75")


def instancia(n, semente):
    rng = np.random.default_rng(semente)
    n_usa = max(2, n // 4)
    n_usb = n - n_usa
    pos = rng.random((n, 2))
    classe = np.array([0] * n_usb + [1] * n_usa)  # 0 USB, 1 USA
    z = 12
    zon = rng.random((z, 2))
    d = np.linalg.norm(zon[:, None] - pos[None], axis=2)  # (z, n)
    peso = rng.dirichlet(np.ones(z) * 2)
    listas, w, cl = [], [], []
    for i in range(z):
        usa = [u for u in np.argsort(d[i]) if classe[u] == 1]
        usb = [u for u in np.argsort(d[i]) if classe[u] == 0]
        listas.append(tuple(usa))
        w.append(THETA * peso[i])
        cl.append(0)
        listas.append(tuple(usb + usa))
        w.append((1 - THETA) * peso[i])
        cl.append(1)
    mu = np.where(classe == 1, 1.0, 1.0)  # servico igual; carga controlada por lam
    return dict(mu=mu, listas=listas, w=np.array(w), cl=np.array(cl), d=d, z=z, n=n)


def tempo_medio(P, bloq, d_lista, cl):
    """Tempo medio de resposta por classe, so dos chamados atendidos."""
    out = {}
    for c in (0, 1):
        sel = cl == c
        num = (P[sel] * d_lista[sel]).sum()
        den = P[sel].sum()
        out[c] = num / den if den > 0 else np.nan
    return out


def roda():
    t0 = time.time()
    linhas = []
    for n in NS:
        for carga in CARGAS:
            for s in SEMENTES:
                ins = instancia(n, s)
                mu, listas, w, cl = ins["mu"], ins["listas"], ins["w"], ins["cl"]
                # escala lam para a ocupacao media exata ficar no alvo (bisecao em a)
                lo, hi = 1e-3, 40.0 * n
                for _ in range(25):
                    a = 0.5 * (lo + hi)
                    ex = exato(mu, listas, a * w)
                    if ex["rho"].mean() < carga:
                        lo = a
                    else:
                        hi = a
                a = 0.5 * (lo + hi)
                lam = a * w
                ex = exato(mu, listas, lam)
                # distancia de cada unidade a cada lista (zona de origem da lista)
                dl = np.zeros((len(listas), n))
                for i, lst in enumerate(listas):
                    dl[i, :] = ins["d"][i // 2]
                te = tempo_medio(ex["P"], ex["bloq"], dl, cl)
                reg = dict(n=n, carga=carga, semente=s, bloq_exato=float((w * ex["bloq"]).sum() / w.sum()))
                for v in VARIANTES:
                    ap = aprox_larson75(mu, listas, lam) if v == "larson75" else aprox(mu, listas, lam, variante=v)
                    P = matriz_p(ap, n)
                    ta = tempo_medio(P, ap["bloq"], dl, cl)
                    reg[v] = dict(
                        conv=bool(ap["iter"] < 2000),
                        rho_max=float(np.abs(ap["rho"] - ex["rho"]).max()),
                        rho_med=float(np.abs(ap["rho"] - ex["rho"]).mean()),
                        P_max=float(np.abs(P - ex["P"]).max()),
                        t_grave=float(ta[0] - te[0]),
                        t_basico=float(ta[1] - te[1]),
                    )
                linhas.append(reg)
    return linhas, time.time() - t0


def resume(linhas):
    res = {}
    for n in NS:
        for carga in CARGAS:
            sub = [r for r in linhas if r["n"] == n and r["carga"] == carga]
            e = dict(bloq_exato=float(np.mean([r["bloq_exato"] for r in sub])))
            for v in VARIANTES:
                e[v] = dict(
                    rho_max_med=float(np.mean([r[v]["rho_max"] for r in sub])),
                    rho_max_p90=float(np.percentile([r[v]["rho_max"] for r in sub], 90)),
                    P_max_med=float(np.mean([r[v]["P_max"] for r in sub])),
                    t_grave_vies=float(np.mean([r[v]["t_grave"] for r in sub])),
                    t_basico_vies=float(np.mean([r[v]["t_basico"] for r in sub])),
                    nao_convergiu=int(sum(not r[v]["conv"] for r in sub)),
                )
            res[f"n{n}_carga{carga}"] = e
    return res


if __name__ == "__main__":
    linhas, seg = roda()
    res = resume(linhas)
    (DADOS / "v_exato_vs_aprox.json").write_text(
        json.dumps(dict(sementes=len(SEMENTES), theta=THETA, resumo=res), indent=1), encoding="utf-8")
    print(f"{len(linhas)} casos em {seg:.0f}s")
    print("variantes:", VARIANTES)
    for k, e in res.items():
        n, c = k[1:].split("_carga")
        print(f"{n:>2} {c:>4} {e['bloq_exato']:.3f} | rho_max " + " ".join(f"{e[v]['rho_max_med']:.4f}" for v in VARIANTES)
              + " | P_max " + " ".join(f"{e[v]['P_max_med']:.4f}" for v in VARIANTES)
              + " | t_grave " + " ".join(f"{e[v]['t_grave_vies']:+.4f}" for v in VARIANTES)
              + " | nao conv " + " ".join(str(e[v]['nao_convergiu']) for v in VARIANTES))
