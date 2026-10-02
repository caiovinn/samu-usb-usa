# Contexto do projeto — Realocação de USB e USA (MAI5003)

Documento de transferência de contexto. Contém o estado do trabalho, as decisões
tomadas e **por quê**, os números fechados, o que já deu errado e não deve ser
repetido, e o que vem a seguir. Escrito para ser lido por alguém — humano ou
assistente — que chega sem nenhum histórico.

Última atualização: outubro de 2026, ao fim da fase 2b (modelo de despacho
calibrado com a produção do SAMU no SIA/SUS e validado por simulação).

---

## 1. O que é

Estudo de realocação da frota móvel de urgência do SAMU separando **USB**
(Unidade de Suporte Básico) de **USA** (Unidade de Suporte Avançado). Projeto da
disciplina MAI5003 — Probabilidade e Estatística.

Grupo: Paulo Henrique Brasil Ribeiro (coordenador), Caio Oliveira (nUSP
11932272), Eduardo Próspero Santana (11320731), Lucas Martinuzzo (11930158),
Matheus de Tulio (11371291).


### Fase 1 — EDA nacional (concluída)

Arquivos na raiz do repositório. Achados que motivaram o resto:

- 5.522 unidades públicas ativas: 3.710 USB e 885 USA, razão 4,2 : 1.
- Cobertura em 20 min: 85,9% da população para USB, 66,4% para USA.
- 40,6 milhões de pessoas têm USB a ≤20 min e **nenhuma USA** nesse raio.
- Gini da frota tomando população como referência: 0,54 (USB), **0,67** (USA).
- O tamanho do município explica pouco: elasticidade de 0,42 (R² 0,57).

Conclusão da fase 1: **o problema é distribuição, não volume.**

### Fase 2 — Huff + 2SFCA bi-objetivo em São Paulo (concluída)

Tudo em `fase2_sao_paulo/`. É o objeto deste documento.

### Fase 2b — despacho calibrado pelo SIA (concluída, aguardando revisão)

Responde à crítica mais fácil ao trabalho (§6.1, "β é arbitrado"). O Huff
modela um *consumidor que escolhe*; no SAMU ninguém escolhe — o regulador manda
a **unidade disponível mais próxima**. A fase 2b troca o Huff por esse modelo
de despacho, cujo único parâmetro (a ocupação q de cada unidade) é **estimado
da produção do SAMU-SP no SIA/SUS**, e valida tudo por simulação. Ver §4.1 e
§5.1. O Huff continua sendo o padrão do código e todos os números da fase 2
seguem reprodutíveis.

---

## 2. Por que a técnica 2

O deck `metodologias_realocacao_saude.pdf` levantou quatro técnicas recentes
ainda não aplicadas a USB/USA. A escolhida foi a **técnica 2 — Huff + 2SFCA com
metaheurística bi-objetivo** (*Balancing efficiency and accessibility in
location-allocation*, Engineering Optimization, 2025), porque a novidade está no
modelo de demanda: abandona a suposição de que o usuário é sempre atendido pela
unidade mais próxima.

As outras três seguem no radar:

| técnica | fonte | papel hoje |
|---|---|---|
| RL/GNN informado por conhecimento | arXiv:2409.01588 | resolve o gargalo de escala estadual — próximo passo natural |
| ADNet, RL multi-período (pk-median) | ACM SIGSPATIAL 2024 | trabalho futuro; exige série histórica do CNES |
| BOMCLP-C, NSGA-II/MOEA-D com compacidade | EvoApplications 2026 | descartado por imaturidade |

---

## 3. Decisões de escopo e por quê

| dimensão | escolha | razão |
|---|---|---|
| recorte | município de São Paulo (3550308) | ambiente controlado: uma malha viária, 123 ambulâncias, iteração rápida |
| demanda | setores censitários do Censo 2022 | é o que o deck promete ("matriz setor↔estabelecimento") e dá resolução fina ao Huff |
| candidatos | bases SAMU atuais + UBS/UPA/hospitais públicos do CNES | realocação realista: só se move para onde já existe infraestrutura pública |

**Composição dos 1.107 candidatos** (CNES, públicos e ativos, deduplicados por
coordenada a ~11 m, filtro `TIPOS_BASE` em `monta.carrega_candidatos`): 490
UBS/centros de saúde (tipo 2, 44,3%), 265 clínicas e centros de especialidade
(36, 23,9%), 117 bases móveis do SAMU (42, 10,6%), 86 hospitais gerais (5), 67
policlínicas/AMA-AME (4), 48 prontos-atendimentos e UPA (73), 31 hospitais
especializados (7) e 3 prontos-socorros gerais (20). Os tipos 1, 15 e 21 do
filtro não têm nenhum registro em SP. Das 92 bases de hoje, **90 são do tipo
42**: a rede atual está praticamente toda nas bases próprias do SAMU, e 89% do
conjunto candidato nunca hospedou ambulância. Distribuição atual por local: 67
locais com 1 unidade, 19 com 2 e 6 com 3 — o que qualifica a afirmação de que
«quase todo local tem uma só ambulância» usada para justificar α inerte.
| distância | tempo de viagem pela rede do OpenStreetMap | credibilidade do caso urbano; linha reta em SP distorce demais |
| frota | USB e USA otimizadas em conjunto, com hierarquia | é a tese do projeto ("duas frotas, um país") |
| custo de mudança | penalidade por **distância**, não por contagem | mover para uma base a 2 km custa menos que atravessar a cidade |

---

## 4. O modelo

**Huff.** A probabilidade de o setor `i` ser atendido pelo local `j` é
proporcional a `S_j^α · f(t_ij)`, com `f` gaussiano. Substitui a regra da unidade
mais próxima.

**2SFCA hierárquico.** Essa probabilidade entra como peso nas duas etapas:
etapa 1 divide as unidades do local pela demanda esperada que o Huff manda para
lá; etapa 2 soma essas razões vistas de cada setor. Resulta num índice de
acessibilidade por setor e por modalidade.

**Hierarquia.** Dois pools sobre a mesma frota: `θ` dos chamados é grave e só
USA atende; `1-θ` escolhe entre USB e USA. A USA que atende um chamado básico
fica indisponível para o avançado.

**Objetivos, ambos minimizados.**

1. Tempo esperado de resposta, ponderado por população e gravidade.
2. Gini da acessibilidade avançada entre setores.

Os dois são necessários, e isso é demonstrável: a soma da acessibilidade
ponderada por população é **identicamente igual à oferta total** (propriedade do
2SFCA, verificada em `huff2sfca._teste`), então "maximizar acessibilidade" é
objetivo degenerado; e o Gini sozinho é minimizado concentrando toda a frota num
único ponto, o que zera a desigualdade e arruína o tempo.

### Parâmetros e a justificativa de cada um

| parâmetro | valor | justificativa |
|---|---|---|
| `BETA` | 4,5 min | ancorado no **despacho**, não no desfecho clínico: deixa 2,2 unidades efetivas por setor, a leitura de "a mais próxima disponível" quando a primeira está ocupada |
| `ALFA` | 1,0 | **inerte neste caso** — quase todo local tem uma só ambulância, então `S^α ≈ 1` |
| `D0` | 30 min | raio da área de captação |
| `THETA` | 0,10 | fração dos chamados que exige suporte avançado; arbitrado |

**β é o parâmetro que governa o modelo inteiro.** A varredura mostra:

| β (min) | unidades efetivas | E[T] mediana | Gini USA |
|---|---|---|---|
| 1,5 | 1,0 | 6,5 | 0,276 |
| 4,5 | 2,2 | 7,5 | 0,224 |
| 8,5 | 6,7 | 10,9 | 0,143 |
| 12,0 | 10,0 | 13,6 | 0,086 |

Em β = 1,5 o Huff degenera exatamente na regra da unidade mais próxima — o que
valida a implementação e, ao mesmo tempo, mostra que a novidade do método vive
inteiramente na escolha de β. **Como β empurra tempo e Gini em direções opostas,
ele desloca a fronteira antes de qualquer otimização.**

### 4.1 Modelo despacho (fase 2b)

**O problema do Huff gaussiano.** Ele usa a distância para decidir o *peso*
de cada base, mas a chance de a base mais próxima estar ocupada não depende de
quão perto ela está — depende da carga dela. Com β = 4,5, um setor a 1 min de
uma base manda 45% dos chamados para a base a 3 min; um setor a 10 min manda
só 25% para a base a 12 min. É o inverso do que acontece: o Huff exagera o
tempo perto das bases e **esconde** o tempo da periferia (lá ele supõe que a
USA distante quase nunca vem, quando na verdade ela vem toda vez que a próxima
está ocupada).

**A regra.** Cada unidade está ocupada com probabilidade q, independente das
outras (Daskin 1983, MEXCLP; ReVelle & Hogan 1989, MALP). A k-ésima unidade
mais próxima atende com probabilidade (1−q)·q^(k−1). Por local, com S_j
unidades: P(j atende i) = ∏_{l mais perto} q_l^{S_l} · (1 − q_j^{S_j}). A
distância decide a **ordem**, não o peso. `huff2sfca.despacho`; ativado com
`avalia(..., modelo="despacho", q_usb=, q_usa=)`. O 2SFCA, o Gini, o NSGA-II
e o custo de mudança ficam idênticos — a contribuição do projeto (equidade da
carga) vem do 2SFCA, não do Huff.

**Ponte β ↔ q** (mesmo número efetivo de unidades, N_ef = e^H):
N_ef(q) = exp([−(1−q)ln(1−q) − q ln q]/(1−q)), forma fechada. β(N_ef) não tem
forma fechada (depende da geometria de cada setor) e é invertido por bisseção
(`sensib_q.beta_do_n_ef`); no caso de dois locais, β = √((t₂²−t₁²)/(2·logit P₁)).

| β (min) | 1,5 | 3 | **4,5** | 6 | 8,5 |
|---|---|---|---|---|---|
| q equivalente | 0,00 | 0,07 | **0,27** | 0,47 | 0,66 |

**q estimado do SIA/SUS** (`coleta/pull_sia_samu.py` → `experimentos/demanda_samu.py`).
Códigos SIGTAP 03.01.03.012-0 (envio de USA), .013-8 (envio de USB), .017-0 e
.018-9 (transferências), conferidos na Tabela Unificada 2026-07. Janela:
maio/2025 a abril/2026 (últimos 12 meses fechados): 25.217 saídas de USA e
280.822 de USB. q = (saídas por hora × tempo de serviço) / unidades; o tempo de
serviço **não está no SIA** e é a única hipótese que sobra:

| tempo de serviço | q_USB | q_USA | β equivalente (pela USA) |
|---|---|---|---|
| 45 min | 0,22 | 0,13 | 3,5 |
| **70 min (central)** | **0,35** | **0,21** | **3,95** |
| 100 min | 0,50 | 0,30 | 4,7 |

**O β = 4,5 escolhido na fase 2 cai dentro da faixa que o dado sustenta.**
θ do dado = 0,082 (era 0,10 por hipótese). A USA é *menos* ocupada por unidade
que a USB.

| parâmetro novo | valor | onde |
|---|---|---|
| `MODELO` | "huff" (padrão) ou "despacho" | `huff2sfca.MODELO` |
| `Q` | 0,27 (equivalente a β = 4,5); o estimado fica em `sp_utilizacao.json` | `huff2sfca.Q` |
| `K_DESP` | 12 locais mais próximos; o resto pesa ~q¹² | `huff2sfca.K_DESP` |
| `TAUS` | 8, 10, 15, 20 min (cobertura probabilística da USA) | `huff2sfca.TAUS` |

---

## 5. Resultados

Configuração atual de São Paulo: 107 USB e 16 USA em 92 locais.

### Varredura de λ (preço da mudança, em minutos por km deslocado)

| λ | E[T] | Gini USA | unidades movidas | km | km/unidade |
|---|---|---|---|---|---|
| atual | 7,435 | 0,224 | — | — | — |
| 0 | 6,640 | 0,031 | 115 | 385 | 3,1 |
| 0,01 | 6,657 | 0,029 | 115 | 377 | 3,1 |
| 0,03 | 6,656 | 0,027 | 112 | 342 | 2,8 |
| 0,1 | 6,669 | 0,025 | 110 | 293 | 2,4 |
| 0,3 | 7,023 | 0,072 | 39 | 103 | 0,8 |
| 1 | 7,297 | 0,085 | 12 | 39 | 0,3 |

**Mover 12 das 123 unidades, 39 km no total, derruba o Gini de 0,224 para 0,085
— 62% do ganho de equidade com 10% do deslocamento.** E mesmo no redesenho
livre a realocação é local: 3,1 km por unidade, um salto para a esquina.

Em tempo por chamado, o mesmo λ vale muito menos, e o deck agora diz isso em
coluna própria: λ=1 devolve 0,138 min (8 s), λ=0,3 devolve 25 s, λ=0,1 devolve
0,766 min (46 s) e λ=0, 48 s. **A recomendação das doze unidades é uma decisão
de equidade, não de tempo.**

Em cobertura o efeito é pequeno porque a capital já satura: 98,24% da população
tem uma USA a ≤ 20 min hoje, 98,60% em λ=1 e 99,37% em λ=0,1 (o mesmo do
p-median). Contado em pessoas fora dos 20 minutos: 201 mil hoje, 160 mil em
λ=1, 72 mil em λ=0,1 — 64% a menos. É esta a resposta a «quanto a cobertura
aumentou», e ela explica por que o trabalho mede equidade por Gini e não por
cobertura.

Padrão geográfico em λ=1: as USA migram para leste e sul, em direção à
periferia; as USB dão saltos de poucas centenas de metros.

### Contra o baseline clássico (p-median)

| configuração | E[T] sob Huff | Gini USA | t até a mais próxima | km |
|---|---|---|---|---|
| atual | 7,435 | 0,224 | 8,84 | — |
| p-median clássico | 6,696 | 0,079 | 6,81 | 373 |
| Huff + 2SFCA (λ=0,1) | 6,669 | 0,025 | 7,17 | 293 |

### O achado que reformula a tese

**O modelo de demanda de Huff quase não muda a eficiência.** Planejar pela regra
clássica custa apenas **+0,4%** de tempo esperado mesmo quando a demanda de fato
se reparte — o p-median é robusto à hipótese de alocação, que era exatamente o
pressuposto que a técnica 2 se propunha a derrubar.

O que o arcabouço entrega é a dimensão que o p-median **não enxerga porque
ignora capacidade**: a equidade da carga, com Gini 3,1× menor e menos
deslocamento.

> A tese defensável não é "chegamos mais rápido". É "distribuímos a carga de
> forma muito mais equânime, ao mesmo tempo de resposta e com menos mudança".
> Se o artigo prometer ganho de eficiência, um revisor derruba com o próprio
> p-median.

### 5.1 Resultados da fase 2b (modelo despacho, q do SIA)

Reprodutibilidade: a matriz de tempos foi refeita sobre um OSM baixado em
out/2026 (`monta.py --so-tempos`, mesmas linhas e colunas) e a configuração
atual sob Huff β = 4,5 dá **exatamente** 7,435 min e Gini 0,2242.

**Varredura** (`experimentos/roda_tudo.py`, 29 NSGA-II em paralelo, 72 min;
`sp_q_sweep.json`). Cenário central (q_USB 0,35, q_USA 0,21):

| configuração | E[T] | Gini USA | pior decil: USA ≤ 10 min | movidas | km |
|---|---|---|---|---|---|
| atual | 5,67 | 0,206 | 0% | — | — |
| p-median | 4,56 | 0,094 | 34,5% | — | — |
| λ = 0 | 4,59 | 0,049 | 14% | 118 | 346 |
| λ = 0,1 (3 sementes) | 4,60–4,63 | 0,042–0,047 | 0–10% | 116–118 | 305–316 |
| λ = 1 (3 sementes) | 5,40–5,43 | 0,080–0,091 | 0% | 17–21 | 40–46 |
| λ = 0,1 com restrição | 4,59–4,60 | 0,061–0,064 | 26–31% | 116–119 | 312–326 |
| λ = 1 com restrição | 4,95–5,02 | 0,038–0,045 | 25–26% | 88–90 | 173–199 |

1. **O achado de equidade sobrevive, menor.** Em λ = 0,1, mesmo tempo do
   p-median e Gini 2,1× menor (sob Huff: 2,8× com o `sp_resultado.json`
   atual; 3,1× na tabela do §5 — ver a nota sobre divergência no §8). O "pacote barato" de λ = 1 (~20 unidades,
   ~45 km) entrega 73–80% do ganho de equidade no cenário central e 74–93%
   entre os cenários de q. Ruído do NSGA-II entre sementes: ±0,005 de Gini.
2. **O Huff superestimava o tempo**: 7,44 → 5,67 min para a rede atual.
3. **Achado novo: minimizar o Gini da acessibilidade deixa o pior decil
   descoberto.** Os 10% da população com pior cobertura têm ~0% de chance de
   USA em 10 min nas soluções "equânimes"; o p-median dá 34,5%. Gini de
   unidades por habitante não é equidade de tempo de chegada.
4. **Com a restrição "pior decil ≥ 25% em 10 min"** o redesenho quase não
   perde nada (tempo igual, Gini 0,043 → 0,062, ainda melhor que o p-median),
   mas **o pacote barato deixa de existir**: cumprir a restrição exige ~90
   unidades e ~180 km. Cobrir a periferia é redesenho, não ajuste fino.
   (Nas linhas com restrição o Gini de λ = 1 sai *menor* que o de λ = 0: é o
   joelho, normalizado pela faixa de cada fronteira, caindo em regiões
   diferentes — não comparar essas duas linhas entre si.)

**Validação por simulação** (`experimentos/simula.py`, `sp_simulacao.json`,
`figs/fase2/sp_07_validacao.png`): a cidade simulada chamado a chamado por um
ano, Poisson nas taxas do SIA, regulador real (grave → USA mais próxima livre;
básico → USB mais próxima livre, USA só se nenhuma USB estiver livre), fila
quando todas ocupadas; 6 configurações × 3 tempos de serviço × 3 sementes.

- Cobertura do pior decil em 10 min: modelo e simulação concordam em ~1 ponto
  em todos os casos (p-median 34,5 vs 34,0%).
- Tempo esperado do chamado grave: o modelo é **otimista em 0,2–0,9 min**,
  mais quanto maior a carga — é a independência entre ocupações (vizinhas se
  ocupam juntas).
- O tempo total simulado fica ~0,5–0,8 min acima do analítico porque no
  modelo a USA disputa o chamado básico em pé de igualdade com a USB; na
  simulação ela é preservada.
- **A ordem das configurações é a mesma** nos dois. Fila praticamente não
  ocorre (~0% dos chamados esperam).

---

## 6. Limitações conhecidas

1. **β é arbitrado, não estimado** — *mitigado na fase 2b*: o modelo despacho
   troca β por q, estimado do SIA, e o β = 4,5 cai dentro da faixa equivalente
   (3,5–4,7). Continua sem dado de escolha individual (qual unidade atendeu
   qual chamado), e o **tempo de serviço** que converte saídas em ocupação é
   hipótese (45/70/100 min). q é da cidade inteira: o SIA fatura em 227 CNES e
   só 34% do volume cai nas bases atuais, então não há q por base.
2. **α é inerte.** De α=1 para α=2 o tempo esperado vai de 11,78 a 11,80 min.
   Só passaria a importar se surgissem bases com 3-4 unidades.
3. **Não há fila nem ocupação** — *mitigado na fase 2b*: o modelo despacho
   usa ocupação, e a simulação mostra que a fila é desprezível na frota atual.
   Resta a independência entre ocupações (modelo otimista em 0,2–0,9 min no
   chamado grave) e a demanda constante ao longo do dia.
4. **Tempos sem trânsito.** A malha do OSM em fluxo livre subestima o
   deslocamento real, provavelmente de forma desigual pela cidade.
5. **Demanda = população residente.** Sem perfil etário, sem incidência de
   agravos, sem variação dia/noite.
6. **Heurísticas, não ótimo.** NSGA-II e p-median são heurísticos; o p-median
   ficou 1,15% acima do ótimo exato em instâncias pequenas.
7. **Um município, não a rede.** São Paulo é densa e bem servida; nada aqui se
   transfere direto para o estado, que é onde a desigualdade da fase 1 aparecia.
8. **O Gini da acessibilidade não protege o pior decil** (fase 2b, §5.1).
   Sem uma restrição de cobertura, as soluções "equânimes" deixam ~10% da
   população sem chance real de USA em 10 min.
9. **Motolância fora do modelo.** O SIA mostra a produção da motolância
   (03.01.03.019-7) subindo de ~1 mil para ~7 mil por mês em 2024–2026; ela
   chega antes da ambulância em parte dos casos graves e não está modelada.

---

## 7. Próximos passos, em ordem de prioridade

0. **Cobertura da USA em faixas mais curtas que 20 min.** C(20) **já existe** —
   está em `pct_usa_20min` nas fronteiras e em `huff_usa20` no
   `sp_comparacao.json` — mas satura na capital e por isso quase não separa
   configurações: 98,24% hoje, 98,60% em λ=1 e 99,37% em λ=0,1 e no p-median.
   O ganho só fica legível contado em gente (201 mil → 160 mil → 72 mil fora
   dos 20 min). Variar τ para 5, 8 e 10 minutos é uma linha de código e devolve
   a métrica mais intuitiva para quem lê de fora. **Não repetir o erro de dizer
   que a cobertura não foi calculada: foi.**
1. ~~**Sensibilidade em β.**~~ Feita (β ∈ {2; 4,5; 8,5}, `sensib_beta.py`) e
   superada pela fase 2b: β substituído por q estimado do SIA (§4.1, §5.1).
1b. **Escolher o segundo objetivo.** Gini da carga ou cobertura do pior
   decil? A fase 2b mostra que eles divergem; a versão com restrição (§5.1) é
   o meio-termo. Decisão do grupo antes de escrever o artigo.
1c. **Tempo de serviço real.** É o único insumo de q que continua hipótese;
   qualquer fonte (relatório da SMS-SP, literatura do SAMU) estreita a faixa
   45–100 min.
2. **Demanda por incidência, não por população.** Ponte natural para o modelo
   bayesiano CAR/ICAR já previsto.
3. **Escalar para o estado com a técnica 1 (RL/GNN).** SP é o piloto; o gargalo
   de escala é exatamente o que aquela técnica resolve.
4. ~~**Disponibilidade em vez de pressão.**~~ Feito na fase 2b (modelo
   despacho + simulação de eventos discretos). Próximo passo possível: fator
   de correção de Larson (1975) / Budge, Ingolfsson & Erkut (2009) para a
   dependência entre ocupações.
5. **ADNet multi-período** como extensão, se houver fôlego para reconstruir a
   série histórica do CNES.

---

## 8. Mapa de arquivos

O repositório é organizado por fase (`fase1_nacional/`, `fase2_sao_paulo/`) e,
dentro de cada fase, por responsabilidade: `coleta/` (baixa dados brutos),
`modelo/` (funções/classes reutilizáveis, sem I/O de arquivo), `experimentos/`
(scripts que rodam o pipeline e gravam em `dados/`/`figs/`), `docs/` (gera
relatório/decks — os "produtos finais" para leitura humana) e `testes/`.
Caminhos (`RAIZ`/`DADOS`/`FIG`/`RAW`) ficam centralizados em
`<fase>/caminhos.py` — nenhum script deveria montar esses caminhos na mão.

### `fase1_nacional/`
```
coleta/       pull_ibge.py, pull_malha.py, pull_sedes.py, pull_cnes.py, pull_sr.py
modelo/       classif.py, base_frota.py, agg_mun.py, acesso.py
experimentos/ build_municipal.py, tabelas.py, figuras.py
docs/         eda_usb_usa.ipynb, relatorio_usb_usa.html, resultados.txt
```

### `fase2_sao_paulo/`
```
coleta/pull_dados.py          coleta bruta — RODA NA MÁQUINA DO USUÁRIO (ver §9)
experimentos/monta.py         _raw/ -> dados/fase2/sp_setores, sp_candidatos, sp_tempos.npy
modelo/huff2sfca.py           o modelo (Huff, 2SFCA hierárquico, Gini, tempo esperado)
modelo/otimiza.py             NSGA-II com checkpoint + busca local + joelho()
modelo/mudanca.py             custo de realocação (emparelhamento ótimo, Hungaro)
modelo/pmedian.py             baseline clássico (guloso + troca de vértices)
experimentos/roda.py          driver: baseline, varredura de λ, fronteiras
experimentos/compara.py       as três configurações nas duas métricas
experimentos/sensib_beta.py   sensibilidade em β
coleta/pull_sia_samu.py       SIA/SUS do DATASUS -> producao SAMU de SP (roda local, ~15 min)
experimentos/demanda_samu.py  theta e ocupacao q de USB/USA -> sp_utilizacao.json, sp_06
experimentos/sensib_q.py      ponte beta<->q, reproducao, reavaliacao barata -> sp_q_sens.json
experimentos/roda_tudo.py     orquestrador da fase 2b: varredura NSGA-II em paralelo -> sp_q_sweep.json
experimentos/simula.py        simulacao de eventos discretos (validacao) -> sp_simulacao.json, sp_07
docs/deck_despacho.js         apresentacao passo a passo da fase 2b (.pptx)
docs/revisao_literatura.html  revisao de literatura: 22 estudos (tecnicas do projeto + outras abordagens), DOIs conferidos no Crossref
experimentos/figuras.py       figs/fase2/sp_*.png
testes/teste_monta.py         testes geométricos contra força bruta
docs/deck_gera.js             gerador da apresentação de resultados (.pptx)
docs/deck_didatico.js         gerador da apresentação didática (.pptx)
docs/formulas_gera.py         renderiza fórmulas em LaTeX -> figs/fase2/formulas/*.png
docs/relatorio_gera.py        gerador do relatório HTML
```
Cada módulo de `modelo/` roda sozinho e executa o próprio teste:
`uv run python -m fase2_sao_paulo.modelo.huff2sfca`.

### `dados/fase2/`
`sp_setores.parquet`, `sp_candidatos.parquet`, `sp_tempos.npy` (matriz,
reconstruível, fora do git), `sp_pareto_lam*.parquet`, `sp_pareto_x_lam*.npy`,
`sp_resultado.json`, `sp_comparacao.json`, `sp_pmedian_x.npy`,
`sp_beta_sens.json`; fase 2b: `sp_utilizacao.json`, `sp_q_sens.json`,
`sp_q_sweep.json`, `sp_simulacao.json` (versionáveis, pequenos) e, fora do git,
`sp_samu_producao.parquet` e `varredura_q/` (fronteiras e checkpoints dos 29 jobs)

**Divergência a resolver:** o `sp_resultado.json` versionado hoje tem, em
λ = 1, 10 unidades / 48 km / Gini 0,057 e, em λ = 0,1, Gini 0,028 — não os
12 / 39 / 0,085 e 0,025 das tabelas do §5. É ruído do NSGA-II entre execuções
(o JSON foi regravado depois que as tabelas foram escritas). Os decks leem o
JSON; este documento, as tabelas. Decidir qual execução é a de referência.

### `figs/fase2/`
`sp_01_pareto.png` · `sp_02_ganho_km.png` · `sp_03_mapa_troca.png` ·
`sp_04_lorenz.png` · `sp_05_comparacao.png` · `sp_06_producao_samu.png` ·
`sp_07_validacao.png` · `formulas/*.png`

### Entregáveis
`fase2_sao_paulo/docs/apresentacao_usb_usa_sp.pptx` (resultados) ·
`fase2_sao_paulo/docs/apresentacao_didatica_samu.pptx` (didático) ·
`fase1_nacional/docs/relatorio_usb_usa.html` (fase 1) ·
`fase2_sao_paulo/docs/relatorio_resultados_sp.html` (fase 2)

O slide 5, **«Como ler os números»**, foi acrescentado depois de a primeira
versão ser criticada por não definir as métricas. Ele fixa, num lugar só: os
**dois defaults** (a rede operada hoje, 7,44 min / Gini 0,224, que é a
referência de ganho; e o p-median, 6,70 / 0,079, que é o comparador
metodológico), a **definição de equidade** (Gini de \(A^A_i\) entre os 26.889
setores, 0 = mesma fatia de USA por habitante para todos), a unidade de cada
métrica e o reconhecimento explícito de que C(τ) ainda não foi calculado para
SP. Quem editar o deck deve manter essas definições sincronizadas com
`matematica_usb_usa.html`. A tabela do slide traz cinco métricas — E[T], tempo
até a mais próxima, C(20), Gini da acessibilidade avançada e custo da mudança —
com a coluna «Hoje» fixando o valor da rede atual em cada uma.

---

## 9. Como rodar

Montagem do ambiente: **[SETUP.md](SETUP.md)**, a única lista de dependências
do projeto. O grupo usa `uv` com Python 3.12 fixado em `.python-version` e as
versões travadas em `uv.lock` (ambos versionados).

```bash
uv sync
uv run python -m fase2_sao_paulo.coleta.pull_dados   # SÓ ESTA ETAPA PRECISA DE REDE
uv run python -m fase2_sao_paulo.experimentos.monta
uv run python -m fase2_sao_paulo.experimentos.roda        # varre todos os λ
uv run python -m fase2_sao_paulo.experimentos.compara
uv run python -m fase2_sao_paulo.experimentos.figuras
```

Fase 2b, numa máquina com núcleos sobrando (16 threads: ~15 min de SIA +
~75 min de varredura + ~2 min de simulação):

```bash
uv run python -m fase2_sao_paulo.coleta.pull_dados osm          # se faltar o grafo
uv run python -m fase2_sao_paulo.experimentos.monta --so-tempos # so a matriz, sem mexer nos candidatos
uv run python -m fase2_sao_paulo.experimentos.roda_tudo --workers 13
uv run python -m fase2_sao_paulo.experimentos.simula
npm ci && node fase2_sao_paulo/docs/deck_despacho.js
```

`roda_tudo` é retomável: cada etapa e cada job são pulados se a saída existe.
Numa máquina nova o `uv` e o Node instalam por `winget install astral-sh.uv`
e `winget install OpenJS.NodeJS.LTS`.

**Restrição de ambiente importante.** Os sandboxes do Claude só alcançam PyPI e
GitHub; `ftp.ibge.gov.br`, `apidadosabertos.saude.gov.br` e o OpenStreetMap
respondem 403 na política de egresso. Por isso `pull_dados.py` roda na máquina
do usuário e todo o resto trabalha sobre `fase2_sao_paulo/_raw/`.

Requisito herdado da fase 1: **numpy ≥ 2 com matplotlib ≥ 3.9**. A máquina
original tinha numpy 2.4.6 junto de matplotlib 3.6.2, scipy 1.9.3, shapely
2.0.2 e geopandas 0.14.1 — todos compilados contra numpy 1.x, e nenhum
carregava. **Foi essa dor que motivou trocar o venv manual pelo `uv`:** ele
fixa o próprio interpretador, não só os pacotes, então a combinação errada não
volta. O ambiente travado hoje é Python 3.12.14 com numpy 2.5.3, pandas 2.3.3,
scipy 1.18.1, matplotlib 3.11.2 e pyarrow 25.0.1.

**Um clone novo não roda o modelo.** `fase2_sao_paulo/_raw/` e
`dados/fase2/sp_tempos.npy` estão no `.gitignore` (grandes e reconstruíveis),
e `roda.py`, `compara.py` e `figuras.py` abrem a matriz de tempos direto. Rode
`pull_dados.py` + `monta.py` antes de qualquer outra coisa.

---

## 10. Armadilhas já encontradas — não repetir

Cada uma destas custou uma rodada de depuração e está corrigida no código.

- **Busca do nó viário mais próximo.** Parar no primeiro anel da grade espacial
  com candidato errava 224 de 300 pontos: como a distância é escalada por
  cos(latitude), o vizinho mais próximo pode estar dois anéis adiante.
- **Arestas paralelas do OSM.** `csr_matrix((w,(u,v)))` **soma** as paralelas em
  vez de tomar a menor — duas ruas entre os mesmos cruzamentos virariam uma
  aresta com o dobro do tempo. Fundir pelo mínimo antes.
- **Corte de tempo no Dijkstra.** O fallback em Python puro deixava vazar nós
  logo além do limite, divergindo do `limit` do scipy.
- **Coordenadas do CNES.** 23 registros compartilham uma coordenada de fábrica
  errada em (-23,32, -46,38), fora do município — o "CECO Parque Ibirapuera"
  aparece a 17 km da malha viária. O filtro de bounding box nacional não pega
  isso. Descartar por distância de encaixe.
- **Orientação das matrizes.** Fatiar colunas de uma matriz de 119 MB custa
  34 ms; fatiar linhas, 2,6 ms. A matriz de tempo é guardada com os
  **candidatos nas linhas**. Com o decaimento pré-calculado e float32 com BLAS,
  a avaliação caiu de 54 ms para 10,5 ms.
- **Semear o NSGA-II.** Sem a solução do p-median na população inicial, a
  metaheurística **perdia** para a heurística clássica no eixo do tempo
  (6,77 contra 6,70 min). Com a semente: 6,64.
- **Duas definições de "joelho da fronteira".** O joelho precisa ser escolhido
  no mesmo espaço que o otimizador usou (tempo **penalizado**). Havia duas
  definições divergentes no projeto, e o mapa saiu com 16 setas para uma solução
  que a tabela dizia ter 12 realocações. Agora há uma função só,
  `otimiza.joelho`, e os resultados gravam `f_obj`.
- **Fronteira plotada no espaço errado.** A frente guardada para λ > 0 foi
  ordenada no espaço penalizado; plotada no tempo puro deixa de ser fronteira e
  vira um zigue-zague. Refiltrar o não-dominado no espaço exibido.
- **Processos em background na VM.** Não sobrevivem entre chamadas do shell
  remoto, nem com `setsid`. Daí o checkpoint do NSGA-II e o parâmetro
  `ORCAMENTO`.
- **A curva de Lorenz tem de começar na origem.** O somatório dos trapézios em
  `huff2sfca.gini` pulava a primeira fatia, `(cw[0]-0)·(cx[0]+0)`. Com isso o
  Gini de uma distribuição *perfeitamente igual* não dava 0 e sim `cw[0]·cx[0]`
  — um piso cujo tamanho depende de qual elemento o `argsort` deixou em
  primeiro no empate, o que é comportamento indefinido: no caso degenerado do
  teste ia de 6e-8 a 1,4e-5 conforme a ordem, 200× de diferença. O teste do
  módulo quebrou ao trocar de versão do numpy, que desempata diferente. O viés
  é da ordem de 1e-9 nos 26.889 setores de SP — **nenhum número publicado
  muda** —, mas o caso degenerado agora é asserção fixa em `_teste()`.
- **Clone novo: não rodar `monta.py` inteiro.** Ele reconstrói os candidatos
  do CNES de hoje e muda os índices de que dependem `sp_pmedian_x.npy` e
  `sp_pareto_x_*.npy`. Para só refazer a matriz: `monta.py --so-tempos`.
- **SIA, fevereiro de 2024.** 216.626 envios de USB contra 19.356
  atendimentos (~10×): erro de faturamento. `demanda_samu` troca envio > 3×
  atendimento pelo atendimento do mês e registra em `anomalias_corrigidas`.
- **Ler o DBF do SIA com `dbfread` é lento demais** (python puro, minutos por
  arquivo de 1–2 GB). O DBF é largura fixa: memmap como matriz uint8 e filtro
  por comparação de bytes — 7 s por arquivo.
- **Despacho é 6× mais lento que o Huff** (76 vs 13 ms por avaliação): o
  gargalo é o `argpartition`, serial. Por isso a varredura paraleliza por job
  com uma thread de BLAS cada (`OMP_NUM_THREADS=1`), e não por threads.
- **Joelho com restrição.** Escolher o joelho só entre as soluções viáveis
  (`viavel` na fronteira); a penalidade empurra as inviáveis para longe mas
  elas ainda podem aparecer se a busca for curta.

---

## 11. Glossário

| termo | significado |
|---|---|
| USB / USA | Unidade de Suporte Básico / Avançado. Só a USA leva médico e desfibrilador |
| 2SFCA | *Two-Step Floating Catchment Area*, índice de acessibilidade que considera capacidade |
| Huff | modelo de escolha probabilística entre destinos concorrentes |
| p-median | minimiza a distância média até a instalação mais próxima, ignorando capacidade |
| NSGA-II | algoritmo evolutivo multiobjetivo com ordenação por não-dominância |
| λ | preço da mudança, em minutos de resposta por km deslocado |
| β | decaimento de distância do Huff, em minutos |
| θ | fração dos chamados que exige suporte avançado |
| E[T] | tempo esperado de resposta sob o modelo de demanda em uso (Huff ou despacho) |
| despacho | regra do regulador: a unidade *disponível* mais próxima atende |
| q | ocupação de uma unidade: fração do tempo em que ela está fora da base |
| pior decil | os 10% da população com menor cobertura; métrica `cob_usa_10_p10` |
| SIA / SIGTAP | sistema de produção ambulatorial do SUS / tabela de procedimentos que codifica o que é faturado |
