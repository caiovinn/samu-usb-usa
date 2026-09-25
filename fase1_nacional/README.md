# EDA — USB e USA

Análise exploratória da frota móvel de urgência do SAMU separando **Unidade de
Suporte Básico (USB)** de **Unidade de Suporte Avançado (USA)**. É o passo
anterior ao MCLP do `../../prototipo_samu.ipynb`, que hoje trata toda ambulância
como equivalente.

## Por onde começar

| arquivo | o que é |
|---|---|
| `docs/eda_usb_usa.ipynb` | o caderno, já executado com todas as saídas |
| `docs/relatorio_usb_usa.html` | relatório fechado, para leitura ou entrega |
| `docs/resultados.txt` | todos os números em texto, para conferir |

## Achados principais

- 5.522 unidades públicas ativas: **3.710 USB** e **885 USA** (4,2 : 1).
- Cobertura em 20 min: **85,9%** da população para USB, **66,4%** para USA.
- **40,6 milhões de pessoas** têm USB a ≤20 min e nenhuma USA nesse raio.
- Só 619 dos 5.570 municípios (11,1%) têm alguma USA no próprio território.
- Gini da frota tomando população como referência: 0,54 (USB), **0,67** (USA).
- Elasticidade de `log(unidades)` contra `log(população)`: **0,42** (R² 0,57).

## Estrutura

```
caminhos.py            RAIZ/DADOS/FIG/RAW centralizados — importe em vez de montar path na mão

coleta/pull_ibge.py    população, área e densidade (Censo 2022, agregado 4714)
coleta/pull_malha.py   centroides municipais (malha do IBGE, sem shapely)
coleta/pull_sedes.py   sedes municipais — FONTE DE TERCEIROS, ver cabeçalho do arquivo
coleta/pull_cnes.py    unidades tipo 42 (API de Dados Abertos do MS) — com coordenada
coleta/pull_sr.py      grupo SR do CNES via pysus — traz CLASS_SR (USB vs USA)

modelo/classif.py      regex de nome fantasia + carregadores
modelo/base_frota.py   mapa CLASS_SR -> modalidade; monta uma linha por unidade
modelo/agg_mun.py      agrega por município; Gini
modelo/acesso.py       haversine e tempo até a unidade mais próxima

experimentos/build_municipal.py  gera dados/fase1/municipal.parquet
experimentos/tabelas.py          todos os números -> dados/fase1/resultados.json + CSVs
experimentos/figuras.py          todas as figuras -> figs/fase1/

docs/                  eda_usb_usa.ipynb, relatorio_usb_usa.html, resultados.txt
```

Os `coleta/pull_*.py` só precisam rodar de novo para atualizar a competência
do CNES. Tudo o mais lê de `dados/fase1/`.

## Ambiente

**Ver [../SETUP.md](../SETUP.md)** — é a única lista de dependências do
projeto.

Resumo: o projeto usa `uv`, com Python 3.12 fixado no repositório. Todo
comando roda a partir da **raiz do repositório**, não desta pasta:

```bash
uv sync                                              # monta o ambiente exato do uv.lock
uv run python -m fase1_nacional.experimentos.tabelas
```

O motivo de existir um gerenciador: esta fase precisa de **numpy ≥ 2 com
matplotlib ≥ 3.9**, e a máquina original tinha numpy 2.4.6 ao lado de
matplotlib 3.6.2, scipy 1.9.3, shapely 2.0.2 e geopandas 0.14.1 — todos
compilados contra numpy 1.x, e nenhum deles carregava. Daí o código da fase 1
evitar scipy e shapely.
