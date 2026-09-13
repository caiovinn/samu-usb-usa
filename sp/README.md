# Fase 2 — Huff + 2SFCA bi-objetivo, São Paulo capital

Primeira versão do estudo com a **técnica 2** do deck de atualização, restrita
ao município de São Paulo (3550308) para ter um ambiente controlado.

## Decisões de escopo

| dimensão | escolha |
|---|---|
| demanda | setores censitários do Censo 2022 (~31 mil em SP) |
| candidatos | bases SAMU atuais + UBS/UPA/hospitais públicos do CNES |
| distância | tempo de viagem pela rede viária do OSM |
| frota | USB e USA otimizadas em conjunto, com hierarquia de gravidade |

## Modelo

Huff substitui a regra da unidade mais próxima: a probabilidade de o setor `i`
ser atendido pelo local `j` é proporcional a `S_j^α · f(t_ij)`, com decaimento
gaussiano `f`. Essa probabilidade entra como peso nas duas etapas do 2SFCA
(Luo 2014), o que dá um índice de acessibilidade por setor e por modalidade.

Hierarquia: uma fração `θ` dos chamados é grave e só pode ser atendida por USA;
o restante escolhe entre USB e USA. São dois pools de demanda sobre a mesma
frota, e a pressão sobre cada USA soma os dois.

Objetivos (ambos minimizados):

1. **tempo esperado** de resposta, ponderado por população e gravidade
2. **Gini** da acessibilidade avançada entre setores

Os dois são necessários. Sozinha, a acessibilidade agregada é degenerada — a
soma ponderada por população é idêntica à oferta total, propriedade do 2SFCA
verificada em `huff2sfca._teste`. E o Gini sozinho é minimizado concentrando
toda a frota num único ponto, que zera a desigualdade e arruína o tempo.

Parâmetros em `huff2sfca.py`: `BETA=8.5` min (f(10 min) ≈ 0,5), `ALFA=1.0`,
`D0=30` min, `THETA=0.10`. Como não há dado de escolha real para calibrar o
Huff, a análise de sensibilidade sobre β e α faz parte do resultado.

## Custo de mudança

Otimizar só tempo e equidade produz uma rede que realoca praticamente todas as
unidades — inútil como recomendação. O terceiro eixo é o **preço da mudança**:
não quantas unidades se movem, mas quantos quilômetros a frota precisa
percorrer para assumir a nova configuração. Como ambulâncias da mesma
modalidade são intercambiáveis, isso é um emparelhamento de custo mínimo entre
posições de origem e destino (`mudanca.py`), resolvido pelo Hungaro exato —
que, medido, sai mais barato que um guloso em laço Python (0,27 ms contra
0,67 ms).

`λ` converte quilômetro de mudança em minuto de resposta e entra no objetivo de
tempo. Varrer λ de 0 (redesenho livre) a 1 (rede quase congelada) dá a curva de
quanto ganho cada quilômetro compra.

## Figuras

```
sp_01_pareto.png      fronteiras de Pareto por λ, com atual e p-median marcados
sp_02_ganho_km.png    ganho de equidade e de tempo contra quilômetro deslocado
sp_03_mapa_troca.png  as 12 realocações de λ=1, com seta de origem a destino
sp_04_lorenz.png      Lorenz da acessibilidade a USA nas três configurações
sp_05_comparacao.png  as três configurações nas quatro métricas
```

Duas armadilhas que as figuras revelaram e que o código agora evita:

- A fronteira guardada para λ > 0 foi ordenada no espaço **penalizado**; plotada
  no tempo puro ela deixa de ser uma fronteira e vira um zigue-zague.
  `_nao_dominada` refiltra no espaço exibido.
- O "joelho" da fronteira precisa ser escolhido no mesmo espaço em que o
  otimizador trabalhou. Havia duas definições no projeto, e o mapa saiu com 16
  setas para uma solução que a tabela dizia ter 12 realocações. Agora há uma
  função só, `otimiza.joelho`, e os resultados gravam `f_obj`.

## Resultados (São Paulo, β = 4,5)

Configuração atual: E[T] 7,44 min, Gini da acessibilidade USA 0,224.

| λ | E[T] | Gini | unidades movidas | km | km/unidade |
|---|---|---|---|---|---|
| 0 | 6,64 | 0,031 | 115 | 385 | 3,1 |
| 0,1 | 6,67 | 0,025 | 110 | 293 | 2,4 |
| 0,3 | 7,02 | 0,072 | 39 | 103 | 0,8 |
| 1 | 7,30 | 0,085 | 12 | 39 | 0,3 |

Movendo **12 unidades por 39 km no total**, o Gini cai de 0,224 para 0,085 —
62% do ganho de equidade com 10% do deslocamento.

### Contra o baseline clássico

O `pmedian.py` resolve o p-median que o protótipo atual do projeto usa (toda
ambulância equivalente, todo setor atendido pela mais próxima). Avaliando as
três configurações nas duas métricas:

| configuração | E[T] sob Huff | Gini USA | t até a mais próxima |
|---|---|---|---|
| atual | 7,435 | 0,224 | 8,84 |
| p-median clássico | 6,696 | 0,079 | 6,81 |
| Huff + 2SFCA | 6,669 | 0,025 | 7,17 |

**O modelo de demanda de Huff quase não muda a eficiência.** Planejar pela
regra clássica custa apenas +0,4% de tempo esperado quando a demanda de fato se
reparte — o p-median é robusto à hipótese de alocação. O que o arcabouço
Huff+2SFCA entrega é a dimensão que o p-median não enxerga, porque ignora
capacidade: a **equidade da carga**, com Gini 3,1× menor e menos deslocamento
(293 km contra 373 km). Este é o argumento honesto do artigo — não vender ganho
de tempo que o método não produz.

## Arquivos

```
pull_dados.py   coleta bruta — RODA NA MÁQUINA DO USUÁRIO, não no sandbox
monta.py        _raw/ -> dados/sp_setores, sp_candidatos, sp_tempos.npy
huff2sfca.py    o modelo (Huff, 2SFCA hierárquico, Gini, tempo esperado)
otimiza.py      NSGA-II com codificação inteira + busca local 1-opt
mudanca.py      custo de realocação (emparelhamento ótimo entre origens e destinos)
pmedian.py      baseline clássico: p-median guloso + troca de vértices
roda.py         driver do experimento: baseline, varredura de λ, fronteiras
compara.py      as três configurações avaliadas nas duas métricas
figuras.py      todas as figuras -> figs/sp_*.png
teste_monta.py  testes das partes geométricas contra força bruta
```

Um detalhe de desempenho que moldou o código: a matriz de tempo é guardada com
os **candidatos nas linhas**. O otimizador só usa as linhas dos locais
ocupados, e fatiar linhas contíguas custa 2,6 ms contra 34 ms de fatiar as
colunas equivalentes. Junto com o decaimento pré-calculado e float32 com BLAS,
a avaliação caiu de 54 ms para 10,5 ms.

Cada módulo roda sozinho (`python sp/huff2sfca.py`) e executa o próprio teste.

## Por que a coleta roda fora

Os ambientes do Claude só alcançam PyPI e GitHub; `ftp.ibge.gov.br`,
`apidadosabertos.saude.gov.br` e o OSM respondem 403 na política de egresso.
`pull_dados.py` é a única etapa que precisa da rede — o resto trabalha sobre
`sp/_raw/`.

```bash
pip install "numpy>=2" pandas pyarrow requests osmnx
python sp/pull_dados.py            # ou: python sp/pull_dados.py setores
python sp/monta.py                 # precisa de geopandas; scipy é opcional
```
