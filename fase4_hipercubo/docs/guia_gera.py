"""Gera fase4_hipercubo/docs/guia_didatico.html: comparacao das fases e a teoria explicada.

Todos os numeros vem de dados/fase4/*.json (h_comparacao, h_ablacao, h_sensibilidade,
v_real_vs_sim, v_exato_vs_aprox) ou sao calculados aqui a partir deles; os exemplos de
ensino usam numeros reais do projeto ou aritmetica trivial, e os ilustrativos sao rotulados.

Uso: uv run python -m fase4_hipercubo.docs.guia_gera
"""
import base64
import html
import json

import numpy as np

from ..caminhos import DADOS, FIG
from ..modelo import hc_real as HR

SAIDA = DADOS.parent.parent / "fase4_hipercubo" / "docs" / "guia_didatico.html"


def J(nome):
    return json.load(open(DADOS / nome, encoding="utf-8"))


def n(x, d=2, sinal=False):
    if round(x, d) == 0:
        x = 0.0                      # evita "-0,00"
    return (f"{x:+.{d}f}" if sinal else f"{x:.{d}f}").replace(".", ",")


def img(nome):
    return f'<img alt="{nome}" src="data:image/png;base64,{base64.b64encode((FIG / nome).read_bytes()).decode()}">'


def tabela(cab, linhas, classe=""):
    h = "".join(f"<th>{c}</th>" for c in cab)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f"<div class='tab {classe}'><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>"


def main():
    comp = J("h_comparacao.json")
    C = comp["configs"]
    abl = J("h_ablacao.json")
    real = J("v_real_vs_sim.json")["resumo"]
    sens = J("h_sensibilidade.json")
    U = HR.dados()["U"]
    q_usb, q_usa = U["q"]["central"]["q_usb"], U["q"]["central"]["q_usa"]

    # ---- tabela principal
    linhas = []
    for nome, v in C.items():
        a, h, s = v["anterior"], v["hipercubo"], v["simulacao"]
        sv = n(s["vidas"], 1) if s else "–"
        sc = n(s["vidas_pior_decil"], 1) if s else "–"
        linhas.append([f"<b>{html.escape(nome)}</b>", str(v["movidas"]),
                       f"{n(a['f_tempo'])} → <b>{n(h['f_tempo'])}</b>",
                       f"{n(a['f_gini'], 3)} → <b>{n(h['f_gini'], 3)}</b>",
                       f"{n(a['cob_usa_10_p10'], 1)} → <b>{n(h['cob_usa_10_p10'], 1)}</b>",
                       f"{n(a['vidas'], 1)} → <b>{n(h['vidas'], 1)}</b> ({sv})",
                       f"{n(a['cvar10'], 1)} → <b>{n(h['cvar10'], 1)}</b> ({sc})"])
    t_main = tabela(["Mapa de bases", "Ambulâncias movidas", "Tempo médio (min)", "Gini (acesso à USA)",
                     "Cobertura USA em 10 min, 10% piores (%)", "Vidas por 1.000 PCR", "CVaR10 (vidas por 1.000 PCR)"], linhas, "larga")

    # ---- numeros para o texto
    ant_sim = np.mean([v["anterior"]["vidas"] - v["simulacao"]["vidas"] for v in C.values() if v["simulacao"]])
    hc_sim = np.mean([v["hipercubo"]["vidas"] - v["simulacao"]["vidas"] for v in C.values() if v["simulacao"]])
    ant_sim_c = np.mean([v["anterior"]["cvar10"] - v["simulacao"]["vidas_pior_decil"] for v in C.values() if v["simulacao"]])
    hc_sim_c = np.mean([v["hipercubo"]["cvar10"] - v["simulacao"]["vidas_pior_decil"] for v in C.values() if v["simulacao"]])
    hoje = C["hoje (rede atual)"]

    def par(k3, k4):
        a, b = C[k3], C[k4]
        return dict(dv=b["simulacao"]["vidas"] - a["simulacao"]["vidas"],
                    dc=b["simulacao"]["vidas_pior_decil"] - a["simulacao"]["vidas_pior_decil"],
                    dg=b["hipercubo"]["f_gini"] - a["hipercubo"]["f_gini"],
                    dt=b["hipercubo"]["f_tempo"] - a["hipercubo"]["f_tempo"])
    c40, cl = par("fase 3: vidas + CVaR, K=40", "fase 4: hipercubo + CVaR, K=40"), par("fase 3: vidas + CVaR, K livre", "fase 4: hipercubo + CVaR, K livre")
    cre = par("fase 3: vidas + CVaR, K livre", "fase 4: reotimiza a fase 3 + CVaR, K livre")
    p20, p40, pl = par("fase 3: vidas, K=20", "fase 4: hipercubo, K=20"), par("fase 3: vidas, K=40", "fase 4: hipercubo, K=40"), \
        par("fase 3: vidas, K livre", "fase 4: hipercubo, K livre")

    # ---- teoria: numeros de exemplo
    N = 123
    res4 = J("h_resumo.json")["pares"]
    difu = [v["unidades_diferentes_da_fase3"] for k, v in res4.items() if k.startswith("hc") and v["unidades_diferentes_da_fase3"] is not None]
    a_erl = (U["por_ano_12m"]["usa"] + U["por_ano_12m"]["usb"]) / 8760.0 * 70.0 / 60.0
    Qg = HR.q_larson75(N, a_erl, 5)
    rho_usb = abl["hoje"]["rho_usb"]
    rho_usa = abl["hoje"]["rho_usa"]
    ex_exato = J("v_exato_vs_aprox.json")["resumo"]
    sec_A = sens["A_servico"]["hoje"]
    r35 = real["central:vidas"]

    css = """
:root{--bg:#fff;--fg:#1d1d1f;--mut:#555;--bd:#d8d8dc;--hd:#f2f2f5;--ac:#d95f02;--bx:#fff7ef}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#16161a;--fg:#ececf0;--mut:#a5a5b0;--bd:#35353d;--hd:#22222a;--bx:#251f19}}
body{background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,Segoe UI,Roboto,sans-serif;max-width:1000px;margin:0 auto;padding:24px 16px}
h1{font-size:1.7rem}h2{margin-top:2.4rem;border-bottom:1px solid var(--bd);padding-bottom:4px}h3{margin-top:1.6rem}
.tab{overflow-x:auto}table{border-collapse:collapse;margin:12px 0;font-size:.9rem}
th,td{border:1px solid var(--bd);padding:5px 8px;text-align:left;vertical-align:top}th{background:var(--hd)}
img{max-width:100%;height:auto}.nota{color:var(--mut);font-size:.9rem}
.caixa{border-left:4px solid var(--ac);padding:6px 14px;background:var(--bx);margin:14px 0}
code{background:var(--hd);padding:1px 5px;border-radius:3px}
.formula{font-family:Cambria,Georgia,serif;font-size:1.05rem;background:var(--hd);padding:8px 12px;margin:10px 0;overflow-x:auto}
"""
    # ---- numeros extras para o texto novo
    from fase3_vidas.modelo import sobrevida as SV
    ex_res = J("v_exato_vs_aprox.json")
    n_casos_exato = len(ex_res["resumo"]) * ex_res["sementes"]
    n_buscas = len(J("h_busca.json"))
    n_refino = len(list((DADOS / "h_refina").glob("*.json")))
    n_cfg_sim = len({l["config"] for l in J("v_real_vs_sim.json")["linhas"]})   # configuracoes da validacao
    # exemplo ilustrativo (numeros inventados para ensinar): bairro com duas ambulancias
    tA, tB = 4.0, 8.0                    # min ate a ambulancia central A e a periferica B
    rA, rB = rho_usb[2], rho_usb[0]      # ocupacoes extremas encontradas pelo hipercubo em "hoje"
    qq = q_usb

    def despacho2(oA, oB):
        pA, pB = 1 - oA, oA * (1 - oB)
        pA += 1 - pA - pB                # as duas ocupadas: espera pela mais proxima (A)
        return pA, pB
    pA1, pB1 = despacho2(qq, qq)
    pA2, pB2 = despacho2(rA, rB)
    t1, t2 = pA1 * tA + pB1 * tB, pA2 * tA + pB2 * tB
    s1, s2 = pA1 * float(SV.s(tA)) + pB1 * float(SV.s(tB)), pA2 * float(SV.s(tA)) + pB2 * float(SV.s(tB))
    glos = tabela(["Métrica", "O que mede", "Como depende da ocupação", "Melhor é"],
                  [["Tempo médio", "Minutos até a viatura chegar, médios sobre a população", "Peso de cada viatura = probabilidade de ela atender; se a mais próxima está ocupada com mais frequência, o tempo sobe", "menor"],
                   ["Gini do acesso à USA", "Desigualdade de acesso à USA entre as pessoas (0 = todos iguais)", "A acessibilidade de um bairro soma as USA que o atendem, pesadas pela chance de atenderem; ocupações diferentes mudam quem atende quem", "menor"],
                   ["10% piores (cobertura em 10 min)", "Cobertura da USA para os que estão pior", "Chance de a viatura que atende chegar em 10 min, média nos 10% menos cobertos", "maior"],
                   ["Vidas por 1.000 PCR", "Sobreviventes esperados a cada mil paradas cardíacas", "A sobrevida cai com os minutos até o desfibrilador (De Maio et al. 2003); o tempo vem de quem atende, e quem atende vem da ocupação", "maior"],
                   ["CVaR10", "Sobrevida dos 10% mais prejudicados", "Mesma conta, restrita ao pior decil", "maior"],
                   ["Ambulâncias movidas", "Custo da mudança", "Não depende da ocupação: é a diferença de posições em relação a hoje", "menor"]])
    corpo = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Guia da fase 4</title><style>{css}</style></head><body>
<h1>Guia da fase 4: hipercubo, o que foi feito e o que se concluiu</h1>

<div class="caixa">
<p><b>Em um parágrafo.</b> O hipercubo é uma forma mais realista de calcular <b>quais ambulâncias estarão livres</b> quando alguém chama. Nas fases 2b e 3, toda ambulância tinha a mesma probabilidade de estar ocupada; no hipercubo, cada uma tem a sua, e ela depende de onde a ambulância fica. Como todas as métricas (tempo, Gini, cobertura, vidas) dependem de <i>quem atende cada bairro</i>, trocar essa régua muda os números de qualquer mapa, mesmo sem mover nenhuma ambulância: a rede de hoje cai de {n(hoje['anterior']['vidas'], 1)} para {n(hoje['hipercubo']['vidas'], 1)} vidas por 1.000 PCR, e a simulação, que é o juiz, dá {n(hoje['simulacao']['vidas'], 1)}. Já as <b>posições</b> otimizadas com a régua nova melhoram pouco em relação às da fase 3.</p>
</div>
<p class="nota">Ordem deste guia: 1) o que é o hipercubo e por que ele muda as métricas; 2) o que foi feito na fase 4; 3) resultados e conclusões.</p>

<h2>1. O que é o hipercubo e por que ele muda as métricas</h2>

<h3>1.1 O problema: a ambulância mais perto pode estar ocupada</h3>
<p>Quando alguém chama, o despachante manda a ambulância <b>livre</b> mais próxima. Se a mais próxima está em outro atendimento, vai a segunda mais próxima, e assim por diante. Então o tempo de resposta de um bairro não depende só de onde as bases estão, mas de <b>a base estar livre naquele momento</b>. Para medir qualquer coisa (tempo, cobertura, vidas) precisamos de um modelo para a probabilidade de cada ambulância estar ocupada.</p>

<h3>1.2 O modelo antigo (fases 2b e 3): moedas independentes e iguais</h3>
<p>Imagine que cada ambulância joga uma moeda viciada: com probabilidade q está ocupada, com 1 − q está livre. As moedas são todas iguais e independentes. Com q = {n(q_usb, 2)} (a ocupação das USB nos dados), o modelo diz que:</p>
<ul>
<li>a mais próxima atende com probabilidade 1 − q = {n(1 - q_usb, 2)};</li>
<li>a segunda atende se a primeira está ocupada e a segunda livre: q·(1 − q) = {n(q_usb * (1 - q_usb), 3)};</li>
<li>a terceira: q²·(1 − q) = {n(q_usb ** 2 * (1 - q_usb), 3)}, e assim por diante.</li>
</ul>
<div class="formula">P(a (j+1)-ésima mais próxima atende) = q<sup>j</sup> · (1 − q)</div>
<p>É simples, rápido de calcular e foi ótimo para guiar a busca. Mas tem duas suposições fortes, e o hipercubo corrige as duas.</p>

<h3>1.3 Primeira falha: as ambulâncias não são iguais</h3>
<p>Uma ambulância no centro, onde há muitos chamados, fica ocupada boa parte do tempo. Uma na periferia quase nunca é chamada. Na rede de hoje, o hipercubo calcula que a ocupação das USB vai de {n(rho_usb[0])} a {n(rho_usb[2])} (média {n(rho_usb[1])}), e a das USA de {n(rho_usa[0])} a {n(rho_usa[2])}. O modelo antigo usava {n(q_usb)} e {n(q_usa)} para todas. Como a população está justamente onde as ambulâncias mais ocupadas ficam, o modelo antigo era otimista.</p>

<h3>1.4 Segunda falha: as ocupações não são independentes</h3>
<p>Se a ambulância A está ocupada, é sinal de um período de muita demanda, e é mais provável que a vizinha B também esteja. Moedas independentes ignoram isso. Larson (1975) mede esse efeito com um fator de correção Q(N, ρ, j), que multiplica a fórmula anterior:</p>
<div class="formula">P(a (j+1)-ésima atende) ≈ Q(N, ρ, j) · ρ₁ · ρ₂ ⋯ ρⱼ · (1 − ρⱼ₊₁)</div>
<p>Aqui ρᵢ é a ocupação da ambulância i (agora diferente para cada uma), e Q = 1 devolve o modelo antigo. Q &gt; 1 quer dizer que várias ocupadas ao mesmo tempo são mais comuns do que as moedas independentes sugerem. Com as 123 viaturas de São Paulo e ocupação média ~0,33, Q vale {', '.join(n(x, 3) for x in Qg[1:5])} para j = 1 a 4: praticamente 1. <b>Nesta escala, a dependência quase não importa; o que importa é a primeira falha.</b></p>

<h3>1.5 O hipercubo exato: contar todas as combinações</h3>
<p>O hipercubo de Larson (1974) modela o sistema como um conjunto de estados: cada estado diz <b>quais</b> ambulâncias estão ocupadas. Com 3 ambulâncias há 2³ = 8 estados. Chamados chegam e levam o sistema de um estado a outro (uma livre passa a ocupada); atendimentos terminam e o levam de volta. Resolvendo as equações de equilíbrio, obtém-se a fração do tempo em cada estado e, daí, a ocupação de cada ambulância e a chance de cada uma atender cada bairro, <b>sem supor independência</b>.</p>
<p>O problema é o tamanho: com N ambulâncias há 2<sup>N</sup> estados. Com as 123 de São Paulo, 2<sup>123</sup> ≈ {f'{2.0 ** 123:.1e}'.replace('.', ',')}, impossível. A solução exata só cabe até ~20 ambulâncias; nós a usamos para <b>validar</b> a aproximação, não para resolver São Paulo.</p>

<h3>1.6 A aproximação de Larson: "chute e corrige"</h3>
<ol>
<li>Comece supondo que todas as ambulâncias têm a mesma ocupação.</li>
<li>Para cada bairro, calcule com a fórmula da seção 1.4 quanto do seu fluxo de chamados cai em cada ambulância (a mais próxima recebe a maior parte, a segunda recebe o que sobra quando a primeira está ocupada, etc.).</li>
<li>Some o que cai em cada ambulância: é a carga de trabalho R dela. Uma ambulância com carga R fica ocupada uma fração ρ = R / (1 + R) do tempo (tempo de serviço como unidade).</li>
<li>Com as novas ocupações, volte ao passo 2. Repita até elas pararem de mudar.</li>
</ol>
<p>Em São Paulo converge em algumas dezenas de repetições, e cada avaliação de um mapa leva ~0,2 s. O exemplo de 3 ambulâncias do próprio artigo é reproduzido: ocupações exatas 0,3548 / 0,3650 / 0,3724 e aproximadas 0,351 / 0,367 / 0,374.</p>

<h3>1.7 Por que isso muda as métricas: um exemplo</h3>
<p>Todas as métricas partem da mesma pergunta: <b>quem atende cada bairro, e com que probabilidade?</b> Para ver o efeito, considere um bairro servido por duas ambulâncias (<i>exemplo ilustrativo: números inventados para ensinar, não são dados do projeto, exceto as ocupações, que são as extremas achadas pelo hipercubo na rede de hoje</i>): A, no centro, a {n(tA, 0)} min do bairro, e B, na periferia, a {n(tB, 0)} min.</p>
{tabela(['', 'Ocupações', 'Chance de A atender', 'Chance de B atender', 'Tempo médio até a chegada', 'Sobrevida a uma PCR'],
        [['Modelo antigo', f'A = B = {n(qq, 2)}', n(pA1, 2), n(pB1, 2), f'{n(t1, 2)} min', f'{n(100 * s1, 1)}%'],
         ['Hipercubo', f'A = {n(rA, 2)}, B = {n(rB, 2)}', n(pA2, 2), n(pB2, 2), f'{n(t2, 2)} min', f'{n(100 * s2, 1)}%']])}
<p>A ambulância central está quase sempre ocupada, então quem atende é a periférica, mais longe: o tempo sobe e a sobrevida cai. Isso muda o tempo médio, a cobertura dos 10% piores, as vidas e o CVaR10. O Gini também muda, porque ele mede quem tem acesso à USA, e o acesso de um bairro depende da chance de cada USA atendê-lo. Só as <b>ambulâncias movidas</b> não mudam (dependem apenas das posições).</p>
{glos}
<p class="nota">Quando comparamos o mesmo mapa nas duas réguas, a diferença vem inteira da ocupação, porque as posições são as mesmas.</p>

<h2>2. O que foi feito na fase 4</h2>
<p>Linha do tempo das fases, para situar a fase 4:</p>
{tabela(['Fase', 'Pergunta', 'Como trata ambulância ocupada', 'Medida de qualidade', 'Como busca os mapas'],
        [['2', 'Onde ficam as bases para reduzir o tempo e a desigualdade?', 'Escolha de Huff: o setor é atendido pelas bases em proporção a uma função da distância (não há ocupação).', 'Tempo médio e Gini do acesso à USA', 'Algoritmo genético NSGA-II (duas metas ao mesmo tempo)'],
         ['2b', 'Idem, mas com ambulância ocupada.', f'Regra de despacho: atende a mais próxima que estiver livre; toda ambulância ocupada com a mesma probabilidade q ({n(q_usb, 2)} USB, {n(q_usa, 2)} USA), independente.', 'Tempo médio, Gini, cobertura dos 10% piores', 'NSGA-II com o modelo de despacho'],
         ['3', 'Quantas vidas se salvam? (parada cardiorrespiratória como caso-teste)', 'Mesma regra da 2b.', 'Vidas por 1.000 PCR e CVaR10', 'Busca local (troca uma viatura de lugar por vez) e um limite superior por programação inteira'],
         ['4', 'A ocupação independente e igual distorce os resultados?', '<b>Hipercubo de Larson</b>: ocupação própria por ambulância.', 'As mesmas da fase 3 (e, para comparar, as da 2b)', 'A mesma busca local, aceitando trocas pelo hipercubo']])}
<h3>2.1 Passos executados</h3>
<ol>
<li><b>Estudo do método.</b> Leitura do artigo de Larson (1975), cujas equações foram implementadas. O artigo de Budge, Ingolfsson e Erkut (2009), sobre serviço por local, <b>não foi lido</b>; o que fizemos nessa direção é formulação própria.</li>
<li><b>Hipercubo exato</b> para poucas ambulâncias, verificado contra a fórmula de Erlang, balanço de carga, força bruta e o exemplo numérico publicado no artigo.</li>
<li><b>Aproximação de Larson</b>, testada contra o hipercubo exato em {n_casos_exato} instâncias sintéticas (6, 10 e 14 ambulâncias, ocupação média de 0,1 a 0,6, {ex_res['sementes']} sementes).</li>
<li><b>Avaliador para São Paulo:</b> 26.889 setores, zonas de 1 km para calcular a carga, regras de despacho iguais às da simulação (grave → USA livre mais próxima; básico → USB, senão USA; PCR → qualquer tipo), sistema sem fila (a fila ocorre em ~0% dos chamados na simulação).</li>
<li><b>Validação contra a simulação da fase 3</b> ({n_cfg_sim} mapas × 3 tempos de serviço × 3 sementes).</li>
<li><b>Ablação:</b> separar quanto do ganho vem da ocupação diferente por ambulância e quanto vem da correção de dependência.</li>
<li><b>Busca local com o hipercubo</b> como avaliador de aceitação ({n_buscas} buscas a partir de hoje e da fase 3, mais {n_refino} buscas com chutes). Mesmo objetivo (vidas e CVaR10), mesmas guardas de cobertura e mesmo limite K da fase 3. Os candidatos continuam propostos pelo modelo antigo (mais rápido); o hipercubo aceita ou recusa.</li>
<li><b>Simulação das soluções novas</b> com as mesmas sementes da fase 3 (comparação pareada).</li>
<li><b>Sensibilidades:</b> tempo de serviço (45/70/100 min), serviço exponencial contra Gamma na simulação e truncagem das listas de preferência.</li>
<li><b>Extensão própria (opcional):</b> tempo de serviço que depende do deslocamento, para explicar o que sobrou de diferença com a simulação.</li>
</ol>
<p><b>O que não mudou:</b> os dados, o objetivo, as guardas, o limite K, a simulação como árbitro, e nenhum arquivo das fases 1 a 3.</p>

<h2>3. Resultados e conclusões</h2>
<h3>3.1 A tabela comparativa</h3>
<p>Cada linha é um mapa de bases; as linhas estão agrupadas pelo objetivo da busca (só vidas, ou vidas + CVaR10). Cada coluna mostra a nota do mapa com <b>a régua antiga → a régua nova (hipercubo)</b>. A simulação, que não depende de nenhuma das duas réguas, aparece entre parênteses nas colunas de vidas e de CVaR10.</p>
{t_main}
<p class="nota">Tempo médio, Gini e cobertura dos 10% piores: definidos como na fase 2b (tempos brutos do OSM, θ = {n(comp['theta'], 4)}, pool básico com qualquer tipo de viatura). Vidas e CVaR10: como na fase 3 (tempos calibrados, serviço de {n(comp['servico_min'], 0)} min). Unidades movidas: em relação à rede de hoje. Todos os mapas, inclusive os da fase 2, são reavaliados com a regra de despacho (viatura livre mais próxima); por isso a linha "fase 2" difere do que a fase 2 publicou com o modelo de Huff. A cobertura dos 10% piores é zero em vários mapas porque, neles, esses 10% não têm nenhuma USA a até 10 min.</p>
{img('h03_comparacao.png')}

<h3>3.2 Como ler a tabela sem se confundir</h3>
<ol>
<li><b>Compare linhas na mesma régua, ou use a simulação como juiz.</b> A régua antiga dá, em média, {n(ant_sim, 2, True)} vidas a mais que a simulação nas linhas simuladas; o hipercubo, {n(hc_sim, 2, True)}. No CVaR10 o erro médio é {n(ant_sim_c, 2, True)} (antiga) contra {n(hc_sim_c, 2, True)} (hipercubo). As notas das duas réguas não são comparáveis: a antiga é mais otimista.</li>
<li><b>Não conclua que um mapa "caiu".</b> O mapa "vidas, K livre" valia {n(C['fase 3: vidas, K livre']['anterior']['vidas'], 1)} na régua antiga e vale {n(C['fase 3: vidas, K livre']['hipercubo']['vidas'], 1)} na nova. O mapa não piorou: mudou a régua.</li>
<li><b>Fase 3 contra fase 4, na simulação:</b> com K = 20, a fase 4 ganha {n(p20['dv'], 2, True)} vidas por 1.000 PCR; com K = 40, {n(p40['dv'], 2, True)}; com K livre, {n(pl['dv'], 2, True)}. São ganhos pequenos. Nos 10% piores (CVaR10 simulado) a diferença é {n(p20['dc'], 2, True)} (K = 20), {n(p40['dc'], 2, True)} (K = 40) e {n(pl['dc'], 2, True)} (K livre): em K = 40, o mapa da fase 4 melhora a média e piora os 10% piores. É uma troca, não um ganho em tudo.</li>
<li><b>Otimizando vidas + CVaR10 (lam = 1), a história é a mesma, só que mais difícil.</b> Na simulação, com K = 40, a fase 4 ganha {n(c40['dv'], 2, True)} vidas e {n(c40['dc'], 2, True)} no CVaR10; somando os dois, que é o objetivo dessa busca, a diferença é {n(c40['dv'] + c40['dc'], 2, True)} (a fase 4 não ganha no objetivo que otimizou). Com K livre, a busca a partir de "hoje" ficou pior que a fase 3 ({n(cl['dv'], 2, True)} vidas, {n(cl['dc'], 2, True)} no CVaR10), porque parou num ótimo local ruim. Já a reotimização a partir da solução da fase 3 praticamente não a muda ({n(cre['dv'], 2, True)} vidas, {n(cre['dc'], 2, True)} no CVaR10).</li>
<li><b>Gini e tempo médio não estão no objetivo</b> da fase 3 nem da 4. Eles são relatados, mas as buscas só maximizaram vidas (lam = 0) ou vidas + CVaR10 (lam = 1); por isso variam sem controle de uma solução a outra (Gini do hipercubo K = 40: {n(C['fase 4: hipercubo, K=40']['hipercubo']['f_gini'], 3)} contra {n(C['fase 3: vidas, K=40']['hipercubo']['f_gini'], 3)} na fase 3, na mesma régua).</li>
<li><b>Linhas de fases diferentes respondem a perguntas diferentes.</b> A fase 2 minimizava tempo médio e Gini; a fase 3 maximiza vidas sob guardas de cobertura; a fase 4 só troca o avaliador.</li>
</ol>

<h3>3.3 Conclusões</h3>
<ul>
<li><b>Como avaliador, o hipercubo funciona.</b> Nas {n_cfg_sim} configurações simuladas, o erro médio nas vidas por 1.000 PCR cai de {n(r35['fase3']['mae'])} (régua antiga) para {n(r35['larson75']['mae'])} (hipercubo), e o viés de {n(r35['fase3']['vies'], 2, True)} para {n(r35['larson75']['vies'], 2, True)}.</li>
<li><b>O ganho vem da primeira falha (ocupações diferentes), não da segunda (dependência).</b> Na ablação, com ocupação fixa e igual o meu código reproduz a régua antiga; com ocupação por ambulância ele se aproxima da simulação; acrescentar a correção de Larson muda em média {n(np.mean([v['endogena'] - v['larson75'] for v in abl.values()]), 3)} vidas por 1.000 PCR, quase nada.</li>
<li><b>Como otimizador, ajuda pouco.</b> Os mapas escolhidos com o hipercubo diferem dos da fase 3 em {min(difu)} a {max(difu)} unidades (de ~123) e valem só um pouco mais na simulação, nem sempre em todas as métricas. A busca a partir de "hoje" com lam = 1 e K livre ficou bem pior que a fase 3: a busca local tem mínimos locais e um avaliador melhor não resolve isso.</li>
<li><b>O que ainda diverge da simulação.</b> Quando a simulação usa serviço exponencial (a hipótese do hipercubo), ele ainda fica otimista: com a rede de hoje, {n(sec_A['hipercubo']['vidas'], 1)} contra {n(sec_A['sim_exp']['vidas'], 1)} vidas por 1.000 PCR. Na simulação da fase 3, o tempo ocupado inclui o deslocamento real, então as unidades que vão mais longe ficam mais ocupadas (ocupação das USA: {n(sec_A['sim_gamma']['q_usa'], 3)} na simulação contra {n(sec_A['hipercubo']['q_usa'], 3)} no hipercubo). A extensão própria da etapa 10 corrige boa parte disso, mas a busca ainda não a usa.</li>
<li><b>Limites do estudo.</b> O tempo de serviço (45/70/100 min) é hipótese, não medida; as taxas de chamado por zona são o total proporcional à população; o artigo de Budge et al. não foi lido; os resultados da busca vêm de poucas sementes e partidas.</li>
</ul>

<h2>4. Onde estão as coisas</h2>
<p>Relatório técnico: <code>fase4_hipercubo/docs/relatorio_hipercubo.html</code>. Notas de método: <code>notas_metodo.md</code>. Dados: <code>dados/fase4/h_comparacao.json</code> (a tabela da seção 3.1), <code>h_ablacao.json</code>, <code>v_real_vs_sim.json</code>. Para refazer esta página: <code>uv run python -m fase4_hipercubo.docs.guia_gera</code>.</p>
</body></html>"""
    SAIDA.write_text(corpo, encoding="utf-8")
    print("guia em", SAIDA)


if __name__ == "__main__":
    main()
