"""Caminhos centrais da fase 5 (otimizacao global e robusta com o hipercubo).

Mesmo padrao das fases 2-4. A fase 5 le da fase 2 os setores, candidatos e
tempos, da fase 3 as solucoes publicadas e da fase 4 o avaliador e as buscas;
grava so em dados/fase5 e figs/fase5 -- as fases anteriores ficam intocadas.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "fase5"
DADOS_FASE2 = RAIZ / "dados" / "fase2"
DADOS_FASE3 = RAIZ / "dados" / "fase3"
DADOS_FASE4 = RAIZ / "dados" / "fase4"
FIG = RAIZ / "figs" / "fase5"
LOGS = RAIZ / "logs"

DADOS.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
