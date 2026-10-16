"""Caminhos centrais da fase 2 (Huff + 2SFCA, Sao Paulo capital).

Um lugar so para a raiz do repo e as pastas de dados/figuras/brutos -- antes
disso, `RAIZ`/`DADOS`/`FIG` eram recalculados com `Path(__file__).resolve()
.parent...` em quase todo arquivo de `fase2_sao_paulo/`. Com um nivel a mais de pasta
(coleta/, modelo/, experimentos/, docs/, testes/), repetir essa conta em
cada arquivo exigiria trocar `.parent.parent` por `.parent.parent.parent`
em todos ao mesmo tempo -- import este modulo em vez disso.

DADOS_FASE1 existe porque `experimentos/monta.py` le
`dados/fase1/frota.parquet`, que e produzido pela fase 1 -- a unica
dependencia entre as duas fases do projeto.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "fase2"
DADOS_FASE1 = RAIZ / "dados" / "fase1"
FIG = RAIZ / "figs" / "fase2"
RAW = Path(__file__).resolve().parent / "_raw"

DADOS.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
