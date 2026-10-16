"""Fase 3 — vidas salvas. Orquestrador local, retomavel, em etapas.

    uv run python -m fase3_vidas.experimentos.vidas                  # tudo
    uv run python -m fase3_vidas.experimentos.vidas otimiza --workers 12
    uv run python -m fase3_vidas.experimentos.vidas --teste          # orcamento minimo

Etapas (cada uma pulada se a saida ja existe; apague o arquivo para refazer):
  calibra   v1_calibracao.json  fator do transito; a rede de hoje por cenario
  reavalia  v2_reavaliacao.json mapas que ja existiam (hoje, p-median, joelhos
                                das fases 2 e 2b) medidos em vidas
  otimiza   v3_busca/ + v3_busca.json  busca local exata: lam x K x semente
  limite    v4_limite.json      MILP em zonas: limite superior valido
  simula    v5_simulacao.json   finalistas na simulacao de eventos discretos
  robustez  v6_robustez.json    finalistas em 18 cenarios; arrependimento
  resumo    v_resumo.json

Um processo por tarefa, uma thread de BLAS por processo (o paralelismo e entre
tarefas). Os numeros de vidas sao sobreviventes esperados por 1.000 PCR.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse                                     # noqa: E402
import json                                         # noqa: E402
import time                                         # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402

import numpy as np                                  # noqa: E402
import pandas as pd                                 # noqa: E402

from fase3_vidas.caminhos import DADOS, DADOS_FASE2  # noqa: E402
from fase3_vidas.modelo import busca as BU          # noqa: E402
from fase3_vidas.modelo import mip_vidas as MV      # noqa: E402
from fase3_vidas.modelo import sobrevida as SV      # noqa: E402

LAMS = (0.0, 0.5, 1.0, 2.0, 4.0)       # peso do CVaR10 no objetivo
KS = (10, 20, 40, 80, None)            # limite de unidades movidas (None = livre)
SEMENTES = (0, 1, 2, 3, 4)             # ordem aleatoria da busca local
FATOR_PESADO = 1.25                    # transito pesado = 1,25 x calibrado
ATRASOS_SENS = (2.0, 5.0)              # sensibilidade do atraso (min)
SAIDAS_DIA_PREF = 350                  # Prefeitura, dez/2023 (cenario de carga baixa)
LADO_KM = 3.0                          # zonas do MILP de limite superior
TEMPO_MILP = 900.0
SERVICOS = {"baixo": 45.0, "central": 70.0, "alto": 100.0}   # = demanda_samu
SEMENTES_SIM = (1, 2, 3)
# modo --teste: variavel de ambiente, para os processos filhos (spawn no
# Windows reimporta o modulo) gravarem no mesmo lugar que o pai
TESTE = {"ativo": os.environ.get("FASE3_TESTE") == "1"}
if TESTE["ativo"]:
    DADOS = DADOS / "_teste"
    DADOS.mkdir(exist_ok=True)
BUSCA = DADOS / "v3_busca"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def salva(nome, obj):
    json.dump(obj, open(DADOS / nome, "w", encoding="utf-8"), indent=2,
              ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o))


def le(nome):
    return json.load(open(DADOS / nome, encoding="utf-8"))


# ------------------------------------------------------------------ dados
_C = {}


def dados():
    """Carrega uma vez por processo."""
    if not _C:
        st = pd.read_parquet(DADOS_FASE2 / "sp_setores.parquet")
        cd = pd.read_parquet(DADOS_FASE2 / "sp_candidatos.parquet")
        Ts = np.load(DADOS_FASE2 / "sp_tempos.npy")                  # (setores, locais)
        U = json.load(open(DADOS_FASE2 / "sp_utilizacao.json", encoding="utf-8"))
        _C.update(st=st, cd=cd, Ts=Ts, T=np.ascontiguousarray(Ts.T),
                  pop=st["pop"].values.astype(float), U=U,
                  x0B=cd.n_usb.values.astype(int), x0A=cd.n_usa.values.astype(int))
    return _C


def qs(servico="central", carga="sia"):
    """(q_usb, q_usa) do cenario. Carga baixa: as saidas por dia que a
    Prefeitura divulgou em dez/2023, em vez das do SIA (q proporcional)."""
    U = dados()["U"]
    q = U["q"][servico]
    f = 1.0
    if carga == "baixa":
        f = SAIDAS_DIA_PREF / (sum(U["por_ano_12m"].values()) / 365.0)
    return q["q_usb"] * f, q["q_usa"] * f


def indices(yB, yA):
    iB, iA = MV.para_indices(yB, yA)
    return iB, iA


def x_de(yB, yA):
    iB, iA = indices(yB, yA)
    return np.concatenate([iB, iA])


def mede(yB, yA, fator, atraso, servico="central", carga="sia"):
    D = dados()
    qb, qa = qs(servico, carga)
    iB, iA = indices(yB, yA)
    return SV.avalia_vidas(D["T"], D["pop"], iB, iA, qb, qa, fator=fator, atraso=atraso)


def mudanca(yB, yA):
    """Unidades movidas e km (linha reta, emparelhamento otimo) desde hoje."""
    from fase2_sao_paulo.modelo import mudanca as MU
    D = dados()
    cd = D["cd"]
    x = x_de(yB, yA)
    x0 = x_de(D["x0B"], D["x0A"])
    n_usb = int(D["x0B"].sum())
    Dkm = MU.matriz_km(cd.lat.values, cd.lon.values)
    return int(MU.movidas(x, x0, n_usb)), float(MU.custo(x, x0, Dkm, n_usb))


# ------------------------------------------------------------- 1. calibra
def calibra():
    D = dados()
    qb, qa = qs()
    iB, iA = indices(D["x0B"], D["x0A"])
    et = lambda f, a: SV.avalia_vidas(D["T"], D["pop"], iB, iA, qb, qa, fator=f, atraso=a)["et_grave"]
    f = SV.calibra_fator(et(0.0, SV.ATRASO), et(1.0, SV.ATRASO))
    sens = {f"{a:g}": SV.calibra_fator(et(0.0, a), et(1.0, a)) for a in ATRASOS_SENS}
    cen = {"livre": (1.0, 0.0), "calibrado": (f, SV.ATRASO),
           "pesado": (FATOR_PESADO * f, SV.ATRASO)}
    hoje = {k: mede(D["x0B"], D["x0A"], *v) for k, v in cen.items()}
    for a, fa in sens.items():
        hoje[f"atraso_{a}"] = mede(D["x0B"], D["x0A"], fa, float(a))
    out = {"fator": f, "atraso": SV.ATRASO, "alvo_grave_min": SV.ALVO_GRAVE,
           "et_grave_bruto": et(1.0, 0.0), "fator_por_atraso": sens,
           "transito": {k: list(v) for k, v in cen.items()}, "hoje": hoje,
           "fontes": ["Prefeitura de SP, 21/12/2023: saida em ~3 min nos casos "
                      "prioritarios; ~20 min para chegar nos casos mais graves",
                      "De Maio et al. 2003, doi:10.1067/mem.2003.266"]}
    salva("v1_calibracao.json", out)
    log(f"calibra: fator {f:.3f} (atraso {SV.ATRASO:g} min); hoje {hoje['calibrado']['vidas']:.1f} "
        f"vidas/1000 PCR, CVaR10 {hoje['calibrado']['cvar10']:.1f}")


def fator():
    c = le("v1_calibracao.json")
    return c["fator"], c["atraso"]


# ------------------------------------------------------------ 2. reavalia
def configs_existentes():
    """{nome: (yB, yA)} dos mapas das fases anteriores."""
    from fase2_sao_paulo.modelo.otimiza import joelho
    D = dados()
    m = len(D["cd"])
    n_usb = int(D["x0B"].sum())
    out = {"hoje": (D["x0B"], D["x0A"])}
    pm = np.load(DADOS_FASE2 / "sp_pmedian_x.npy")
    out["p-median"] = (MV.por_local(pm[:n_usb], m), MV.por_local(pm[n_usb:], m))
    for lam in ("0.1", "1"):                       # fase 2: Huff + Gini, NSGA-II
        F = pd.read_parquet(DADOS_FASE2 / f"sp_pareto_lam{lam}.parquet")
        X = np.load(DADOS_FASE2 / f"sp_pareto_x_lam{lam}.npy")
        x = X[joelho(F[["f_obj", "f_gini"]].values)]
        out[f"fase2 lam={lam}"] = (MV.por_local(x[:n_usb], m), MV.por_local(x[n_usb:], m))
    varr = DADOS_FASE2 / "varredura_q"             # fase 2b: despacho + Gini
    for c, lam in (("central", "0.1"), ("central", "1"), ("central_r25", "0.1"), ("central_r25", "1")):
        nome = f"{c}_lam{lam}_s42"
        F = pd.read_parquet(varr / f"pareto_{nome}.parquet")
        X = np.load(varr / f"pareto_x_{nome}.npy")
        ok = F.viavel.values if "viavel" in F else np.ones(len(F), bool)
        x = X[np.nonzero(ok)[0][joelho(F.loc[ok, ["f_obj", "f_gini"]].values)]]
        out[f"fase2b {c} lam={lam}"] = (MV.por_local(x[:n_usb], m), MV.por_local(x[n_usb:], m))
    return out


def reavalia():
    f, a = fator()
    D = dados()
    from fase2_sao_paulo.modelo import huff2sfca as H
    qb, qa = qs()
    th = D["U"]["theta_dados"]
    linhas = {}
    for nome, (yB, yA) in configs_existentes().items():
        r = mede(yB, yA, f, a)
        iB, iA = indices(yB, yA)
        g = H.avalia(D["T"], D["pop"], iB, iA, modelo="despacho", q_usb=qb, q_usa=qa,
                     theta=th, detalhe=False)
        mv, km = mudanca(yB, yA)
        linhas[nome] = dict(r, gini_usa=g["f_gini"], movidas=mv, km=km)
        np.save(DADOS / f"v2_y_{nome.replace(' ', '_').replace('=', '')}.npy", np.stack([yB, yA]))
    salva("v2_reavaliacao.json", {"fator": f, "atraso": a, "configs": linhas})
    for k, v in linhas.items():
        log(f"reavalia {k:28s} vidas {v['vidas']:5.1f}  CVaR10 {v['cvar10']:5.1f}  "
            f"Gini {v['gini_usa']:.3f}  movidas {v['movidas']}")


# ------------------------------------------------------------- 3. otimiza
# Guardas: "hoje" = coberturas do chamado basico (USB) e grave (USA) nao piores
# que as da rede de hoje. "pm" = a do chamado grave nao pior que a do p-median
# classico — so alcancavel sem limite K. A primeira rodada mostrou por que a
# segunda existe: so com a PCR no objetivo, a USA para o chamado grave cai ao
# piso de hoje (39,6% em 15 min), contra 53,6% no p-median.
LAMS_PM = (0.0, 1.0)
CHUTES, TAM_CHUTE = 10, 3          # busca local iterada sobre a melhor partida
_BZ = {}


def _busca():
    if not _BZ:
        from fase2_sao_paulo.experimentos.roda import vizinhos
        D = dados()
        f, a = fator()
        qb, qa = qs()
        C, G = BU.coberturas(D["Ts"], f, a)
        bz = BU.Busca(C, G, D["pop"], qb, qa, D["x0B"], D["x0A"])
        base = bz.medidas(bz.estado(D["x0B"], D["x0A"]))
        pm = bz.medidas(bz.estado(*configs_existentes()["p-median"]))
        _BZ.update(bz=bz, base={"hoje": base, "pm": dict(base, cob_grave=pm["cob_grave"])},
                   viz=vizinhos(D["cd"]))
    return _BZ["bz"], _BZ["base"]


def chave(lam, K, g="hoje"):
    return f"lam={lam:g} K={'livre' if K is None else K}" + ("" if g == "hoje" else " G=pm")


def arq_y(lam, K, g="hoje"):
    return DADOS / f"v3_y_lam{lam:g}_K{'livre' if K is None else K}{'' if g == 'hoje' else '_Gpm'}.npy"


def _nome(lam, K, s, g="hoje"):
    return f"lam{lam:g}_K{'livre' if K is None else K}_s{s}" + ("" if g == "hoje" else "_Gpm")


def _viavel(bz, md, y, K, base):
    return (md["cob_basico"] >= base["cob_basico"] - 1e-9 and
            md["cob_grave"] >= base["cob_grave"] - 1e-9 and
            (K is None or bz.movidas(y) <= K))


def tarefa_busca(args):
    lam, K, s, g = args
    arq = BUSCA / f"{_nome(lam, K, s, g)}.json"
    if arq.exists():
        return json.load(open(arq))
    bz, bases = _busca()
    base = bases[g]
    D = dados()
    t0 = time.time()
    y0 = configs_existentes()["p-median"] if s == "pm" else (D["x0B"], D["x0A"])
    st, md, hist = bz.otimiza(*y0, lam=lam, K=K, base=base, semente=0 if s == "pm" else s,
                              max_passos=1 if TESTE["ativo"] else 30)
    out = {"lam": lam, "K": K, "semente": s, "guarda": g, "degraus": md, "historico": hist,
           "viavel": _viavel(bz, md, st["y"], K, base),
           "yB": st["y"]["B"].tolist(), "yA": st["y"]["A"].tolist(),
           "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(arq, "w"), default=float)
    return out


def tarefa_refina(args):
    lam, K, g, s, yB, yA = args
    arq = BUSCA / f"refina_{_nome(lam, K, s, g)}.json"
    if arq.exists():
        return json.load(open(arq))
    bz, bases = _busca()
    t0 = time.time()
    st, md, ganhos = bz.refina(np.array(yB), np.array(yA), lam=lam, K=K, base=bases[g],
                               chutes=1 if TESTE["ativo"] else CHUTES, tam=TAM_CHUTE,
                               viz=_BZ["viz"], semente=0 if s == "pm" else int(s),
                               max_passos=1 if TESTE["ativo"] else 30)
    out = {"lam": lam, "K": K, "guarda": g, "partida": s, "degraus": md, "ganhos": ganhos,
           "viavel": _viavel(bz, md, st["y"], K, bases[g]),
           "yB": st["y"]["B"].tolist(), "yA": st["y"]["A"].tolist(),
           "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(arq, "w"), default=float)
    return out


def _roda(fn, tarefas, workers, rot):
    res = []
    with ProcessPoolExecutor(workers) as ex:
        fut = {ex.submit(fn, t): t for t in tarefas}
        for i, fu in enumerate(as_completed(fut), 1):
            res.append(fu.result())
            if i % 10 == 0 or i == len(fut):
                log(f"  {rot} {i}/{len(fut)}")
    return res


def otimiza(workers):
    BUSCA.mkdir(exist_ok=True)
    tarefas = [(l, K, s, "hoje") for l in LAMS for K in KS for s in SEMENTES]
    tarefas += [(l, None, "pm", "hoje") for l in LAMS]
    tarefas += [(l, None, "pm", "pm") for l in LAMS_PM]
    if TESTE["ativo"]:
        tarefas = [(0.0, 20, 0, "hoje")]
    log(f"otimiza: {len(tarefas)} buscas, {workers} processos")
    res = _roda(tarefa_busca, tarefas, workers, "buscas")

    grupos = {}
    for r in res:
        grupos.setdefault((r["lam"], r["K"], r["guarda"]), []).append(r)
    J = lambda r: r["degraus"]["vidas"] + r["lam"] * r["degraus"]["cvar10"]
    melhores = {k: max([r for r in rs if r["viavel"]], key=J) for k, rs in grupos.items()
                if any(r["viavel"] for r in rs)}
    log(f"otimiza: refinando {len(melhores)} melhores partidas ({CHUTES} chutes de {TAM_CHUTE})")
    ref = _roda(tarefa_refina, [(l, K, g, b["semente"], b["yB"], b["yA"])
                                for (l, K, g), b in melhores.items()], workers, "refinos")
    ref = {(r["lam"], r["K"], r["guarda"]): r for r in ref}

    f, a = fator()
    resumo = {}
    for (lam, K, g), rs in sorted(grupos.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1] or 999)):
        if (lam, K, g) not in ref:
            continue
        rf, b = ref[(lam, K, g)], melhores[(lam, K, g)]
        yB, yA = np.array(rf["yB"]), np.array(rf["yA"])
        mv, km = mudanca(yB, yA)
        ok = [r for r in rs if r["viavel"]]
        resumo[chave(lam, K, g)] = {
            "lam": lam, "K": K, "guarda": g, "melhor_partida": b["semente"],
            "exato": mede(yB, yA, f, a), "movidas": mv, "km": km, "viavel": rf["viavel"],
            "degraus_local": b["degraus"], "degraus_refinado": rf["degraus"],
            "ganho_refino_vidas": 1000 * (rf["degraus"]["vidas"] - b["degraus"]["vidas"]),
            "faixa_vidas_partidas": [1000 * min(r["degraus"]["vidas"] for r in ok),
                                     1000 * max(r["degraus"]["vidas"] for r in ok)],
            "faixa_cvar10_partidas": [1000 * min(r["degraus"]["cvar10"] for r in ok),
                                      1000 * max(r["degraus"]["cvar10"] for r in ok)],
            "partidas_inviaveis": [r["semente"] for r in rs if not r["viavel"]],
            "segundos": float(sum(r["segundos"] for r in rs) + rf["segundos"]),
        }
        np.save(arq_y(lam, K, g), np.stack([yB, yA]))
    bz, bases = _busca()
    salva("v3_busca.json", {"fator": f, "atraso": a, "lams": LAMS, "lams_pm": LAMS_PM, "Ks": KS,
                            "sementes": SEMENTES, "chutes": CHUTES, "tam_chute": TAM_CHUTE,
                            "guardas": {k: {kk: 100 * vv for kk, vv in v.items()
                                            if kk.startswith("cob")} for k, v in bases.items()},
                            "solucoes": resumo})
    for k, v in resumo.items():
        log(f"  {k:22s} vidas {v['exato']['vidas']:5.1f}  CVaR10 {v['exato']['cvar10']:5.1f}  "
            f"grave {v['exato']['cob_grave']:4.1f}%  movidas {v['movidas']:3d}  "
            f"refino +{v['ganho_refino_vidas']:.2f}  partidas {v['faixa_vidas_partidas'][0]:.1f}-"
            f"{v['faixa_vidas_partidas'][1]:.1f}")


# -------------------------------------------------------------- 4. limite
def tarefa_limite(K):
    D = dados()
    f, a = fator()
    qb, qa = qs()
    st = D["st"]
    z = MV.zonas(st.lat.values, st.lon.values, LADO_KM)
    M = MV.Modelo.de_setores(D["Ts"], z, D["pop"], D["x0B"], D["x0A"], qb, qa,
                             fator=f, atraso=a)
    bz, bases = _busca()
    base = bases["hoje"]
    # guardas com o mesmo piso da busca; nas zonas a cobertura e superestimada
    # (Jensen), entao a restricao fica mais folgada: continua relaxacao
    r = M.resolve(K=K, base_basico=base["cob_basico"], base_grave=base["cob_grave"],
                  tempo_max=30 if TESTE["ativo"] else TEMPO_MILP)
    out = {"K": K, "zonas": M.nz, "lado_km": LADO_KM,
           **{k: v for k, v in r.items() if k not in ("yB", "yA")}}
    if "yB" in r:
        out["exato_da_solucao_zonas"] = mede(r["yB"], r["yA"], f, a)
    return out


def limite(workers):
    Ks = [20] if TESTE["ativo"] else [None]
    with ProcessPoolExecutor(min(workers, len(Ks))) as ex:
        res = list(ex.map(tarefa_limite, Ks))
    busca = le("v3_busca.json")["solucoes"]
    for r in res:
        k = chave(0.0, r["K"])
        if k in busca and "limite" in r:
            # comparacao no MESMO objetivo (degraus): busca refinada
            v = busca[k]["degraus_refinado"]["vidas"]
            r["busca_degraus"] = v
            r["folga_max_rel"] = (r["limite"] - v) / v
        log(f"limite K={r['K']}: limite {1000*r.get('limite', float('nan')):.2f} "
            f"busca {1000*r.get('busca_degraus', float('nan')):.2f} "
            f"({r.get('segundos')} s, status {r['status']})")
    salva("v4_limite.json", {"lado_km": LADO_KM, "tempo_max_s": TEMPO_MILP, "por_K": res,
                             "nota": "limite = limite dual do MILP em zonas com cobertura "
                                     "fracionaria; vale como teto do otimo por setor "
                                     "(1 - e^L concava: a media por zona so superestima)"})


# -------------------------------------------------------------- finalistas
def finalistas():
    """{nome: (yB, yA)}: o que ja existia + as solucoes da busca."""
    out = {k: v for k, v in configs_existentes().items()
           if k in ("hoje", "p-median", "fase2 lam=0.1", "fase2b central lam=0.1",
                    "fase2b central_r25 lam=0.1")}
    for lam, K, g in ((0.0, 20, "hoje"), (0.0, 40, "hoje"), (1.0, 40, "hoje"), (0.0, None, "hoje"),
                      (1.0, None, "hoje"), (4.0, None, "hoje"), (0.0, None, "pm"), (1.0, None, "pm")):
        arq = arq_y(lam, K, g)
        if arq.exists():
            y = np.load(arq)
            out["vidas " + chave(lam, K, g)] = (y[0], y[1])
    return out


# -------------------------------------------------------------- 5. simula
def tarefa_sim(args):
    from fase3_vidas.experimentos import simula_vidas as SI
    nome, yB, yA, serv, sem = args
    D = dados()
    f, a = fator()
    U = D["U"]
    taxas = (U["por_ano_12m"]["usa"] / 8760.0, U["por_ano_12m"]["usb"] / 8760.0)
    x = x_de(yB, yA)
    dias = 30 if TESTE["ativo"] else SI.DIAS
    r, soma, cnt = SI.simula(D["T"], D["pop"], x, int(D["x0B"].sum()), *taxas,
                             SERVICOS[serv], sem, fator=f, atraso=a, dias=dias)
    an = mede(yB, yA, f, a, servico=serv)
    # pior decil definido pelo modelo; sobrevida simulada nesses setores
    iB, iA = indices(yB, yA)
    S = SV.avalia_vidas(D["T"], D["pop"], iB, iA, *qs(serv), fator=f, atraso=a, detalhe=True)["S"]
    o = np.argsort(S)
    pior = np.zeros(len(S), bool)
    pior[o[np.cumsum(D["pop"][o]) / D["pop"].sum() <= SV.ALFA_CVAR]] = True
    r["vidas_pior_decil"] = float(1000 * soma[pior].sum() / max(cnt[pior].sum(), 1))
    return {"config": nome, "servico": serv, "semente": sem, "sim": r,
            "analitico": {k: v for k, v in an.items() if k != "S"}}


def simula(workers):
    fin = finalistas()
    tarefas = [(n, y[0], y[1], s, sem) for n, y in fin.items() for s in SERVICOS for sem in SEMENTES_SIM]
    if TESTE["ativo"]:
        tarefas = tarefas[:2]
    log(f"simula: {len(tarefas)} rodadas, {workers} processos")
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(tarefa_sim, tarefas))
    linhas = []
    for r in res:
        l = {"config": r["config"], "servico": r["servico"], "semente": r["semente"]}
        l.update({f"sim_{k}": v for k, v in r["sim"].items()})
        l.update({f"an_{k}": v for k, v in r["analitico"].items()})
        linhas.append(l)
    df = pd.DataFrame(linhas)
    med = df.groupby(["config", "servico"], sort=False).agg(["mean", "min", "max"])
    med.columns = [f"{a}_{b}" for a, b in med.columns]
    med = med.reset_index()
    salva("v5_simulacao.json", {"rodadas": linhas, "medias": med.to_dict("records"),
                                "sementes": SEMENTES_SIM, "servicos": SERVICOS})
    c = df[df.servico == "central"].groupby("config", sort=False).mean(numeric_only=True)
    for k, v in c.iterrows():
        log(f"  {k:28s} vidas modelo {v['an_vidas']:5.1f}  simulado {v['sim_vidas']:5.1f}  "
            f"pior decil sim {v['sim_vidas_pior_decil']:5.1f}  fila {100*v['sim_frac_fila']:.2f}%")


# ------------------------------------------------------------ 6. robustez
def robustez():
    f, a = fator()
    fin = finalistas()
    cen = [(s, tn, c) for s in SERVICOS for tn in ("livre", "calibrado", "pesado")
           for c in ("sia", "baixa")]
    fat = {"livre": (1.0, a), "calibrado": (f, a), "pesado": (FATOR_PESADO * f, a)}
    tab = []
    for s, tn, c in cen:
        for nome, (yB, yA) in fin.items():
            r = mede(yB, yA, *fat[tn], servico=s, carga=c)
            tab.append({"servico": s, "transito": tn, "carga": c, "config": nome,
                        "vidas": r["vidas"], "cvar10": r["cvar10"],
                        "cob_grave": r["cob_grave"], "cob_basico": r["cob_basico"]})
    df = pd.DataFrame(tab)
    df["melhor"] = df.groupby(["servico", "transito", "carga"]).vidas.transform("max")
    df["arrep"] = df.melhor - df.vidas
    df["arrep_rel"] = df.arrep / df.melhor
    agg = df.groupby("config").agg(arrep_max=("arrep", "max"), arrep_rel_max=("arrep_rel", "max"),
                                   vidas_min=("vidas", "min"), vidas_max=("vidas", "max"),
                                   cvar_min=("cvar10", "min")).sort_values("arrep_max")
    escolha = agg.index[0]
    salva("v6_robustez.json", {"cenarios": [list(x) for x in cen], "tabela": tab,
                               "por_config": agg.reset_index().to_dict("records"),
                               "minimax_arrependimento": escolha,
                               "carga_baixa_fator_q": SAIDAS_DIA_PREF / (sum(dados()["U"]["por_ano_12m"].values()) / 365.0)})
    log(f"robustez: escolha por minimax-arrependimento = {escolha}")
    for k, v in agg.iterrows():
        log(f"  {k:28s} arrependimento max {v.arrep_max:5.2f} ({100*v.arrep_rel_max:4.1f}%)  "
            f"vidas {v.vidas_min:5.1f}-{v.vidas_max:5.1f}")


# -------------------------------------------------------------- 7. classes
# Teste pedido: SEM a PCR. So as duas classes observadas no SIA — chamado grave
# (so USA) e chamado basico (USB primeiro) —, e o objetivo e a fracao dos
# chamados alcancados em ate TAU_GUARDA min:
#     th * P(USA livre a <= tau) + (1 - th) * P(USB livre a <= tau)
# th = fracao de envios de USA no SIA ("chamadas") ou 0,5 ("igual": o chamado
# grave pesa como o basico, como proxy de gravidade). Mesmas guardas (nenhuma
# classe pior que hoje) e mesmos limites K. A sobrevida a PCR desses mapas e
# so medida depois, para comparar.
PESOS_CLASSE = ("chamadas", "igual")
KS_CLASSE = (20, 40, None)
SEMENTES_CLASSE = (0, 1, 2)
_BC = {}


def _busca_classe(peso):
    if peso not in _BC:
        from fase2_sao_paulo.experimentos.roda import vizinhos
        D = dados()
        f, a = fator()
        qb, qa = qs()
        th = D["U"]["theta_dados"] if peso == "chamadas" else 0.5
        C, G = BU.coberturas(D["Ts"], f, a, bandas=(SV.TAU_GUARDA, SV.TAU_GUARDA))
        bz = BU.Busca(C, G, D["pop"], qb, qa, D["x0B"], D["x0A"], d=(th, 1 - th),
                      tipos=((0, 1), (1, 0)))
        _BC[peso] = (bz, bz.medidas(bz.estado(D["x0B"], D["x0A"])), th, vizinhos(D["cd"]))
    return _BC[peso]


def tarefa_classe(args):
    peso, K, s = args
    arq = BUSCA / f"classe_{peso}_K{'livre' if K is None else K}_s{s}.json"
    if arq.exists():
        return json.load(open(arq))
    bz, base, th, viz = _busca_classe(peso)
    D = dados()
    t0 = time.time()
    y0 = configs_existentes()["p-median"] if s == "pm" else (D["x0B"], D["x0A"])
    st, md, ganhos = bz.refina(*y0, K=K, base=base, chutes=1 if TESTE["ativo"] else CHUTES,
                               tam=TAM_CHUTE, viz=viz, semente=0 if s == "pm" else s,
                               max_passos=1 if TESTE["ativo"] else 30)
    out = {"peso": peso, "theta": th, "K": K, "semente": s, "objetivo": md, "ganhos": ganhos,
           "viavel": _viavel(bz, md, st["y"], K, base),
           "yB": st["y"]["B"].tolist(), "yA": st["y"]["A"].tolist(),
           "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(arq, "w"), default=float)
    return out


def classes(workers):
    BUSCA.mkdir(exist_ok=True)
    tarefas = [(p, K, s) for p in PESOS_CLASSE for K in KS_CLASSE for s in SEMENTES_CLASSE]
    tarefas += [(p, None, "pm") for p in PESOS_CLASSE]
    if TESTE["ativo"]:
        tarefas = [("chamadas", 20, 0)]
    log(f"classes: {len(tarefas)} buscas (sem PCR no objetivo), {workers} processos")
    res = _roda(tarefa_classe, tarefas, workers, "classes")
    f, a = fator()
    D = dados()
    th_dados = D["U"]["theta_dados"]

    def objetivo(r, th):
        return th * r["cob_grave"] + (1 - th) * r["cob_basico"]

    refs = {k: v for k, v in configs_existentes().items() if k in ("hoje", "p-median")}
    out = {"tau_min": SV.TAU_GUARDA, "theta_dados": th_dados, "Ks": KS_CLASSE,
           "sementes": SEMENTES_CLASSE, "referencias": {}, "solucoes": {}}
    for nome, (yB, yA) in refs.items():
        r = mede(yB, yA, f, a)
        out["referencias"][nome] = dict(r, obj_chamadas=objetivo(r, th_dados), obj_igual=objetivo(r, 0.5))
    for p in PESOS_CLASSE:
        for K in KS_CLASSE:
            rs = [r for r in res if r["peso"] == p and r["K"] == K and r["viavel"]]
            if not rs:
                continue
            b = max(rs, key=lambda r: r["objetivo"]["vidas"])
            yB, yA = np.array(b["yB"]), np.array(b["yA"])
            r = mede(yB, yA, f, a)
            mv, km = mudanca(yB, yA)
            k = f"classes {p} K={'livre' if K is None else K}"
            out["solucoes"][k] = dict(r, obj_chamadas=objetivo(r, th_dados), obj_igual=objetivo(r, 0.5),
                                      peso=p, K=K, movidas=mv, km=km, melhor_partida=b["semente"],
                                      faixa_obj_partidas=[100 * min(x["objetivo"]["vidas"] for x in rs),
                                                          100 * max(x["objetivo"]["vidas"] for x in rs)])
            np.save(DADOS / f"v7_y_{p}_K{'livre' if K is None else K}.npy", np.stack([yB, yA]))
    salva("v7_classes.json", out)
    for k, v in {**out["referencias"], **out["solucoes"]}.items():
        log(f"  {k:28s} grave {v['cob_grave']:5.1f}%  basico {v['cob_basico']:5.1f}%  "
            f"obj(chamadas) {v['obj_chamadas']:5.1f}  obj(igual) {v['obj_igual']:5.1f}  "
            f"PCR {v['vidas']:5.1f}  CVaR10 {v['cvar10']:5.1f}  movidas {v.get('movidas', 0)}")



# --------------------------------------------------------------- resumo
def resumo():
    out = {"calibracao": le("v1_calibracao.json"),
           "reavaliacao": le("v2_reavaliacao.json")["configs"],
           "busca": le("v3_busca.json")["solucoes"]}
    for nome, arq in (("limite", "v4_limite.json"), ("simulacao", "v5_simulacao.json"),
                      ("robustez", "v6_robustez.json"), ("classes", "v7_classes.json")):
        if (DADOS / arq).exists():
            d = le(arq)
            out[nome] = {k: v for k, v in d.items() if k not in ("rodadas", "tabela")}
    salva("v_resumo.json", out)
    log("resumo -> dados/fase3/v_resumo.json")


ETAPAS = {"calibra": ("v1_calibracao.json", calibra), "reavalia": ("v2_reavaliacao.json", reavalia),
          "otimiza": ("v3_busca.json", otimiza), "limite": ("v4_limite.json", limite),
          "simula": ("v5_simulacao.json", simula), "robustez": ("v6_robustez.json", robustez),
          "classes": ("v7_classes.json", classes),
          "resumo": ("v_resumo.json", resumo)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("etapas", nargs="*", default=list(ETAPAS))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--teste", action="store_true", help="orcamento minimo, saidas em dados/fase3/_teste")
    ap.add_argument("--refaz", action="store_true", help="refaz as etapas pedidas mesmo com saida")
    a = ap.parse_args()
    if a.teste and not TESTE["ativo"]:
        # relanca ja no modo teste: os filhos herdam a variavel de ambiente
        import subprocess
        import sys
        amb = dict(os.environ, FASE3_TESTE="1")
        raise SystemExit(subprocess.call([sys.executable, "-m", "fase3_vidas.experimentos.vidas",
                                          *sys.argv[1:]], env=amb))
    for e in a.etapas:
        arq, fn = ETAPAS[e]
        if (DADOS / arq).exists() and not a.refaz:
            log(f"{e}: ja existe {arq}, pulando")
            continue
        t0 = time.time()
        log(f"== {e}")
        fn(a.workers) if e in ("otimiza", "limite", "simula", "classes") else fn()
        log(f"{e}: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
