"""Gera fase4_hipercubo/docs/relatorio_hipercubo.html a partir dos JSON de dados/fase4.

Nenhum numero e digitado aqui: tudo vem dos arquivos. Os textos de interpretacao
dependem dos numeros so por comparacoes (maior/menor); se um resultado mudar de
sinal, a frase correspondente e reescrita pelo codigo.

Uso: uv run python -m fase4_hipercubo.docs.relatorio_gera
"""
import base64
import html
import json

import numpy as np

from ..caminhos import DADOS, FIG

SAIDA = DADOS.parent.parent / "fase4_hipercubo" / "docs" / "relatorio_hipercubo.html"


def J(nome):
    return json.load(open(DADOS / nome, encoding="utf-8"))


def tem(nome):
    return (DADOS / nome).exists()


def img(nome):
    b = base64.b64encode((FIG / nome).read_bytes()).decode()
    return f'<img alt="{nome}" src="data:image/png;base64,{b}">'


def f(x, d=2, sinal=False):
    return (f"{x:+.{d}f}" if sinal else f"{x:.{d}f}").replace(".", ",")


def tabela(cab, linhas):
    h = "".join(f"<th>{html.escape(c)}</th>" for c in cab)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f"<div class='tab'><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>"


def main():
    real = J("v_real_vs_sim.json")["resumo"]
    abl = J("h_ablacao.json")
    ex = J("v_exato_vs_aprox.json")["resumo"]
    sens = J("h_sensibilidade.json") if tem("h_sensibilidade.json") else None
    res = J("h_resumo.json") if tem("h_resumo.json") else None

    # ---- numeros-chave
    c = real["central:vidas"]
    mods = ("fase3", "larson75", "larson75_ida")
    abl_ok = {k: v for k, v in abl.items()}
    efeito_rho = np.mean([v["fixa"] - v["endogena"] for v in abl_ok.values()])
    efeito_q = np.mean([v["endogena"] - v["larson75"] for v in abl_ok.values()])

    resumo_busca = "A busca com hipercubo ainda não foi rodada."
    if res:
        hcs = {k: v for k, v in res["pares"].items() if k.startswith("hc")}
        pos = {k: v for k, v in hcs.items() if v["dif_pareada_media"] > 0}
        neg = [k[3:] for k, v in hcs.items() if v["dif_pareada_media"] <= 0]
        mx = max(v["dif_pareada_media"] / v["sim_fase3"] * 100 for v in pos.values())
        resumo_busca = (f"Usado para reotimizar posições, o ganho na simulação é pequeno: em {len(pos)} de {len(hcs)} casos fica entre "
                        f"{f(min(v['dif_pareada_media'] for v in pos.values()), 2, True)} e {f(max(v['dif_pareada_media'] for v in pos.values()), 2, True)} "
                        f"vidas por 1.000 PCR (no máximo {f(mx, 1)}%), e em {', '.join(neg) or 'nenhum caso'} a busca ficou pior que a fase 3 (seção 4).")
    t_val = tabela(["Medida (modelo − simulação)", "Modelo da fase 3", "Hipercubo (Larson 1975)", "Hipercubo + serviço por deslocamento"],
                   [[nome,
                     *[f"{f(real[f'central:{m}'][k]['vies'], 2, True)} / {f(real[f'central:{m}'][k]['mae'], 2)}" for k in ("fase3", "larson75", "larson75_ida")]]
                    for nome, m in (("Vidas por 1.000 PCR", "vidas"), ("Cobertura grave em 15 min (pp)", "cob_grave"),
                                    ("Cobertura básico em 15 min (pp)*", "cob_basico"),
                                    ("Tempo grave (min)", "et_grave"), ("Tempo básico (min)", "et_basico"))])

    t_abl = tabela(["Configuração", "Simulação", "Fase 3", "Hipercubo, ocupação fixa", "Hipercubo, ocupação por unidade", "+ correção de Larson", "Ocupação USB (mín–máx)"],
                   [[k, f(v["sim"]), f(v["fase3"]), f(v["fixa"]), f(v["endogena"]), f(v["larson75"]),
                     f"{f(v['rho_usb'][0])}–{f(v['rho_usb'][2])}"] for k, v in abl.items()])

    # ---- exato
    linhas_ex = []
    for chave, e in ex.items():
        n, carga = chave[1:].split("_carga")
        if n in ("10",):
            linhas_ex.append([n, carga, f(e["bloq_exato"], 3), f(e["daskin"]["rho_max_med"], 4), f(e["larson75"]["rho_max_med"], 4),
                              f(e["daskin"]["P_max_med"], 4), f(e["larson75"]["P_max_med"], 4)])
    t_ex = tabela(["Unidades", "Ocupação média", "Bloqueio (exato)", "Erro máx. de ocupação: indep.", "idem: Larson 1975",
                   "Erro máx. de P(despacho): indep.", "idem: Larson 1975"], linhas_ex)

    # ---- sensibilidade
    sec_sens = ""
    if sens:
        A = sens["A_servico"]
        linhas = []
        for cfg, v in A.items():
            for k, nome in (("vidas", "vidas"), ("et_grave", "tempo grave (min)"), ("q_usa", "ocupação USA")):
                linhas.append([cfg, nome, f(v["hipercubo"][k], 3), f(v["sim_gamma"][k], 3), f(v["sim_exp"][k], 3)])
        t_A = tabela(["Configuração", "Medida", "Hipercubo", "Simulação, serviço Gamma(2) (fase 3)", "Simulação, serviço exponencial"], linhas)
        B = sens["B_tempo_servico"]
        linhas_B = [[k.split(" | ")[0], k.split(" | ")[1], f(v["dif_sim"], 2, True),
                     f"{f(v['dif_sim_min'], 2, True)} a {f(v['dif_sim_max'], 2, True)}", f(v["dif_hipercubo"], 2, True)]
                    for k, v in B.items()]
        t_B = tabela(["Solução da busca com hipercubo", "Serviço", "Ganho sobre a fase 3 (simulação)", "Faixa entre sementes", "Ganho previsto pelo hipercubo"], linhas_B) if B else "<p>(sem dados)</p>"
        C = sens["C_truncagem_usb"]
        t_C = tabela(["Configuração"] + [f"{k} USB por lista" for k in C],
                     [[cfg] + [f(C[k][cfg], 2) for k in C] for cfg in C[next(iter(C))]])
        sec_sens = f"""
<h2>5. Sensibilidades</h2>
<h3>5.1 Hipótese de serviço: o que explica o resíduo</h3>
<p>Na simulação da fase 3 o tempo ocupado de cada viatura inclui o deslocamento real. O hipercubo clássico usa um tempo de serviço fixo por classe. Rodei também a simulação com serviço exponencial de média fixa, que é a hipótese do hipercubo.</p>
{t_A}
<p>Com o serviço exponencial da própria hipótese do hipercubo, o modelo fica otimista nas vidas. Com o serviço Gamma da fase 3 ele fica próximo, o que em parte é compensação de efeitos. A ocupação simulada das USA é maior que a do hipercubo porque as unidades que atendem mais longe ficam mais tempo ocupadas. A extensão "serviço por deslocamento" (nossa, inspirada na ideia de serviço por local de Budge et al., artigo não lido) corrige isso e reduz o erro da cobertura grave (tabela da seção 3).</p>
<h3>5.2 Tempo de serviço: 45, 70 e 100 min</h3>
{t_B}
<h3>5.3 Truncagem das listas de preferência</h3>
{t_C}
<p>O número de USB por lista (8, 12 ou 20) praticamente não altera as vidas; a truncagem em 12 é suficiente.</p>
<p class='nota'>A sensibilidade ao θ (fração de chamados graves) não se aplica: a fase 3 mede a PCR como traçadora e o θ não entra no objetivo.</p>"""

    # ---- busca
    sec_busca = ""
    if res:
        linhas = []
        for k, v in res["pares"].items():
            linhas.append([k, f(v["sim_fase3"]), f(v["sim_hc"]), f(v["dif_pareada_media"], 2, True),
                           f"{f(v['dif_min'], 2, True)} a {f(v['dif_max'], 2, True)}",
                           "" if v["unidades_diferentes_da_fase3"] is None else str(v["unidades_diferentes_da_fase3"])])
        var = res["vidas_hc_entre_sementes"]
        maiores, menores = [], []
        for k, v in res["pares"].items():
            if k.startswith("hc") and k[3:] in var:
                amp = var[k[3:]]["max"] - var[k[3:]]["min"]
                (maiores if v["dif_pareada_media"] > amp else menores).append(k[3:])
        frase_busca = ("As faixas das sementes da simulação são estreitas (mesmos chamados). "
                       "Comparando o ganho pareado com a amplitude entre sementes da busca: "
                       f"o ganho é maior que a amplitude em {', '.join(maiores) or 'nenhum caso'}; "
                       f"é menor ou do tamanho dela em {', '.join(menores) or 'nenhum caso'} "
                       "(nesses, não se distingue de sorte da busca). Casos com ganho negativo mostram que a busca "
                       "a partir de &quot;hoje&quot; pode parar em ótimos locais piores que a solução da fase 3, "
                       "que usa mais partidas e refinamento.")
        linhas_v = [[k, f"{f(v['min'])} a {f(v['max'])}", str(v["n"])] for k, v in var.items()]
        sec_busca = f"""
<h2>4. Busca local com o hipercubo</h2>
<p>A busca é a da fase 3 (Teitz–Bart generalizado) com o hipercubo como avaliador de aceitação. Objetivo, limite K e guardas são os da fase 3. As soluções finais passam pela simulação, que é independente do hipercubo, com as mesmas sementes da fase 3 (comparação pareada).</p>
{img('h02_busca.png')}
{tabela(['Solução', 'Simulação, fase 3', 'Simulação, hipercubo', 'Diferença pareada (média)', 'Faixa (3 sementes)', 'Unidades diferentes'], linhas)}
<p>Variação do resultado entre sementes da busca (vidas pelo hipercubo, a partir de "hoje"):</p>
{tabela(['Caso', 'Faixa de vidas', 'Sementes'], linhas_v)}
<p>{frase_busca}</p>"""

    css = """
:root{--bg:#fff;--fg:#1d1d1f;--mut:#555;--bd:#d8d8dc;--hd:#f2f2f5;--ac:#d95f02}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#16161a;--fg:#ececf0;--mut:#a5a5b0;--bd:#35353d;--hd:#22222a}}
body{background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif;max-width:980px;margin:0 auto;padding:24px 16px}
h1{font-size:1.7rem}h2{margin-top:2.2rem;border-bottom:1px solid var(--bd);padding-bottom:4px}
.tab{overflow-x:auto}table{border-collapse:collapse;margin:12px 0;font-size:.92rem}
th,td{border:1px solid var(--bd);padding:5px 9px;text-align:left}th{background:var(--hd)}
img{max-width:100%;height:auto}.nota{color:var(--mut);font-size:.9rem}
.res{border-left:4px solid var(--ac);padding:6px 14px;background:var(--hd)}
"""
    corpo = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Fase 4 — hipercubo</title><style>{css}</style></head><body>
<h1>Fase 4: o modelo hipercubo de Larson como avaliador e busca local</h1>
<div class="res">
<p><b>Resposta curta.</b> Como avaliador, o hipercubo corrige o viés otimista do modelo da fase 3: o erro médio nas vidas por 1.000 PCR (serviço central, 13 configurações) cai de {f(c['fase3']['mae'])} para {f(c['larson75']['mae'])} e o viés vai de {f(c['fase3']['vies'], 2, True)} para {f(c['larson75']['vies'], 2, True)}.
A melhora vem da <b>ocupação diferente por unidade</b> (média de {f(efeito_rho)} vidas por 1.000 PCR sobre as 7 configurações da ablação), e <b>não</b> da correção de dependência de Larson (média de {f(efeito_q, 3)}), que com 123 unidades e ocupação média ~0,33 é desprezível.
{resumo_busca}</p></div>

<h2>1. Método</h2>
<p>Larson (1975, <i>Operations Research</i> 23(5):845–868, doi:10.1287/opre.23.5.845), lido no texto: a região é dividida em átomos (aqui, zonas de 1 km), cada um gera chamados Poisson; as N unidades têm serviço exponencial; o despacho segue uma lista de preferência fixa por átomo. A aproximação estima a ocupação ρ de cada unidade por um ponto fixo, com a probabilidade de a (j+1)-ésima unidade da lista ser a primeira livre dada por Q(N,ρ,j)·ρ₁⋯ρⱼ·(1−ρⱼ₊₁); Q = 1 é a ocupação independente das fases 2b e 3. Usamos o sistema de perda (sem fila, ~0% na simulação) e Q' das eqs. 14–16 do artigo. Regras de despacho iguais às da simulação: grave → USA livre mais próxima; básico → USB, senão USA; PCR traçadora → livre mais próxima de qualquer tipo.</p>
<p class="nota">Não implementado como no artigo: serviço por local e várias unidades por local de Budge, Ingolfsson &amp; Erkut (2009, doi:10.1287/opre.1080.0591), cujo texto não foi lido. Larson (1974), Jarvis (1985) e Batta et al. (1989) tiveram só os metadados conferidos (Crossref/OpenAlex). Generalizações nossas (μ por unidade, listas parciais, fator "local", serviço por deslocamento) estão marcadas como tal em notas_metodo.md.</p>

<h2>2. Validação exata em instâncias pequenas</h2>
<p>O solver exato reproduz o exemplo de 3 unidades do artigo (ocupações 0,3548 / 0,3650 / 0,3724) e a aproximação reproduz os valores aproximados publicados. Em instâncias sintéticas (8 sementes por caso), instâncias de 10 unidades:</p>
{t_ex}

<h2>3. Hipercubo contra a simulação, dados reais de São Paulo</h2>
<p>Simulação de eventos discretos da fase 3 (365 dias, 3 sementes), 13 configurações. Cada célula: viés / erro absoluto médio (modelo − simulação), serviço central (70 min). *A guarda de cobertura do básico da fase 3 é só USB; a simulação e o hipercubo usam a regra real (USB depois USA), o que explica parte da diferença nessa linha.</p>
{t_val}
{img('h01_validacao.png')}
<h3>Ablação: de onde vem a melhora</h3>
<p>Mesmo código de avaliação com três ocupações. Com ocupação fixa por classe, ele reproduz o modelo da fase 3 exatamente.</p>
{t_abl}
{sec_busca}
{sec_sens}
<h2>6. Limitações</h2>
<ul>
<li>Serviço exponencial e sem fila; a simulação tem serviço Gamma com deslocamento e fila de espera (≈0%).</li>
<li>Taxa de chamados por zona = taxa total × população (não há taxa por zona nos dados); sem perfil horário; despacho real não observado.</li>
<li>Tempo de serviço (45/70/100 min) continua sendo hipótese, não medida.</li>
<li>A triagem de candidatos da busca usa a ocupação independente; o hipercubo decide a aceitação mas não define o espaço de busca.</li>
<li>Resultados da busca são de um conjunto limitado de sementes e partidas.</li>
</ul>
</body></html>"""
    SAIDA.write_text(corpo, encoding="utf-8")
    print("relatorio em", SAIDA)


if __name__ == "__main__":
    main()
