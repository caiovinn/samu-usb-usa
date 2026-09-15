# EDA — USB e USA

Análise exploratória da frota móvel de urgência do SAMU separando **Unidade de
Suporte Básico (USB)** de **Unidade de Suporte Avançado (USA)**. É o passo
anterior ao MCLP do `../prototipo_samu.ipynb`, que hoje trata toda ambulância
como equivalente.

## Por onde começar

| arquivo | o que é |
|---|---|
| `eda_usb_usa.ipynb` | o caderno, já executado com todas as saídas |
| `relatorio_usb_usa.html` | relatório fechado, para leitura ou entrega |
| `resultados.txt` | todos os números em texto, para conferir |

## Achados principais

- 5.522 unidades públicas ativas: **3.710 USB** e **885 USA** (4,2 : 1).
- Cobertura em 20 min: **85,9%** da população para USB, **66,4%** para USA.
- **40,6 milhões de pessoas** têm USB a ≤20 min e nenhuma USA nesse raio.
- Só 619 dos 5.570 municípios (11,1%) têm alguma USA no próprio território.
- Gini da frota tomando população como referência: 0,54 (USB), **0,67** (USA).
- Elasticidade de `log(unidades)` contra `log(população)`: **0,42** (R² 0,57).

## Estrutura

```
pull_ibge.py     população, área e densidade (Censo 2022, agregado 4714)
pull_malha.py    centroides municipais (malha do IBGE, sem shapely)
pull_sedes.py    sedes municipais — FONTE DE TERCEIROS, ver cabeçalho do arquivo
pull_cnes.py     unidades tipo 42 (API de Dados Abertos do MS) — com coordenada
pull_sr.py       grupo SR do CNES via pysus — traz CLASS_SR (USB vs USA)

classif.py       regex de nome fantasia + carregadores
base_frota.py    mapa CLASS_SR -> modalidade; monta uma linha por unidade
agg_mun.py       agrega por município; Gini
acesso.py        haversine e tempo até a unidade mais próxima
build_municipal.py  gera dados/municipal.parquet

tabelas.py       todos os números -> dados/resultados.json + CSVs
figuras.py       todas as figuras -> figs/
```

Os `pull_*.py` só precisam rodar de novo para atualizar a competência do CNES.
Tudo o mais lê de `dados/`.

## Ambiente

**Ver [SETUP.md](SETUP.md)** — é a única lista de dependências do projeto.

Resumo: o projeto usa `uv`, com Python 3.12 fixado no repositório.

```bash
uv sync                  # monta o ambiente exato do uv.lock
uv run python tabelas.py
```

O motivo de existir um gerenciador: esta fase precisa de **numpy ≥ 2 com
matplotlib ≥ 3.9**, e a máquina original tinha numpy 2.4.6 ao lado de
matplotlib 3.6.2, scipy 1.9.3, shapely 2.0.2 e geopandas 0.14.1 — todos
compilados contra numpy 1.x, e nenhum deles carregava. Daí o código da fase 1
evitar scipy e shapely.
