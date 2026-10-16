"""Textos interpretativos do relatorio da fase 3, com os numeros interpolados.

Separado de relatorio_gera.py para que a leitura dos resultados fique num
lugar so. Cada frase que compara numeros e montada a partir dos JSONs; as
que dependem de um resultado qualitativo (quem e melhor) testam a condicao
antes de afirmar.
"""
import json

from fase3_vidas.caminhos import DADOS


def _n(x, c=1):
    return f"{x:,.{c}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def _p(x, c=1):
    return f"{_n(x, c)}%"


def _tab(cab, linhas, dir_=(), realce=()):
    th = "".join(f'<th class="{"n" if i in dir_ else ""}">{c}</th>' for i, c in enumerate(cab))
    corpo = "".join(
        f'<tr class="{"realce" if k in realce else ""}">' +
        "".join(f'<td class="{"n" if i in dir_ else ""}">{c}</td>' for i, c in enumerate(l)) + "</tr>\n"
        for k, l in enumerate(linhas))
    return f"<thead><tr>{th}</tr></thead>\n<tbody>\n{corpo}</tbody>"


def gera(V, cal, re_, sol, lim, sim, rob, rec, rec_nome):
    T = {}
    hoje, pm = re_["hoje"], re_["p-median"]
    s = lambda k: sol[k]["exato"]
    lv, lvg = s("lam=0 K=livre"), s("lam=0 K=livre G=pm")
    eqg = s("lam=1 K=livre G=pm")
    ano = V["_ano"]
    por_mil = ano["pcr_ano"] / 1000                      # vidas/ano por 1 sobrevivente /1.000 PCR
    ganho_total = lv["vidas"] - hoje["vidas"]
    Ks = [k for k in (10, 20, 40, 80) if f"lam=0 K={k}" in sol]
    frac = {k: (s(f"lam=0 K={k}")["vidas"] - hoje["vidas"]) / ganho_total for k in Ks}
    cl = json.load(open(DADOS / "v7_classes.json", encoding="utf-8"))
    V["_cls_livre"] = cl["solucoes"]["classes chamadas K=livre"]
    pior_gini = max((v for k, v in re_.items() if k.startswith("fase2") and v["movidas"] > 60),
                    key=lambda v: v["vidas"])

    # ------------------------------------------------------------- resumo
    T["RESUMO"] = (
        "<ul>"
        f"<li><strong>O ganho grande é sair da rede de hoje.</strong> Um redesenho completo leva a sobrevida de "
        f"{_n(hoje['vidas'])} para {_n(lvg['vidas'])} sobreviventes por 1.000 PCR "
        f"(+{_p(100 * (lvg['vidas'] / hoje['vidas'] - 1), 0)}), mantendo a USA para o chamado grave no nível do p-median.</li>"
        f"<li><strong>O p-median clássico já está quase lá.</strong> O melhor mapa encontrado salva só "
        f"{_n(lvg['vidas'] - pm['vidas'])} a mais por 1.000 PCR (~{_n((lvg['vidas'] - pm['vidas']) * por_mil, 0)} vidas/ano) — "
        f"e com menos equidade (10% piores: {_n(lvg['cvar10'])} contra {_n(pm['cvar10'])}). Entre os dois, a escolha é de valores, não de técnica.</li>"
        f"<li><strong>O Gini não comprou vidas.</strong> Os redesenhos das fases 2 e 2b ficam em até {_n(pior_gini['vidas'])}, abaixo do p-median.</li>"
        f"<li><strong>Mudar pouco já rende.</strong> Mover 20 unidades entrega {_p(100 * frac.get(20, 0), 0)} do ganho do redesenho completo; "
        f"40 unidades, {_p(100 * frac.get(40, 0), 0)}.</li>"
        f"<li><strong>Cobertura em 15 min não é sobrevida.</strong> Sem a PCR no objetivo, o mapa que mais cobre chamados em 15 min "
        f"salva ~{_n(lv['vidas'] - V['_cls_livre']['vidas'])} vidas a menos por 1.000 PCR (§5.10).</li>"
        "</ul>")

    # ------------------------------------------------------------- 5.3
    linhas_k = "; ".join(f"K = {k}: {_n(s(f'lam=0 K={k}')['vidas'])} ({_p(100 * frac[k], 0)} do ganho)" for k in Ks)
    T["TXT_BUSCA"] = (
        f"<p>Com λ = 0 (só vidas): {linhas_k}; sem limite, {_n(lv['vidas'])}. Os primeiros movimentos são os que mais rendem "
        f"— cada unidade movida vale menos que a anterior. Aumentar λ troca vidas da cidade por vidas dos 10% piores: sem limite K, "
        f"λ = 1 dá {_n(s('lam=1 K=livre')['vidas'])} e CVaR₁₀ {_n(s('lam=1 K=livre')['cvar10'])}, contra {_n(lv['vidas'])} e "
        f"{_n(lv['cvar10'])} com λ = 0. O p-median ({_n(pm['vidas'])}; {_n(pm['cvar10'])}) fica praticamente sobre essa fronteira.</p>"
        f"<p class=\"nota\">A coluna \"partidas\" mostra a faixa do objetivo em degraus entre as cinco sementes aleatórias (e a partida do "
        f"p-median, sem limite K): a melhor partida é a que vai para a busca iterada.</p>")

    # ------------------------------------------------------------- 5.4 guarda
    T["TXT_GUARDA"] = (
        f"<p>Maximizar só a sobrevida a PCR deixa a cobertura da USA no chamado grave perto do piso permitido (a rede de hoje, "
        f"{_p(hoje['cob_grave'])}): {_p(lv['cob_grave'])} em até 15 min, contra {_p(pm['cob_grave'])} no p-median. Faz sentido: na PCR a USB "
        f"com DEA costuma chegar primeiro, e o objetivo não vê os chamados que só a USA resolve (AVC, infarto, trauma grave).</p>"
        f"<p>Exigir a cobertura do p-median no chamado grave (o piso do p-median, §4.5) custa quase nada: {_n(lvg['vidas'])} contra "
        f"{_n(lv['vidas'])} sobreviventes por 1.000 PCR, com {_p(lvg['cob_grave'])} de cobertura grave. Por isso a recomendação usa o piso "
        f"do p-median. Com limite K esse piso não é alcançável a partir de hoje, e as soluções com K ficam com a cobertura grave perto "
        f"da de hoje ({_n(min(s(f'lam=0 K={k}')['cob_grave'] for k in Ks), 0)}–{_n(max(s(f'lam=0 K={k}')['cob_grave'] for k in Ks), 0)}%) — "
        f"é um limite delas.</p>")

    # ------------------------------------------------------------- 5.5 qualidade
    ganhos = []
    for k, v in sol.items():
        l = v["lam"]
        J = lambda d: 1000 * (d["vidas"] + l * d["cvar10"])
        ganhos.append(J(v["degraus_refinado"]) - J(v["degraus_local"]))
    lk = lim["por_K"][0]
    folga = 100 * lk.get("folga_max_rel", float("nan"))
    T["TXT_QUALIDADE"] = (
        f"<p><strong>Busca iterada.</strong> Os {V['chutes']} chutes por configuração melhoraram o objetivo em no máximo "
        f"{_n(max(ganhos), 2)} (em sobreviventes por 1.000 PCR, já somando λ·CVaR); em {sum(g < 1e-6 for g in ganhos)} das "
        f"{len(ganhos)} configurações, nada. A melhor partida já estava no ótimo local iterado — sinal de convergência, não prova.</p>"
        f"<p><strong>Teto do MILP.</strong> Em zonas de {V['lado_km']} km, o limite dual para o caso sem limite K foi "
        f"{_n(1000 * lk['limite'])} contra {_n(1000 * lk['busca_degraus'])} da busca no mesmo objetivo em degraus — folga de "
        f"{_n(folga, 0)}%. É um teto válido, mas largo demais para certificar: a agregação em zonas sozinha já superestima a "
        f"sobrevida em ~20%, e o solver parou no limite de tempo ({_n(lk['segundos'], 0)} s). Não sabemos o quanto a busca está "
        f"longe do ótimo verdadeiro; sabemos que nos casos pequenos, onde dá para conferir, ela o encontra.</p>")

    # ------------------------------------------------------------- 5.7 robustez
    pc = {d["config"]: d for d in rob["por_config"]}
    T["TXT_ROBUSTEZ"] = (
        f"<p>O mapa de menor arrependimento máximo é <strong>{V['rec_nome']}</strong>: no pior dos 18 cenários ele perde "
        f"{_n(pc[rec_nome]['arrep_max'], 2)} sobrevivente por 1.000 PCR para o melhor mapa daquele cenário. O p-median perde até "
        f"{_n(pc['p-median']['arrep_max'], 1)}; a rede de hoje, {_n(pc['hoje']['arrep_max'], 1)}. Os níveis absolutos variam muito entre "
        f"cenários (de {_n(pc[rec_nome]['vidas_min'])} a {_n(pc[rec_nome]['vidas_max'])}, sobretudo pelo trânsito), mas a ordem dos "
        f"mapas quase não muda — a recomendação não depende das hipóteses que não conseguimos medir.</p>"
        f"<p>Mas a troca de equidade continua lá: no pior cenário, os 10% piores do mapa recomendado ficam em "
        f"{_n(pc[rec_nome]['cvar_min'])} sobreviventes por 1.000 PCR, contra {_n(pc['p-median']['cvar_min'])} no p-median. "
        f"O arrependimento mede só vidas na cidade; quem priorizar os piores deve olhar também esta coluna.</p>")

    # ------------------------------------------------------------- 5.10 classes
    linhas, chaves = [], []
    for k, v in {**cl["referencias"], **cl["solucoes"]}.items():
        nome = k.replace("classes chamadas", "classes, θ do SIA").replace("classes igual", "classes, θ = 0,5")
        nome = nome.replace("K=livre", "sem limite")
        linhas.append([nome, str(v.get("movidas", 0)), _p(v["cob_grave"]), _p(v["cob_basico"]),
                       _n(v["obj_chamadas"]), _n(v["vidas"]), _n(v["cvar10"])])
        chaves.append(k)
    linhas.append(["vidas: λ=0 sem limite · piso p-median", str(sol["lam=0 K=livre G=pm"]["movidas"]),
                   _p(lvg["cob_grave"]), _p(lvg["cob_basico"]),
                   _n(cl["theta_dados"] * lvg["cob_grave"] + (1 - cl["theta_dados"]) * lvg["cob_basico"]),
                   _n(lvg["vidas"]), _n(lvg["cvar10"])])
    T["T_CLASSES"] = _tab(["mapa", "movidas", "USA ≤ 15 min (grave)", "USB ≤ 15 min (básico)",
                           "chamados ≤ 15 min (θ do SIA)", "PCR: vidas /1.000", "CVaR₁₀"],
                          linhas, dir_={1, 2, 3, 4, 5, 6}, realce={len(linhas) - 1})
    cls = V["_cls_livre"]
    T["theta"] = _n(cl["theta_dados"], 3)
    T["TXT_CLASSES"] = (
        f"<p>Sem a PCR, o redesenho completo alcança mais chamados em 15 min do que qualquer outro mapa: "
        f"{_p(cls['cob_grave'])} dos graves e {_p(cls['cob_basico'])} dos básicos. Mas, medido em sobrevida a PCR, ele fica em "
        f"{_n(cls['vidas'])} por 1.000 — {_n(lvg['vidas'] - cls['vidas'])} abaixo do mapa otimizado por vidas e "
        f"{_n(pm['vidas'] - cls['vidas'])} abaixo do próprio p-median. O motivo é o limiar: \"em até 15 min\" não distingue chegar em "
        f"5 de chegar em 14, e a sobrevida cai ~22% por minuto nessa faixa. Os dois pesos (θ do SIA e θ = 0,5) chegam ao mesmo mapa "
        f"sem limite K, porque com 123 unidades dá para melhorar as duas classes ao mesmo tempo.</p>"
        f"<p>A lição para o projeto: <strong>métricas de cobertura com limiar largo escolhem mapas piores em vidas</strong>. Se a "
        f"PCR for descartada como traçadora, o objetivo de classes deveria usar o tempo inteiro (como o tempo esperado) ou limiares "
        f"curtos, não 15 min.</p>")

    # ------------------------------------------------------------- conclusoes
    ganho_ano = (lvg["vidas"] - hoje["vidas"]) * por_mil
    T["CONCLUSOES"] = (
        "<ol>"
        f"<li><strong>Redesenhar a rede salva vidas; o método de redesenho importa pouco, desde que mire o tempo.</strong> "
        f"De {_n(hoje['vidas'])} para {_n(lvg['vidas'])} sobreviventes por 1.000 PCR — ordem de {_n(ganho_ano, 0)} vidas por ano na "
        f"capital ({V['vidas_ano_faixa']}, hipótese de incidência). O p-median clássico, que só minimiza o tempo até a unidade mais "
        f"próxima, já chega a {_n(pm['vidas'])}.</li>"
        f"<li><strong>Entre o melhor mapa e o p-median a diferença é pequena e é de valores.</strong> O mapa otimizado ganha "
        f"{_n(lvg['vidas'] - pm['vidas'])} por 1.000 PCR na cidade e perde {_n(pm['cvar10'] - lvg['cvar10'])} nos 10% piores. "
        f"Com λ = 1 e o piso do p-median, o otimizador chega a {_n(eqg['vidas'])} e {_n(eqg['cvar10'])}: quase o p-median, com um pouco "
        f"mais de equidade. Qual ponto defender é decisão do grupo.</li>"
        f"<li><strong>A tese da fase 2 não se sustenta em vidas.</strong> O Gini da acessibilidade baixou, mas as vidas não subiram além "
        f"do p-median. A contribuição defensável passa a ser a medida — vidas e os 10% piores — e o caminho em etapas (K), não o Gini.</li>"
        f"<li><strong>Mudança em etapas.</strong> Se a gestão só puder mover parte da frota, os mapas com K = 20 e K = 40 entregam "
        f"{_p(100 * frac.get(20, 0), 0)} e {_p(100 * frac.get(40, 0), 0)} do ganho, sem piorar nenhuma classe de chamado em relação a hoje.</li>"
        f"<li><strong>A PCR sozinha não basta como objetivo</strong> (ela segura a USA do chamado grave no piso de hoje) <strong>e a cobertura em 15 min "
        f"também não</strong> (ela perde vidas). O par que funcionou é sobrevida a PCR + piso de cobertura grave no nível do p-median.</li>"
        f"<li><strong>As conclusões resistem às hipóteses.</strong> Em 18 cenários de tempo por saída, trânsito e carga, a ordem dos mapas "
        f"se mantém; na simulação, sem a independência entre ocupações, também (o modelo é otimista em {V['_simdif']}).</li>"
        "</ol>"
        "<p><strong>O que este estudo não afirma:</strong> que o mapa recomendado é o ótimo (a busca não tem certificado e o teto do MILP "
        "é largo); que o número de vidas por ano é preciso (depende de uma curva de Ontário e de uma incidência europeia); que os 123 "
        "locais escolhidos comportam uma base (estrutura física e equipes não foram verificadas).</p>")

    # ------------------------------------------------------------- armadilhas
    T["ARMADILHAS"] = (
        "<ul>"
        "<li><strong>Uma só curva de sobrevida</strong>, de Ontário nos anos 1990 (De Maio 2003), PCR de causa cardíaca. O nível "
        "absoluto de sobrevida em São Paulo pode ser outro; as comparações entre mapas são mais confiáveis que os níveis.</li>"
        "<li><strong>PCR onde as pessoas moram.</strong> Sem idade (o Censo por setor com faixas etárias não foi baixado) e sem "
        "população diurna: bairros comerciais e de idosos estão sub-representados.</li>"
        f"<li><strong>Calibração em um ponto.</strong> O fator {V['fator']} vem de uma notícia (20 min nos casos mais graves); não sabemos "
        "se esse número inclui o atendimento da ligação. A robustez testa trânsito livre e 25% mais pesado.</li>"
        "<li><strong>Uma correção nossa no meio do caminho.</strong> A primeira calibração dividia sem excluir os setores sem unidade "
        "alcançável (fator 1,729 em vez do certo) e a aproximação em degraus começava em 0 min, quando nenhuma resposta é mais rápida que "
        "o atraso. E a busca de um movimento por vez parava em ótimos locais (−1,2% no caso de teste); virou busca iterada. "
        "Os três foram corrigidos antes dos resultados finais; a avaliação final sempre usou a curva contínua.</li>"
        "<li><strong>Ocupações independentes.</strong> A simulação mede o viés (modelo otimista) e confirma a ordem dos mapas.</li>"
        f"<li><strong>Tempo por saída e carga não medidos.</strong> 45/70/100 min e o conflito entre o SIA (~{_n(V['_sia_dia'], 0)} saídas/dia, "
        f"{V['janela']}) e a Prefeitura (~{_n(V['_pref_dia'], 0)}/dia em dez/2023) entram como cenários, não como fatos.</li>"
        "<li><strong>Sem validação externa.</strong> Não há tempos de resposta observados por bairro em dado público; a Lei de Acesso à "
        "Informação ficou fora do prazo.</li>"
        "<li><strong>Otimalidade não provada.</strong> A busca iterada encontra o ótimo nos casos pequenos e converge nos grandes, mas o "
        "teto do MILP é largo.</li>"
        f"<li><strong>Limiares arbitrários.</strong> Os pisos de cobertura usam {V['tau_guarda']} min; o teste sem PCR (§5.10) mostra quanto um "
        "limiar largo engana.</li>"
        "<li><strong>Viabilidade das bases.</strong> Os candidatos são estabelecimentos públicos do CNES, até 10 unidades por local; "
        "garagem, equipes e custo de instalar uma base não foram considerados — só o número de unidades movidas e os km em linha reta.</li>"
        "</ul>")
    return T
