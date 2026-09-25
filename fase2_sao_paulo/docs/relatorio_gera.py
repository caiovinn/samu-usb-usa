"""Gera relatorio_resultados_sp.html a partir de relatorio_resultados_sp.src.html.

Le os JSONs em dados/fase2/ e as figuras em figs/fase2/, calcula os textos
derivados (mesma logica de deck_gera.js, aqui em Python) e substitui os
placeholders __X__ do .src.html. Roda por ultimo, depois de
fase2_sao_paulo/experimentos/{roda,compara,figuras,sensib_beta}.py.

    python -m fase2_sao_paulo.docs.relatorio_gera
"""
import base64
import json
from datetime import datetime
from pathlib import Path

from fase2_sao_paulo.caminhos import DADOS, FIG

AQUI = Path(__file__).resolve().parent
SRC = AQUI / "relatorio_resultados_sp.src.html"
SAIDA = AQUI / "relatorio_resultados_sp.html"


def carrega(nome):
    return json.load(open(DADOS / nome, encoding="utf-8"))


def n(x, casas=2):
    s = f"{x:.{casas}f}"
    return s.replace(".", ",").replace("-", "−")


def pct(x, casas=1):
    return f"{n(x, casas)}%"


def km0(x):
    return f"{round(x)} km"


def vez(a, b):
    return f"{n(a / b, 1)}×"


def seg(delta_min):
    s = round(delta_min * 60)
    sinal = "+" if s > 0 else ("−" if s < 0 else "±")
    return f"{sinal}{abs(s)} s"


def fig_b64(nome):
    dados = base64.b64encode((FIG / nome).read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{dados}" alt="{nome}">'


def tabela_html(cabecalho, linhas, alinhar_direita=None):
    alinhar_direita = alinhar_direita or set()
    th = "".join(f'<th class="{"n" if i in alinhar_direita else ""}">{c}</th>'
                 for i, c in enumerate(cabecalho))
    corpo = ""
    for linha in linhas:
        tds = "".join(f'<td class="{"n" if i in alinhar_direita else ""}">{c}</td>'
                      for i, c in enumerate(linha))
        corpo += f"<tr>{tds}</tr>\n"
    return f"<thead><tr>{th}</tr></thead>\n<tbody>\n{corpo}</tbody>"


def main():
    res = carrega("sp_resultado.json")
    comp = carrega("sp_comparacao.json")
    beta_sens = None
    if (DADOS / "sp_beta_sens.json").exists():
        beta_sens = carrega("sp_beta_sens.json")

    por_config = {c["config"]: c for c in comp}
    atual_c, pm_c, huff_c = (por_config["atual"], por_config["p-median (classico)"],
                             por_config["Huff+2SFCA"])
    base = res["atual"]

    def jo(lam):
        return res["por_lambda"][f"{lam:g}"]["joelho"]

    txt = SRC.read_text(encoding="utf-8")

    # ---------------------------------------------------------- 1: metadados
    txt = txt.replace("__DATA_GERACAO__",
                       datetime.now().strftime("Gerado em %d/%m/%Y às %H:%M"))
    # horas de inicio/fim/duracao: melhor esforco -- preenchidas a mao se o
    # log do rerun nao estiver disponivel neste processo
    for chave in ("__HORA_INICIO__", "__HORA_FIM__", "__DURACAO__"):
        if chave in txt:
            txt = txt.replace(chave, "ver log do rerun")

    # ------------------------------------------------------- 2: tabela lambda
    linhas = [["atual", n(base["f_tempo"]), "—", n(base["f_gini"], 3), "—", "—"]]
    for lam in sorted(res["por_lambda"], key=float):
        j = jo(float(lam))
        linhas.append([f"λ = {lam}", n(j["f_tempo"]), seg(j["f_tempo"] - base["f_tempo"]),
                        n(j["f_gini"], 3), str(j["movidas"]), km0(j["km_total"])])
    tabela = tabela_html(["config.", "E[T] min", "Δ/chamado", "Gini", "movidas", "km"],
                          linhas, alinhar_direita={1, 2, 3, 4, 5})
    txt = txt.replace("<!-- __TABELA_LAMBDA__ -->", tabela)

    # --------------------------------------------------- 3: tabela comparacao
    linhas = []
    for nome, rot in [("atual", "atual"), ("p-median (classico)", "p-median clássico"),
                       ("Huff+2SFCA", "Huff + 2SFCA")]:
        c = por_config[nome]
        linhas.append([rot, n(c["huff_tempo"]), n(c["huff_gini"], 3),
                        n(c["classico_t_usa"]), km0(c["km_mudanca"]), str(c["movidas"])])
    tabela = tabela_html(["config.", "E[T] sob Huff", "Gini", "t até a mais próxima",
                          "km mudança", "movidas"], linhas, alinhar_direita={1, 2, 3, 4, 5})
    txt = txt.replace("<!-- __TABELA_COMPARACAO__ -->", tabela)

    # ------------------------------------------------------------- 4: figuras
    for chave, nome in [("__FIG_PARETO__", "sp_01_pareto.png"),
                        ("__FIG_GANHO__", "sp_02_ganho_km.png"),
                        ("__FIG_MAPA__", "sp_03_mapa_troca.png"),
                        ("__FIG_LORENZ__", "sp_04_lorenz.png"),
                        ("__FIG_COMPARACAO__", "sp_05_comparacao.png")]:
        txt = txt.replace(f"<!-- {chave} -->", fig_b64(nome))

    # --------------------------------------------------------- 5: achado central
    j1 = jo(1.0)
    rho_g = 100 * (base["f_gini"] - j1["f_gini"]) / base["f_gini"]
    perda = 100 * (pm_c["huff_tempo"] / huff_c["huff_tempo"] - 1)
    achado = (f'Movendo {j1["movidas"]} das 123 unidades ({km0(j1["km_total"])} ao todo), '
              f'o Gini cai de {n(base["f_gini"], 3)} para {n(j1["f_gini"], 3)} — '
              f'{n(rho_g, 0)}% do ganho de equidade possível. Planejar pela regra clássica '
              f'(p-median) custa apenas {n(perda, 1)}% de tempo esperado a mais que o ótimo '
              f'sob Huff — o ganho real do modelo está na equidade '
              f'({vez(pm_c["huff_gini"], huff_c["huff_gini"])} melhor que o p-median), não na '
              f'eficiência.')
    txt = txt.replace("<!-- __TXT_ACHADO__ -->", achado)

    # ------------------------------------------------- 6: sensibilidade em beta
    if beta_sens:
        linhas = [[n(r["beta"], 1), n(r["n_ef_usa_mediana"], 1), n(r["f_tempo"]),
                    n(r["f_gini"], 3)] for r in beta_sens["tabela_atual"]]
        tabela = tabela_html(["β", "N_ef mediano", "E[T] min", "Gini"], linhas,
                             alinhar_direita={1, 2, 3})
        txt = txt.replace("<!-- __TABELA_BETA_BARATA__ -->", tabela)

        linha1 = [r for r in beta_sens["sweep"] if r["lam"] == 1.0]
        linhas = [[n(r["beta"], 1), n(r["f_tempo"]), n(r["f_gini"], 3),
                    f'{r["movidas"]} / {km0(r["km_total"])}',
                    pct(100 * r["rho_g"], 0) if r["rho_g"] is not None else "—"]
                   for r in linha1]
        tabela = tabela_html(["β", "E[T] min", "Gini", "movidas / km", "ρ_G (λ=1)"],
                             linhas, alinhar_direita={1, 2, 3, 4})
        txt = txt.replace("<!-- __TABELA_BETA_SWEEP__ -->", tabela)

        rho_gs = [r["rho_g"] for r in linha1 if r["rho_g"] is not None]
        sobrevive = all(v >= 0.5 for v in rho_gs) if rho_gs else False
        if sobrevive:
            txt_beta = (f'Sim. Em todos os β testados ({", ".join(n(r["beta"], 1) for r in linha1)}), '
                        f'λ=1 entrega pelo menos {pct(100 * min(rho_gs), 0)} do ganho de equidade '
                        f'alcançável naquele β — a recomendação de poucas unidades e pouco '
                        f'deslocamento não depende de qual destes β foi escolhido.')
        else:
            txt_beta = (f'Parcialmente. A fração do ganho de equidade entregue por λ=1 varia de '
                        f'{pct(100 * min(rho_gs), 0)} a {pct(100 * max(rho_gs), 0)} conforme β — '
                        f'a recomendação precisa declarar em que faixa de β ela vale '
                        f'(ver matematica_usb_usa.html §10).')
        txt = txt.replace("<!-- __TXT_BETA__ -->", txt_beta)
    else:
        aviso = ("dados/fase2/sp_beta_sens.json não encontrado — rode "
                 "fase2_sao_paulo/experimentos/sensib_beta.py.")
        for chave in ("<!-- __TABELA_BETA_BARATA__ -->", "<!-- __TABELA_BETA_SWEEP__ -->"):
            txt = txt.replace(chave, f"<tbody><tr><td>{aviso}</td></tr></tbody>")
        txt = txt.replace("<!-- __TXT_BETA__ -->", aviso)

    SAIDA.write_text(txt, encoding="utf-8")
    print(f"-> {SAIDA}  ({SAIDA.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
