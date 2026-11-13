# Fase 5 — otimização global e robusta com o hipercubo

A fase 4 deixou um **avaliador** bom (o hipercubo de Larson) e uma **busca**
fraca. A fase 5 conserta a busca, mantendo o problema das fases 3 e 4:

- sempre partindo da **rede de hoje** (CNES: 107 USB + 16 USA em 92 locais);
- objetivo J = vidas + λ · CVaR10 (por 1.000 PCR);
- guardas: cobertura básica (USB) e do grave (USA) em 15 min ≥ as de hoje;
- no máximo K unidades movidas desde hoje.

## O que muda na busca (`modelo/busca_global.py`)

1. **Máscara de K na triagem.** Com a solução no limite K, a busca das fases 3/4
   propunha destinos que estouravam K; eram recusados e a unidade não se movia.
   Agora só destinos permitidos entram na triagem.
2. **Triagem com a ocupação de cada unidade** (`modelo/triagem.py`), atualizada a
   cada troca aceita, em vez do q igual por tipo.
3. **Chutes que respeitam K** na busca iterada (na fase 4, com K = 20/40, nenhum
   chute chegava a ser testado).
4. **Avaliador com desempate fixo** (`modelo/avaliador.py`): mesmo resultado do
   `hc_real` da fase 4, sem o ruído de até ~0,004 vidas que fazia a busca aceitar
   "melhoras" falsas.

## Como rodar (Windows, na raiz do repositório)

```bash
uv sync                                                                   # uma vez
uv run python -m fase5_otimizacao.modelo.avaliador                        # teste (~1 min)
uv run python -m fase5_otimizacao.experimentos.roda_busca --teste         # ~2 min
uv run python -m fase5_otimizacao.experimentos.roda_busca --workers 6     # as 60 buscas
uv run python -m fase5_otimizacao.experimentos.roda_busca --etapa resumo
uv run python -m fase5_otimizacao.experimentos.roda_busca --etapa simula
```

- **Workers:** cada processo usa ~1,2 GB de memória e um núcleo. Use
  `min(núcleos - 1, memória em GB / 1,5)`.
- **Retomável:** cada busca grava `dados/fase5/busca/<nome>.json` ao terminar e é
  pulada se já existir. Pode interromper com Ctrl+C e rodar de novo.
- **Guarda do grave mais apertada (opcional):** `--guarda-grave fase3` exige a
  cobertura do grave do mapa da fase 3 de mesmo (λ, K). Grava em
  `dados/fase5/busca_gg_fase3/`; use a mesma opção no `resumo` e no `simula`.

## Pré-requisito: a matriz de tempos

`dados/fase2/sp_tempos.npy` não vem no clone. Ela tem de ser gerada com o
código atual e os candidatos da main:

```bash
uv run python -m fase2_sao_paulo.experimentos.monta --so-tempos
```

Com o grafo do OSM desta máquina ela reproduz a fase 3 em 0,03% (vidas) e
0,5% (CVaR10); a simulação reproduz exatamente os números da fase 4. Uma matriz
antiga, montada sobre outra lista de candidatos, dava ~40 vidas onde o certo é ~54.

## Arquivos

| arquivo | o que é |
|---|---|
| `modelo/avaliador.py` | hipercubo com desempate fixo (teste: igual ao `hc_real`) |
| `modelo/triagem.py` | triagem por q igual ("q") ou ocupação de cada unidade ("rho") |
| `modelo/busca_global.py` | busca local + busca iterada, com máscara de K |
| `experimentos/linha_base.py` | 43 mapas das fases anteriores pela mesma régua → `dados/fase5/linha_base.json` |
| `experimentos/triagem_qualidade.py` | a ordem da triagem acerta o hipercubo? → `dados/fase5/triagem_qualidade.json` |
| `experimentos/roda_busca.py` | as 60 buscas, resumo e validação por simulação |

Arquivos de `dados/fase5/` que começam com `_` são de teste.
