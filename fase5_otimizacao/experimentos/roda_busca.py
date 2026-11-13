"""Fase 5, etapa 3: busca global com o hipercubo, sempre partindo da rede de hoje.

    uv run python -m fase5_otimizacao.experimentos.roda_busca --teste          # ~5 min, confere tudo
    uv run python -m fase5_otimizacao.experimentos.roda_busca --workers 6      # as 60 buscas
    uv run python -m fase5_otimizacao.experimentos.roda_busca --etapa resumo   # tabela por (lam, K)
    uv run python -m fase5_otimizacao.experimentos.roda_busca --etapa simula   # validacao independente

Retomavel: cada busca grava dados/fase5/busca/<nome>.json ao terminar e e pulada
se o arquivo ja existe. Pode interromper (Ctrl+C) e rodar de novo.

Tarefas: lam in (0, 1) x K in (20, 40, livre) x sementes 0..9, todas a partir
de hoje (x0, o CNES). Cada tarefa: busca local com triagem por ocupacao de cada
unidade + busca iterada (CHUTES chutes de TAM unidades, respeitando K)
-- modelo/busca_global.py. Objetivo e guardas da fase 3:
    J = vidas + lam * CVaR10; cob_basico_usb e cob_grave >= hoje; movidas <= K.

--guarda-grave fase3: em vez de "cob_grave >= hoje", exige a cobertura do grave
do mapa da fase 3 de mesmo (lam, K) (medida pelo mesmo hipercubo). Grava em
dados/fase5/busca_gg_fase3/ para nao misturar.

Avaliador: hipercubo larson75 com desempate fixo, servico de 70 min, taxas do SIA.
Uma thread de BLAS por processo; o paralelismo e entre buscas.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse                                                     # noqa: E402
import json                                                         # noqa: E402
import time                                                         # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed    # noqa: E402

import numpy as np                                                  # noqa: E402

from ..caminhos import DADOS, DADOS_FASE3, DADOS_FASE4              # noqa: E402

S_MIN = 70.0
LAMS = (0.0, 1.0)
KS = (20, 40, None)
SEMENTES = tuple(range(10))
CHUTES, TAM = 10, 3
N_CAND = 4
MAX_PASSOS = 30
SEMENTES_SIM = (1, 2, 3)          # as da fase 3/4: comparacao pareada

_W = {}                           # estado por processo


def _k(K):
    return "livre" if K is None else str(K)


def nome(lam, K, s):
    return f"lam{lam:g}_K{_k(K)}_s{s}"


def pasta(guarda):
    return DADOS / ("busca" if guarda == "hoje" else "busca_gg_fase3")


def _log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------ por processo
def _prepara():
    """Avaliador, triagem e medidas de hoje: uma vez por processo (~2 GB)."""
    if not _W:
        from fase3_vidas.experimentos import vidas as V
        from fase4_hipercubo.modelo import hc_real as HR
        from ..modelo.avaliador import Avaliador
        from ..modelo.triagem import Triagem
        f, a = V.fator()
        av = Avaliador(f, a, S_MIN, HR.taxas_sia())
        D = av.D
        qb, qa = V.qs()
        tr = Triagem(np.ascontiguousarray(D["T"].T), D["pop"], f, a, qb, qa, D["x0B"], D["x0A"])
        viz = __import__("fase2_sao_paulo.experimentos.roda", fromlist=["vizinhos"]).vizinhos(D["cd"])
        hoje = av.avalia(D["x0B"], D["x0A"])
        _W.update(av=av, tr=tr, viz=viz, hoje=hoje, D=D, fator=f, atraso=a)
    return _W


def _base(lam, K, guarda):
    """Guardas: as de hoje, ou cob_grave do mapa da fase 3 de mesmo (lam, K)."""
    W = _prepara()
    base = {k: W["hoje"][k] for k in ("cob_basico_usb", "cob_grave")}
    if guarda == "fase3":
        y3 = np.load(DADOS_FASE3 / f"v3_y_lam{lam:g}_K{_k(K)}.npy")
        r3 = W["av"].avalia(y3[0], y3[1])
        base["cob_grave"] = max(base["cob_grave"], r3["cob_grave"])
    return base


def tarefa(args):
    lam, K, s, guarda, teste = args
    arq = pasta(guarda) / f"{nome(lam, K, s)}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    from ..modelo.busca_global import BuscaGlobal
    W = _prepara()
    D = W["D"]
    base = _base(lam, K, guarda)
    bg = BuscaGlobal(W["av"], W["tr"], D["x0B"], D["x0A"], lam=lam, K=K, base=base,
                     n_cand=N_CAND, triagem="rho", viz=W["viz"])
    t0 = time.time()
    y, md, reg = bg.ils({"B": D["x0B"], "A": D["x0A"]}, semente=s,
                        chutes=1 if teste else CHUTES, tam=TAM,
                        max_passos=1 if teste else MAX_PASSOS)
    out = {"lam": lam, "K": K, "semente": s, "partida": "hoje", "guarda_grave": guarda,
           "viavel": y is not None, "base": base, "segundos": round(time.time() - t0, 1),
           "avaliacoes": bg.n_aval, "chutes": reg, "parametros":
               {"n_cand": N_CAND, "chutes": CHUTES, "tam": TAM, "max_passos": MAX_PASSOS,
                "s_min": S_MIN, "triagem": "rho"}}
    if y is not None:
        out.update({"medidas": md, "J": bg.J(md), "movidas": bg.movidas(y),
                    "yB": y["B"].tolist(), "yA": y["A"].tolist()})
    arq.write_text(json.dumps(out, default=float), encoding="utf-8")
    return out


# -------------------------------------------------------------------- busca
def tarefas(guarda, teste):
    if teste:
        return [(0.0, 40, 0, guarda, True)]
    return [(l, K, s, guarda, False) for l in LAMS for K in KS for s in SEMENTES]


def busca(workers, guarda, teste):
    p = pasta(guarda) if not teste else DADOS / "_teste_busca"
    if teste:
        globals()["pasta"] = lambda g: DADOS / "_teste_busca"
    p.mkdir(parents=True, exist_ok=True)
    ts = tarefas(guarda, teste)
    feitas = sum((p / f"{nome(l, K, s)}.json").exists() for l, K, s, _, _ in ts)
    _log(f"{len(ts)} buscas ({feitas} ja feitas), {workers} processos -> {p}")
    t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        fut = {ex.submit(tarefa, t): t for t in ts}
        for i, fu in enumerate(as_completed(fut), 1):
            r = fu.result()
            J = f"J {r['J']:.3f} vidas {r['medidas']['vidas']:.2f} cvar {r['medidas']['cvar10']:.2f} " \
                f"movidas {r['movidas']}" if r["viavel"] else "SEM SOLUCAO VIAVEL"
            _log(f"  {i}/{len(ts)} lam={r['lam']:g} K={_k(r['K'])} s{r['semente']}: {J} | "
                 f"{r['avaliacoes']} aval, {r['segundos']:.0f} s")
    _log(f"busca terminada em {(time.time() - t0) / 60:.1f} min")


# ------------------------------------------------------------------- resumo
def _referencias():
    """J das buscas da fase 3 e da fase 4 que partiram de hoje, pela mesma regua."""
    lb = json.loads((DADOS / "linha_base.json").read_text(encoding="utf-8"))
    ref = {}
    for l in lb["mapas"]:
        rot = l["rotulo"]
        if rot.startswith("fase3 ") and "p-median" not in rot:
            ref.setdefault((l["lam"], l["K"] if l["K"] is not None else None, "fase 3"), []).append(l)
        if rot.startswith("fase4 busca"):
            ref.setdefault((l["lam"], l["K"], "fase 4"), []).append(l)
    return ref


def resumo(guarda):
    p = pasta(guarda)
    res = [json.loads(a.read_text(encoding="utf-8")) for a in sorted(p.glob("*.json"))]
    ref = _referencias()
    out = []
    _log(f"{len(res)} buscas em {p}")
    print(f"{'lam':>4}{'K':>7}{'n':>4}  {'J fase 5: min / mediana / max':>32}  {'fase 3':>8}  "
          f"{'fase 4 (min-max)':>17}  {'vidas':>7}{'CVaR10':>8}")
    for lam in LAMS:
        for K in KS:
            g = [r for r in res if r["lam"] == lam and r["K"] == K and r["viavel"]]
            if not g:
                continue
            Js = np.array([r["J"] for r in g])
            best = g[int(np.argmax(Js))]
            Jf = lambda l: l["J0"] if lam == 0 else l["J1"]
            r3 = [Jf(l) for l in ref.get((lam, K, "fase 3"), [])]
            r4 = [Jf(l) for l in ref.get((lam, K, "fase 4"), [])]
            lin = {"lam": lam, "K": K, "n": len(g), "J_min": float(Js.min()),
                   "J_mediana": float(np.median(Js)), "J_max": float(Js.max()),
                   "melhor_semente": best["semente"], "melhor": best["medidas"],
                   "fase3_J": r3[0] if r3 else None,
                   "fase4_J_min": min(r4) if r4 else None, "fase4_J_max": max(r4) if r4 else None,
                   "avaliacoes_media": float(np.mean([r["avaliacoes"] for r in g])),
                   "minutos_medios": float(np.mean([r["segundos"] for r in g]) / 60)}
            out.append(lin)
            f4 = f"{min(r4):.2f}-{max(r4):.2f}" if r4 else "-"
            print(f"{lam:4g}{_k(K):>7}{len(g):4d}  {Js.min():10.2f} / {np.median(Js):6.2f} / "
                  f"{Js.max():6.2f}    {r3[0] if r3 else float('nan'):8.2f}  {f4:>17}  "
                  f"{best['medidas']['vidas']:7.2f}{best['medidas']['cvar10']:8.2f}")
    arq = DADOS / f"resumo_busca{'' if guarda == 'hoje' else '_gg_fase3'}.json"
    arq.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    _log(f"-> {arq.relative_to(DADOS.parent.parent)}")


# ------------------------------------------------------------------ simula
def simula(guarda):
    """Melhor mapa da fase 5 de cada (lam, K) contra os da fase 3 e da fase 4, na
    simulacao de eventos discretos da fase 3 (independente do hipercubo), com as
    mesmas sementes: diferenca pareada."""
    from fase3_vidas.experimentos import simula_vidas as SIM
    from fase3_vidas.experimentos import vidas as V
    from fase3_vidas.modelo import mip_vidas as MV
    from fase4_hipercubo.modelo import hc_real as HR
    f, a = V.fator()
    D = V.dados()
    tx = HR.taxas_sia()
    res = [json.loads(x.read_text(encoding="utf-8")) for x in sorted(pasta(guarda).glob("*.json"))]
    b4 = json.loads((DADOS_FASE4 / "h_busca.json").read_text(encoding="utf-8"))

    def roda(yB, yA):
        iB, iA = MV.para_indices(np.asarray(yB), np.asarray(yA))
        x = np.concatenate([iB, iA])
        return [SIM.simula(D["T"], D["pop"], x, len(iB), tx[0], tx[1], S_MIN, s,
                           fator=f, atraso=a)[0] for s in SEMENTES_SIM]

    out = {"hoje": roda(D["x0B"], D["x0A"])}
    for lam in LAMS:
        for K in KS:
            g = [r for r in res if r["lam"] == lam and r["K"] == K and r["viavel"]]
            if not g:
                continue
            best = max(g, key=lambda r: r["J"])
            chave = f"lam={lam:g} K={_k(K)}"
            ent = {"fase 5": roda(best["yB"], best["yA"])}
            y3 = DADOS_FASE3 / f"v3_y_lam{lam:g}_K{_k(K)}.npy"
            if y3.exists():
                y = np.load(y3)
                ent["fase 3"] = roda(y[0], y[1])
            g4 = [r for r in b4 if r["partida"] == "hoje" and r["lam"] == lam and r["K"] == K]
            if g4:
                r4 = max(g4, key=lambda r: r["hc"]["vidas"] + lam * r["hc"]["cvar10"])
                ent["fase 4"] = roda(r4["yB"], r4["yA"])
            out[chave] = ent
            v = {k: np.mean([m["vidas"] for m in ent[k]]) for k in ent}
            d3 = [ent["fase 5"][i]["vidas"] - ent["fase 3"][i]["vidas"]
                  for i in range(len(SEMENTES_SIM))] if "fase 3" in ent else []
            cg = {k: np.mean([m["cob_grave"] for m in ent[k]]) for k in ent}
            _log(f"{chave}: vidas simuladas " + " | ".join(f"{k} {v[k]:.2f}" for k in v) +
                 (f" | fase5-fase3 pareado {np.mean(d3):+.2f} ({min(d3):+.2f} a {max(d3):+.2f})"
                  if d3 else "") + " | cob. grave " + " ".join(f"{k} {cg[k]:.1f}" for k in cg))
    arq = DADOS / f"simulacao{'' if guarda == 'hoje' else '_gg_fase3'}.json"
    arq.write_text(json.dumps(out, default=float), encoding="utf-8")
    _log(f"-> {arq.relative_to(DADOS.parent.parent)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--etapa", choices=("busca", "resumo", "simula"), default="busca")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--guarda-grave", choices=("hoje", "fase3"), default="hoje")
    ap.add_argument("--teste", action="store_true", help="1 busca curta, grava em _teste_busca/")
    a = ap.parse_args()
    if a.etapa == "busca":
        busca(1 if a.teste else a.workers, a.guarda_grave, a.teste)
    elif a.etapa == "resumo":
        resumo(a.guarda_grave)
    else:
        simula(a.guarda_grave)


if __name__ == "__main__":
    main()
