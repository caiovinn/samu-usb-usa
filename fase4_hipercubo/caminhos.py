"""Caminhos centrais da fase 4 (modelo hipercubo de Larson como avaliador).

Mesmo padrao das fases 2 e 3. A fase 4 le da fase 2 os setores, candidatos,
tempos e a utilizacao, e da fase 3 as solucoes publicadas; grava so em
dados/fase4 e figs/fase4 — as fases anteriores ficam intocadas.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "fase4"
DADOS_FASE2 = RAIZ / "dados" / "fase2"
DADOS_FASE3 = RAIZ / "dados" / "fase3"
FIG = RAIZ / "figs" / "fase4"
LOGS = RAIZ / "logs"

DADOS.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
