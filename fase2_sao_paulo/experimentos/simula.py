"""Validacao por simulacao de eventos discretos — o modelo despacho acerta?

    uv run python -m fase2_sao_paulo.experimentos.simula

O modelo despacho (huff2sfca.despacho) tem duas simplificacoes:
  - ocupacoes INDEPENDENTES entre unidades (Daskin), quando na vida real elas
    se correlacionam: um pico de chamados ocupa varias vizinhas ao mesmo tempo;
  - no pool basico, USB e USA disputam o chamado em pe de igualdade.

Aqui a cidade e simulada chamado a chamado, sem nenhuma das duas:
  - chamados chegam como processo de Poisson, com as taxas do SIA (12 meses),
    em setores sorteados com probabilidade proporcional a populacao;
  - chamado grave -> USA livre mais proxima; chamado basico -> USB livre mais
    proxima e, se nenhuma estiver livre, USA livre mais proxima (o regulador
    preserva a USA);
  - todas ocupadas -> o chamado espera a primeira unidade elegivel a liberar;
  - a unidade fica ocupada por: tempo ate o local + R, com R ~ Gamma(2) de
    media (tempo de servico - tempo medio ate o local).

Para cada configuracao (atual, p-median, joelhos da varredura) e cada tempo
de servico, compara o simulado com o que o modelo analitico preve: tempo
esperado, ocupacao, chance de o mais proximo atender e a cobertura em 10 min
do pior decil. Grava dados/fase2/sp_simulacao.json e figs/fase2/sp_07_validacao.png.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json                                         # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np                                  # noqa: E402
import pandas as pd                                 # noqa: E402

from fase2_sao_paulo.caminhos import DADOS, FIG     # noqa: E402

DIAS, AQUEC = 365, 14          # dias medidos e de aquecimento (descartados)
SEMENTES = (1, 2, 3)
T_IDA = 6.0                    # min; ordem de grandeza do tempo ate o local
TAU = 10.0
VARR = DADOS / "varredura_q"
JOELHOS = (("central", 0.1), ("central", 1.0),
           ("central_r25", 0.1), ("central_r25", 1.0))


def configuracoes(cd):
    from fase2_sao_paulo.modelo.otimiza import joelho
    x0 = np.concatenate([np.repeat(cd.id.values, cd.n_usb.values),
                         np.repeat(cd.id.values, cd.n_usa.values)])
    out = {"atual": x0, "p-median": np.load(DADOS / "sp_pmedian_x.npy")}
    for c, lam in JOELHOS:
        nome = f"{c}_lam{lam:g}_s42"
        F = pd.read_parquet(VARR / f"pareto_{nome}.parquet")
        X = np.load(VARR / f"pareto_x_{nome}.npy")
        ok = F.viavel.values if "viavel" in F else np.ones(len(F), bool)
        i = np.nonzero(ok)[0][joelho(F.loc[ok, ["f_obj", "f_gini"]].values)]
        out[f"{c} lam={lam:g}"] = X[i]
    return out


def simula(T, pop, x, n_usb, taxa_usa, taxa_usb, s_min, semente):
    """Uma rodada. taxas em chamados/hora. Devolve dict de metricas + por setor."""
    rng = np.random.default_rng(semente)
    n = len(x)
    usb, usa = np.arange(n_usb), np.arange(n_usb, n)
    tu = T[x]                                         # (unidades, setores)
    ord_usb = np.argsort(tu[usb], axis=0).T           # (setores, n_usb)
    ord_usa = np.argsort(tu[usa], axis=0).T + n_usb
    horas = 24.0 * (DIAS + AQUEC)
    lam = taxa_usa + taxa_usb
    k = rng.poisson(lam * horas)
    chegada = np.sort(rng.uniform(0, horas * 60, k))  # minutos
    grave = rng.random(k) < taxa_usa / lam
    setor = rng.choice(len(pop), size=k, p=pop / pop.sum())
    resto = rng.gamma(2.0, (s_min - T_IDA) / 2.0, k)

    livre_em = np.zeros(n)
    ocupado = np.zeros(n)                             # minutos ocupados medidos
    t0 = AQUEC * 24 * 60
    resp = np.empty(k); mais_prox = np.zeros(k, bool); espera = np.zeros(k, bool)
    for c in range(k):
        agora, i = chegada[c], setor[c]
        listas = (ord_usa[i],) if grave[c] else (ord_usb[i], ord_usa[i])
        u = -1
        for lst in listas:
            ok = livre_em[lst] <= agora
            if ok.any():
                u = lst[np.argmax(ok)]
                # mesmo local do mais proximo conta (local com 2 unidades)
                mais_prox[c] = lst is listas[0] and tu[u, i] <= tu[lst[0], i]
                break
        inicio = agora
        if u < 0:                                     # todas ocupadas: fila
            eleg = np.concatenate(listas)
            u = eleg[np.argmin(livre_em[eleg])]
            inicio = livre_em[u]
            espera[c] = True
        ida = tu[u, i]
        resp[c] = inicio - agora + ida
        fim = inicio + ida + resto[c]
        if fim > t0:
            ocupado[u] += fim - max(inicio, t0)
        livre_em[u] = fim
    med = chegada >= t0
    dur = DIAS * 24 * 60
    g, b = med & grave, med & ~grave
    # cobertura em TAU por setor, so chamados graves (estimada por contagem)
    cnt = np.bincount(setor[g], minlength=len(pop))
    ok10 = np.bincount(setor[g], weights=(resp[g] <= TAU), minlength=len(pop))
    return {
        "et_grave": float(resp[g].mean()), "et_basico": float(resp[b].mean()),
        "f_tempo": float(resp[med].mean()),
        "q_usb": float(ocupado[usb].sum() / (dur * len(usb))),
        "q_usa": float(ocupado[usa].sum() / (dur * len(usa))),
        "p_mais_prox_grave": float(mais_prox[g].mean()),
        "frac_fila": float(espera[med].mean()),
        "cob10_grave": float(100 * (resp[g] <= TAU).mean()),
    }, cnt, ok10


def analitico(T, pop, x, n_usb, q, theta):
    from fase2_sao_paulo.modelo import huff2sfca as H
    r = H.avalia(T, pop, x[:n_usb], x[n_usb:], modelo="despacho",
                 q_usb=q["q_usb"], q_usa=q["q_usa"], theta=theta)
    loc, inv = np.unique(x[n_usb:], return_inverse=True)
    P = H.despacho(T[loc], H._log_ocup(loc, inv, np.full(len(inv), q["q_usa"])))
    c = H.cobertura(T[loc], P, TAU)
    o = np.argsort(c)
    pior = np.zeros(len(pop), bool)
    pior[o[np.cumsum(pop[o]) / pop.sum() <= 0.10]] = True
    w = pop / pop.sum()
    return {"f_tempo": r["f_tempo"], "et_grave": float(np.sum(w * r["T_av"])),
            "cob10_grave": r["cob_usa_10"], "cob10_p10": r["cob_usa_10_p10"],
            "p_mais_prox_grave": float(np.sum(w * P.max(axis=0)))}, pior


def tarefa(args):
    nome, x, s_nome, s_min, q, semente, taxas, theta = args
    from fase2_sao_paulo.experimentos import roda as R
    st, cd, T = R.carrega()
    pop = st["pop"].values.astype(float)
    n_usb = int(cd.n_usb.sum())
    sim, cnt, ok10 = simula(T, pop, x, n_usb, *taxas, s_min, semente)
    an, pior = analitico(T, pop, x, n_usb, q, theta)
    sim["cob10_p10"] = float(100 * ok10[pior].sum() / max(cnt[pior].sum(), 1))
    return {"config": nome, "servico": s_nome, "semente": semente,
            "sim": sim, "analitico": an}


def main():
    from fase2_sao_paulo.experimentos import roda as R
    u = json.load(open(DADOS / "sp_utilizacao.json"))
    taxas = (u["por_ano_12m"]["usa"] / 8760.0, u["por_ano_12m"]["usb"] / 8760.0)
    theta = u["theta_dados"]
    _, cd, _ = R.carrega()
    confs = configuracoes(cd)
    from fase2_sao_paulo.experimentos.demanda_samu import TEMPOS_SERVICO_MIN
    tarefas = [(n, x, sn, smin, u["q"][sn], s, taxas, theta)
               for n, x in confs.items() for sn, smin in TEMPOS_SERVICO_MIN.items()
               for s in SEMENTES]
    with ProcessPoolExecutor(12) as ex:
        res = list(ex.map(tarefa, tarefas))

    linhas = []
    for r in res:
        linha = {"config": r["config"], "servico": r["servico"], "semente": r["semente"]}
        linha.update({f"sim_{k}": v for k, v in r["sim"].items()})
        linha.update({f"an_{k}": v for k, v in r["analitico"].items()})
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    med = df.groupby(["config", "servico"], sort=False).mean(numeric_only=True).reset_index()
    json.dump({"taxas_por_hora": {"usa": taxas[0], "usb": taxas[1]}, "theta": theta,
               "dias": DIAS, "sementes": list(SEMENTES), "rodadas": linhas,
               "medias": med.to_dict("records")},
              open(DADOS / "sp_simulacao.json", "w"), indent=2, default=float)
    figura(med)
    c = med[med.servico == "central"]
    with pd.option_context("display.width", 220, "display.precision", 2):
        print(c[["config", "an_f_tempo", "sim_f_tempo", "an_et_grave", "sim_et_grave",
                 "sim_q_usb", "sim_q_usa", "an_p_mais_prox_grave", "sim_p_mais_prox_grave",
                 "an_cob10_p10", "sim_cob10_p10", "sim_frac_fila"]].to_string(index=False))
    print("-> dados/fase2/sp_simulacao.json, figs/fase2/sp_07_validacao.png")


def figura(med):
    """Previsto (analitico) x simulado: se o modelo acerta, os pontos caem na
    diagonal. Dois paineis porque as duas metricas tem unidades diferentes."""
    from fase2_sao_paulo.experimentos import figuras as FG
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.8))
    for ax, (a, s, rot) in zip(axs, (("an_et_grave", "sim_et_grave",
                                      "tempo esperado, chamado grave (min)"),
                                     ("an_cob10_p10", "sim_cob10_p10",
                                      "pior decil: USA em ate 10 min (%)"))):
        lo = min(med[a].min(), med[s].min()); hi = max(med[a].max(), med[s].max())
        pad = 0.06 * (hi - lo + 1e-9)
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], "-", color="#c3c2b7", lw=1, zorder=1)
        ax.scatter(med[a], med[s], s=36, color=FG.C_USB, edgecolor="#fcfcfb", lw=1.5, zorder=3)
        ax.set_xlabel("previsto pelo modelo", color=FG.TINTA2, fontsize=9)
        ax.set_ylabel("simulado", color=FG.TINTA2, fontsize=9)
        ax.set_title(rot, loc="left", fontsize=10, color=FG.TINTA)
        for e in ("top", "right"):
            ax.spines[e].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "sp_07_validacao.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
