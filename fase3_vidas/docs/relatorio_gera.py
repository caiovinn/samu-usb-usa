"""Gera relatorio_vidas.html a partir de relatorio_vidas.src.html.

    uv run python -m fase3_vidas.docs.relatorio_gera

Le dados/fase3/*.json (e dados/fase2/sp_utilizacao.json para o SIA), as
figuras de figs/fase3/ e preenche os {{CAMPOS}} do .src.html. Todo numero vem
dos arquivos de resultado; o texto interpretativo fica aqui, com os numeros
interpolados. Roda por ultimo, depois de experimentos/vidas.py e figuras.py.
Para se nao sobrar nenhum {{CAMPO}} sem valor.
"""
import base64
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from fase3_vidas.caminhos import DADOS, DADOS_FASE2, FIG
from fase3_vidas.modelo import busca as BU, mip_vidas as MV, sobrevida as SV

AQUI = Path(__file__).resolve().parent
SRC = AQUI / "relatorio_vidas.src.html"
SAIDA = AQUI / "relatorio_vidas.html"
INC_CENTRAL = 25171 * 4 / 178_879_118 * 1e5     # EuReCa TWO: CPR iniciada, 3 meses -> ano
INC_FAIXA = (0.5, 1.5)                          # +-50%: hipotese, nao medida


def le(nome, pasta=DADOS):
    return json.load(open(pasta / nome, encoding="utf-8"))


def n(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def pct(x, casas=1):
    return f"{n(x, casas)}%"


def mil(x):
    return n(x, 0)


def fig(nome):
    b = base64.b64encode((FIG / nome).read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{b}" alt="{nome}">'


def tabela(cab, linhas, dir_=(), realce=()):
    th = "".join(f'<th class="{"n" if i in dir_ else ""}">{c}</th>' for i, c in enumerate(cab))
    corpo = ""
    for k, l in enumerate(linhas):
        tds = "".join(f'<td class="{"n" if i in dir_ else ""}">{c}</td>' for i, c in enumerate(l))
        corpo += f'<tr class="{"realce" if k in realce else ""}">{tds}</tr>\n'
    return f"<thead><tr>{th}</tr></thead>\n<tbody>\n{corpo}</tbody>"


def nome_bonito(k):
    k = k.replace("fase2b central_r25", "fase 2b (com restrição)").replace("fase2b central", "fase 2b")
    k = k.replace("fase2 ", "fase 2 ").replace("lam=", "λ=").replace("vidas ", "vidas: ")
    return k.replace("K=livre", "sem limite").replace(" G=pm", " · piso p-median")


def main():
    V = {}
    cal = le("v1_calibracao.json")
    re_ = le("v2_reavaliacao.json")["configs"]
    bu = le("v3_busca.json")
    sol = bu["solucoes"]
    lim = le("v4_limite.json")
    sim = le("v5_simulacao.json")
    rob = le("v6_robustez.json")
    U = le("sp_utilizacao.json", DADOS_FASE2)
    st = pd.read_parquet(DADOS_FASE2 / "sp_setores.parquet")
    cd = pd.read_parquet(DADOS_FASE2 / "sp_candidatos.parquet")
    prod = pd.read_parquet(DADOS_FASE2 / "sp_samu_producao.parquet")

    hoje, pm = re_["hoje"], re_["p-median"]
    rec_nome = rob["minimax_arrependimento"]
    todos = {**{k: v for k, v in re_.items()},
             **{"vidas " + k: dict(v["exato"], movidas=v["movidas"], km=v["km"]) for k, v in sol.items()}}
    rec = todos[rec_nome]
    pop_total = float(st["pop"].sum())

    # ------------------------------------------------------------ campos simples
    V.update(DATA=datetime.now().strftime("%d/%m/%Y %H:%M"),
             hoje_vidas=n(hoje["vidas"]), pm_vidas=n(pm["vidas"]), rec_vidas=n(rec["vidas"]),
             rec_nome=nome_bonito(rec_nome), et_bruto=n(cal["et_grave_bruto"]),
             alvo=n(cal["alvo_grave_min"], 0), atraso=n(cal["atraso"], 0), fator=n(cal["fator"], 3),
             fator_a2=n(cal["fator_por_atraso"]["2"], 3), fator_a5=n(cal["fator_por_atraso"]["5"], 3),
             q_usb=n(U["q"]["central"]["q_usb"], 2), q_usa=n(U["q"]["central"]["q_usa"], 2),
             s5=pct(100 * SV.s(5)), s9=pct(100 * SV.s(9)), s15=pct(100 * SV.s(15)),
             tau_guarda=n(SV.TAU_GUARDA, 0),
             hoje_basico=pct(hoje["cob_basico"]), hoje_grave=pct(hoje["cob_grave"]),
             pm_grave=pct(pm["cob_grave"]),
             lams="{" + "; ".join(n(l, 1 if l % 1 else 0) for l in bu["lams"]) + "}",
             ks="{" + "; ".join("livre" if k is None else str(k) for k in bu["Ks"]) + "}",
             n_bandas=str(len(SV.BANDAS)), cap=str(BU.CAP),
             tau_min=n(min(SV.BANDAS)), tau_max=n(max(SV.BANDAS), 0), chutes=str(bu["chutes"]), tam_chute=str(bu["tam_chute"]),
             lado_km=n(lim["lado_km"], 0), n_setores=mil(len(st)), pop_total=mil(pop_total),
             n_cand=mil(len(cd)), frota=str(int(cd.n_usb.sum() + cd.n_usa.sum())),
             n_usb=str(int(cd.n_usb.sum())), n_usa=str(int(cd.n_usa.sum())),
             n_locais_hoje=str(int(((cd.n_usb + cd.n_usa) > 0).sum())),
             pref_2024=mil(U["validacao_anual"]["2024"]["prefeitura"]),
             pref_2025=mil(U["validacao_anual"]["2025"]["prefeitura"]),
             inc_central=n(INC_CENTRAL, 0), janela=f'{U["janela"][0]} a {U["janela"][1]}')

    # tamanho do MILP sem agregacao (secao 4.8): mesma regra de cortes de mip_vidas
    n_cortes = int(np.ceil(-MV.L_MIN_CORTE / MV.PASSO_CORTE)) + 1
    V.update(n_cortes=str(n_cortes), n_vars_y=mil(2 * len(cd)),
             n_restr=n(len(st) * len(SV.BANDAS) * n_cortes / 1e6, 0),
             n_linhas_L=mil(len(st) * len(SV.BANDAS) / 1e3))

    # ------------------------------------------------------------ SIA
    meses = [k for k in sorted(U["mensal"]) if U["janela"][0] <= k <= U["janela"][1]]
    tot = {c: sum(U["mensal"][k][c] for k in meses) for c in U["mensal"][meses[0]]}
    env = tot["envio_usa"] + tot["envio_usb"]
    rot = [("chamadas", "chamadas recebidas pela central"),
           ("chamadas_orient", "… resolvidas com orientação por telefone"),
           ("envio_usb", "envios de USB"), ("envio_usa", "envios de USA"),
           ("regul_multi", "regulações com acionamento de múltiplos meios"),
           ("moto", "atendimentos por motolância")]
    base_pct = {"chamadas": None, "chamadas_orient": tot["chamadas"], "envio_usb": env,
                "envio_usa": env, "regul_multi": env, "moto": None}
    linhas = []
    for c, r in rot:
        b = base_pct[c]
        linhas.append([r, mil(tot[c]), pct(100 * tot[c] / b) + (" dos envios" if b == env else " das chamadas") if b else "—"])
    V["T_SIA"] = tabela(["", "12 meses", "proporção"], linhas, dir_={1, 2})
    V["pct_usb"] = pct(100 * tot["envio_usb"] / env)
    V["pct_multi"] = pct(100 * tot["regul_multi"] / env)
    p = prod[prod.PA_UFMUN == "355030"]
    qt = pd.to_numeric(p.PA_QTDAPR, errors="coerce").fillna(0)
    V["pct_sem_cid"] = pct(100 * qt[p.PA_CIDPRI == "0000"].sum() / qt.sum(), 2)

    # ------------------------------------------------------------ 5.1 calibracao
    h = cal["hoje"]
    linhas = []
    for k, rot_ in (("livre", "trânsito livre, sem atraso"), ("calibrado", f"calibrado (f = {n(cal['fator'], 3)})"),
                    ("pesado", "pesado (1,25 × calibrado)"), ("atraso_2", "atraso de 2 min (f recalibrado)"),
                    ("atraso_5", "atraso de 5 min (f recalibrado)")):
        r = h[k]
        linhas.append([rot_, n(r["et_grave"]), n(r["et_basico"]), n(r["vidas"]), n(r["cvar10"]),
                       pct(r["cob_grave"]), pct(r["cob_basico"])])
    V["T_CALIB"] = tabela(["tempos", "E[T] grave (min)", "E[T] básico (min)", "vidas /1.000 PCR",
                           "CVaR₁₀", "USA ≤ 15 min (grave)", "USB ≤ 15 min (básico)"],
                          linhas, dir_={1, 2, 3, 4, 5, 6}, realce={1})

    # ------------------------------------------------------------ 5.2 reavaliacao
    linhas = [[nome_bonito(k), n(v["vidas"]), n(v["cvar10"]), pct(v["cob_grave"]), pct(v["cob_basico"]),
               n(v["gini_usa"], 3), str(v["movidas"])] for k, v in re_.items()]
    V["T_REAVALIA"] = tabela(["mapa", "vidas", "CVaR₁₀", "USA ≤ 15 min", "USB ≤ 15 min", "Gini USA", "movidas"],
                             linhas, dir_={1, 2, 3, 4, 5, 6})
    gini = {k: v for k, v in re_.items() if k.startswith("fase2") and v["movidas"] > 60}
    melhor_gini = max(gini.values(), key=lambda v: v["vidas"])
    V["TXT_REAVALIA"] = (
        f"<p>Medidos em vidas, os redesenhos guiados pelo Gini das fases 2 e 2b não superam o p-median "
        f"clássico: o melhor deles chega a {n(melhor_gini['vidas'])} sobreviventes por 1.000 PCR, contra "
        f"{n(pm['vidas'])} do p-median e {n(hoje['vidas'])} da rede de hoje. O Gini mais baixo "
        f"({n(min(v['gini_usa'] for v in gini.values()), 3)}) não comprou nenhuma vida a mais — "
        f"o que confirma, na métrica que importa, que igualar unidades por habitante não é o mesmo que "
        f"chegar a tempo.</p>")

    # ------------------------------------------------------------ 5.3 busca
    linhas, realce = [], set()
    for i, (k, v) in enumerate(sol.items()):
        e = v["exato"]
        linhas.append([nome_bonito(k), str(v["movidas"]), mil(v["km"]), n(e["vidas"]),
                       f'{n(v["faixa_vidas_partidas"][0])}–{n(v["faixa_vidas_partidas"][1])}',
                       n(e["cvar10"]), pct(e["cob_grave"]), pct(e["cob_basico"])])
        if "vidas " + k == rec_nome:
            realce.add(i)
    V["T_BUSCA"] = tabela(["configuração", "movidas", "km", "vidas", "partidas (degraus)", "CVaR₁₀",
                           "USA ≤ 15 min", "USB ≤ 15 min"], linhas, dir_={1, 2, 3, 4, 5, 6, 7}, realce=realce)
    V["F_FRONTEIRA"] = fig("v01_fronteira.png")
    V["F_ROBUSTEZ"] = fig("v02_robustez.png")
    V["F_MAPA"] = fig("v03_mapa.png")
    V["F_VALIDACAO"] = fig("v04_validacao.png")

    # ------------------------------------------------------------ 5.6 simulacao
    med = [m for m in sim["medias"] if m["servico"] == "central"]
    linhas = [[nome_bonito(m["config"]), n(m["an_vidas_mean"]), n(m["sim_vidas_mean"]),
               f'{n(m["sim_vidas_min"])}–{n(m["sim_vidas_max"])}', n(m["sim_vidas_pior_decil_mean"]),
               pct(100 * m["sim_frac_fila_mean"], 2)] for m in med]
    V["T_SIM"] = tabela(["mapa", "modelo", "simulado", "faixa (3 sementes)", "simulado, pior decil", "chamados em fila"],
                        linhas, dir_={1, 2, 3, 4, 5})
    dif = [m["an_vidas_mean"] - m["sim_vidas_mean"] for m in med]
    ordem_an = [m["config"] for m in sorted(med, key=lambda m: -m["an_vidas_mean"])]
    ordem_si = [m["config"] for m in sorted(med, key=lambda m: -m["sim_vidas_mean"])]
    an_ = {m["config"]: m["an_vidas_mean"] for m in med}
    si_ = {m["config"]: m["sim_vidas_mean"] for m in med}
    trocas = [abs(an_[a] - an_[b]) for a in an_ for b in an_
              if a < b and (an_[a] - an_[b]) * (si_[a] - si_[b]) < 0]
    txt_ordem = ("A ordem dos mapas é a mesma nos dois." if not trocas else
                 f"A ordem dos mapas se mantém, exceto entre mapas que o modelo separa por no máximo "
                 f"{n(max(trocas), 1)} — dentro do ruído.")
    V["TXT_SIM"] = (
        f"<p>O modelo é otimista em até {n(max(dif))} sobreviventes por 1.000 PCR "
        f"(tempo por saída central): na simulação as ocupações se correlacionam — picos ocupam vizinhas ao "
        f"mesmo tempo —, e o primeiro desfibrilador demora um pouco mais. "
        f"{txt_ordem}"
        f" Fila praticamente não ocorre.</p>")
    V["_sim"] = {m["config"]: m for m in med}
    V["_simdif"] = f"até {n(max(dif))} sobreviventes por 1.000 PCR"

    # ------------------------------------------------------------ 5.7 robustez
    pc = rob["por_config"]
    linhas = [[nome_bonito(d["config"]), n(d["arrep_max"]), pct(100 * d["arrep_rel_max"]),
               f'{n(d["vidas_min"])}–{n(d["vidas_max"])}', n(d["cvar_min"])] for d in pc]
    V["T_ROBUSTEZ"] = tabela(["mapa", "arrependimento máx.", "relativo", "vidas nos 18 cenários", "pior CVaR₁₀"],
                             linhas, dir_={1, 2, 3, 4}, realce={0})

    # ------------------------------------------------------------ 5.9 por ano
    pcr_ano = pop_total * INC_CENTRAL / 1e5
    ganho = (rec["vidas"] - hoje["vidas"]) / 1000 * pcr_ano
    ganho_pm = (rec["vidas"] - pm["vidas"]) / 1000 * pcr_ano
    V["vidas_ano_central"] = "+" + n(ganho, 0)
    V["vidas_ano_faixa"] = f"{n(ganho * INC_FAIXA[0], 0)}–{n(ganho * INC_FAIXA[1], 0)}"
    V["_ano"] = dict(pcr_ano=pcr_ano, ganho=ganho, ganho_pm=ganho_pm)
    # saidas/dia: SIA na janela de 12 meses; Prefeitura = cenario de carga baixa da robustez
    V["_sia_dia"] = sum(U["por_ano_12m"].values()) / 365.0
    V["_pref_dia"] = V["_sia_dia"] * rob["carga_baixa_fator_q"]
    V["TXT_ANO"] = (
        f"<p>Com ~{n(INC_CENTRAL, 0)} PCR com ressuscitação tentada por 100 mil habitantes por ano (EuReCa TWO) "
        f"e {mil(pop_total)} habitantes, a capital teria ~{mil(pcr_ano)} PCR por ano. A diferença entre o mapa "
        f"recomendado e a rede de hoje — {n(rec['vidas'] - hoje['vidas'])} sobreviventes por 1.000 PCR — "
        f"vale então <strong>~{n(ganho, 0)} vidas por ano</strong>; contra o p-median, {n(ganho_pm, 0)}. "
        f"A faixa de {V['vidas_ano_faixa']} usa ±50% na incidência: é uma <em>hipótese</em> — a incidência "
        f"europeia varia muito entre países, e a estimativa brasileira (~50 por 100 mil, diretriz da SBC) foi "
        f"lida só em textos que a citam. É ordem de grandeza, não previsão.</p>")

    # ------------------------------------------------------------ textos que dependem dos resultados
    from fase3_vidas.docs import textos
    V.update(textos.gera(V, cal=cal, re_=re_, sol=sol, lim=lim, sim=sim, rob=rob, rec=rec, rec_nome=rec_nome))

    txt = SRC.read_text(encoding="utf-8")
    for k, v in V.items():
        if not k.startswith("_"):
            txt = txt.replace("{{" + k + "}}", v)
    sobra = re.findall(r"\{\{[A-Za-z0-9_]+\}\}", txt)
    assert not sobra, f"campos sem valor: {sorted(set(sobra))}"
    SAIDA.write_text(txt, encoding="utf-8")
    print(f"-> {SAIDA}  ({SAIDA.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
