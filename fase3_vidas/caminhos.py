"""Caminhos centrais da fase 3 (vidas salvas: sobrevida a PCR, otimizacao exata).

Mesmo padrao de fase2_sao_paulo/caminhos.py. A fase 3 nao recoleta nada: le
da fase 2 a matriz de tempos, os setores, os candidatos, a ocupacao estimada
do SIA e as solucoes ja publicadas, e grava so em dados/fase3 e figs/fase3 —
a fase 2 fica intocada e reprodutivel.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "fase3"
DADOS_FASE2 = RAIZ / "dados" / "fase2"
FIG = RAIZ / "figs" / "fase3"
LOGS = RAIZ / "logs"

DADOS.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
