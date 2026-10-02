"""Producao do SAMU-SP no SIA -> theta e ocupacao q de USB e USA.

    uv run python -m fase2_sao_paulo.experimentos.demanda_samu

Le dados/fase2/sp_samu_producao.parquet (coleta/pull_sia_samu.py) e grava
dados/fase2/sp_utilizacao.json. O que sai daqui substitui dois parametros
arbitrados do modelo:

  theta   fracao dos envios que e de USA (era 0,10 por hipotese)
  q       ocupacao de cada unidade = carga oferecida / unidades, com
          carga = (envios + transferencias por hora) x tempo de servico

O tempo de servico (saida da base -> unidade livre de novo) NAO esta no SIA:
e o unico insumo que continua hipotese, varrido em TEMPOS_SERVICO_MIN.

Codigos SIGTAP do subgrupo 03.01.03 (conferidos na Tabela Unificada 2026-07,
fase2_sao_paulo/_raw/sigtap/tb_procedimento.txt).
"""
import json

import numpy as np
import pandas as pd

from fase2_sao_paulo.caminhos import DADOS

MUN = "355030"
CODIGOS = {
    "0301030120": "envio_usa",       # envio de USA (e/ou embarcacao, aeromedico)
    "0301030138": "envio_usb",       # envio de USB (e/ou embarcacao, motolancia)
    "0301030090": "atend_usa",       # atendimento pre-hospitalar pela USA
    "0301030103": "atend_usb",       # atendimento pre-hospitalar pela USB
    "0301030170": "transf_usa",      # transporte inter-hospitalar pela USA
    "0301030189": "transf_usb",      # transporte inter-hospitalar pela USB
    "0301030197": "moto",            # atendimento por motolancia
    "0301030014": "chamadas",        # chamadas recebidas pela central
    "0301030146": "chamadas_orient", # chamadas com orientacao
    "0301030111": "regul_multi",     # regulacao com multiplos meios
}
TEMPOS_SERVICO_MIN = {"baixo": 45.0, "central": 70.0, "alto": 100.0}
PREFEITURA = {2024: 314_089, 2025: 355_806}   # atendimentos presenciais, SMS-SP
N_PROVISORIO = 3   # ultimos meses de competencia ainda recebem registros tardios


def carrega():
    df = pd.read_parquet(DADOS / "sp_samu_producao.parquet")
    df = df[df.PA_UFMUN == MUN].copy()
    df["cat"] = df.PA_PROC_ID.map(CODIGOS).fillna("outros")
    for c in ("PA_QTDAPR", "PA_QTDPRO"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    df["cmp"] = pd.PeriodIndex(df.PA_CMP.str[:4] + "-" + df.PA_CMP.str[4:6], freq="M")
    return df


def serie_mensal(df):
    s = df.pivot_table(index="cmp", columns="cat", values="PA_QTDAPR",
                       aggfunc="sum", fill_value=0).sort_index()
    for c in set(CODIGOS.values()) - set(s.columns):
        s[c] = 0
    # erro de faturamento: 2024-02 tem 216.626 envios de USB contra 19.356
    # atendimentos (~10x o normal). Envio > 3x atendimento e lancamento
    # errado: troca pelo atendimento do mesmo mes e registra
    anomalias = []
    for mod in ("usb", "usa"):
        e, a = s[f"envio_{mod}"], s[f"atend_{mod}"]
        ruim = e > 3 * a.clip(lower=1)
        for p in s.index[ruim]:
            anomalias.append({"mes": str(p), "codigo": f"envio_{mod}",
                              "valor": int(e[p]), "trocado_por": int(a[p])})
        s.loc[ruim, f"envio_{mod}"] = a[ruim]
    s.attrs["anomalias"] = anomalias
    return s


def por_cnes(df, cd):
    """Volume por estabelecimento que fatura, cruzado com as bases atuais."""
    v = df.pivot_table(index="PA_CODUNI", columns="cat", values="PA_QTDAPR",
                       aggfunc="sum", fill_value=0)
    cd = cd.assign(cnes=cd.codigo_cnes.astype(str).str.zfill(7))
    v = v.join(cd.set_index("cnes")[["id", "nome", "tipo", "n_usb", "n_usa"]],
               how="left")
    return v


def figura(s, fonte, provisorios):
    """Carga mensal (envios + transferencias) por modalidade. Duas escalas muito
    diferentes (USB ~10x USA): dois paineis com o eixo x comum, nunca dois
    eixos y no mesmo grafico."""
    from fase2_sao_paulo.experimentos import figuras as FG   # estilo do projeto
    import matplotlib.pyplot as plt
    base = "envio" if fonte == "envio" else "atend"
    x = s.index.to_timestamp()
    fig, axs = plt.subplots(2, 1, figsize=(8, 4.6), sharex=True)
    for ax, mod, cor in ((axs[0], "usb", FG.C_USB), (axs[1], "usa", FG.C_USA)):
        y = s[f"{base}_{mod}"] + s[f"transf_{mod}"]
        ax.plot(x, y, "-", color=cor, lw=2)
        ax.scatter(x, y, color=cor, s=14, zorder=3)
        if provisorios:
            ax.axvspan(pd.Period(provisorios[0]).to_timestamp(), x.max(),
                       color="#f0efec", zorder=0)
        ax.set_ylim(0, y.max() * 1.15)
        ax.set_ylabel(f"{mod.upper()}\nsaidas/mes", color=FG.TINTA2, fontsize=9)
        ax.grid(axis="y", color="#e6e5e1", lw=.8)
        for e in ("top", "right"):
            ax.spines[e].set_visible(False)
        ax.annotate(f"{y.iloc[-1 - len(provisorios)]:,.0f}".replace(",", "."),
                    (x[-1 - len(provisorios)], y.iloc[-1 - len(provisorios)]),
                    xytext=(0, 8), textcoords="offset points", ha="center",
                    fontsize=8, color=FG.TINTA2)
    axs[1].text(x.max(), 0, "provisorio ", ha="right", va="bottom", fontsize=7,
                color=FG.TINTA2)
    axs[0].set_title(f"SAMU-SP no SIA/SUS: {base}s + transferencias por mes",
                     loc="left", fontsize=10, color=FG.TINTA)
    fig.tight_layout()
    fig.savefig(FG.FIG / "sp_06_producao_samu.png")
    plt.close(fig)


def main():
    df = carrega()
    cd = pd.read_parquet(DADOS / "sp_candidatos.parquet")
    n_usb, n_usa = int(cd.n_usb.sum()), int(cd.n_usa.sum())
    s = serie_mensal(df)
    ultimo = s.index.max()
    completos = s.index[s.index <= ultimo - N_PROVISORIO]
    janela = completos[-12:]                       # ultimos 12 meses fechados
    sj = s.loc[janela]
    horas = float(sum(p.days_in_month * 24 for p in janela))

    # carga por modalidade: envios (pre-hospitalar) + transferencias
    env_usa, env_usb = sj.envio_usa.sum(), sj.envio_usb.sum()
    usa = env_usa + sj.transf_usa.sum()
    usb = env_usb + sj.transf_usb.sum()
    # se os codigos de envio nao forem usados em SP, cai para atendimento
    fonte = "envio"
    if env_usa + env_usb == 0:
        fonte = "atendimento"
        usa = sj.atend_usa.sum() + sj.transf_usa.sum()
        usb = sj.atend_usb.sum() + sj.transf_usb.sum()
    theta = float(usa / (usa + usb)) if usa + usb else None

    q = {}
    for nome, smin in TEMPOS_SERVICO_MIN.items():
        q[nome] = {"q_usb": float(min(0.95, usb / horas * smin / 60 / n_usb)),
                   "q_usa": float(min(0.95, usa / horas * smin / 60 / n_usa))}

    anual = s.groupby(s.index.year).sum()
    valida = {int(a): {"sia_atend_usb_usa": int(anual.loc[a, ["atend_usb", "atend_usa"]].sum()),
                       "sia_envios": int(anual.loc[a, ["envio_usb", "envio_usa"]].sum()),
                       "prefeitura": v}
              for a, v in PREFEITURA.items() if a in anual.index}

    v = por_cnes(df[df.cmp.isin(janela)], cd)      # mesma janela de 12 meses
    v["total"] = v[[c for c in v.columns if c in ("envio_usa", "envio_usb", "atend_usa",
                                                   "atend_usb", "transf_usa", "transf_usb")]].sum(axis=1)
    em_base = v[v.n_usb.fillna(0) + v.n_usa.fillna(0) > 0]
    frac_em_base = float(em_base.total.sum() / v.total.sum()) if v.total.sum() else 0.0
    por_base = frac_em_base > 0.5 and len(em_base) >= 10

    saida = {
        "janela": [str(janela[0]), str(janela[-1])], "provisorios": [str(p) for p in s.index[-N_PROVISORIO:]],
        "fonte_carga": fonte, "frota": {"usb": n_usb, "usa": n_usa},
        "por_ano_12m": {"usa": int(usa), "usb": int(usb)},
        "theta_dados": theta, "q": q, "validacao_anual": valida,
        "anomalias_corrigidas": s.attrs["anomalias"],
        "obs": ["motolancia (0301030197) cresce de ~1 mil para ~7 mil/mes; nao entra "
                "na carga das ambulancias",
                "faturamento SIA ~92-93% dos atendimentos divulgados pela Prefeitura"],
        "cnes_faturantes": int(len(v)), "frac_volume_em_bases_atuais": frac_em_base,
        "q_por_base_disponivel": bool(por_base),
        # CNES que fatura e nao e candidato fica sem nome: "" e nao NaN, que
        # nao e JSON valido (o deck em node quebra ao ler)
        "maiores_faturantes": v.sort_values("total", ascending=False).head(8)[
            ["nome", "tipo", "total"]].fillna("").reset_index().to_dict("records"),
        "mensal": {str(k): {c: int(x) for c, x in row.items()}
                   for k, row in s[[c for c in CODIGOS.values() if c in s]].iterrows()},
        "fontes": ["DATASUS SIA/SUS PASP*.dbc (FTP), filtro PA_UFMUN=355030",
                   "SIGTAP Tabela Unificada 2026-07, subgrupo 03.01.03",
                   "Prefeitura de SP: 314.089 (2024) e 355.806 (2025) atendimentos presenciais"],
    }
    if por_base:
        hb = em_base.copy()
        hb["q_central"] = (hb.total / horas * TEMPOS_SERVICO_MIN["central"] / 60
                           / (hb.n_usb.fillna(0) + hb.n_usa.fillna(0)))
        saida["q_por_base"] = {int(r.id): float(min(0.95, r.q_central))
                               for r in hb.itertuples()}
    arq = DADOS / "sp_utilizacao.json"
    json.dump(saida, open(arq, "w"), indent=2, ensure_ascii=False, default=str)
    figura(s, fonte, saida["provisorios"])

    print(f"janela {janela[0]}..{janela[-1]} | carga por {fonte} | "
          f"USA {usa:,} USB {usb:,} em 12 meses")
    print(f"theta (dados) = {theta:.3f}   (modelo usava 0,10)")
    for nome, d in q.items():
        print(f"  servico {TEMPOS_SERVICO_MIN[nome]:>3.0f} min ({nome:>7}): "
              f"q_USB={d['q_usb']:.2f}  q_USA={d['q_usa']:.2f}")
    for a, d in valida.items():
        print(f"  {a}: SIA atend {d['sia_atend_usb_usa']:,} | envios {d['sia_envios']:,}"
              f" | Prefeitura {d['prefeitura']:,}")
    print(f"{len(v)} CNES faturam; {100*frac_em_base:.0f}% do volume em bases atuais "
          f"-> q por base: {'SIM' if por_base else 'nao (cidade inteira)'}")
    print(f"-> {arq}")


if __name__ == "__main__":
    main()
