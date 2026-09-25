"""Caminhos centrais da fase 1 (EDA nacional USB/USA).

Um lugar so para a raiz do repo e as pastas de dados/figuras -- antes disso,
cada script usava nomes de arquivo relativos ao cwd ("frota.parquet", sem
pasta), o que so funcionava se o processo fosse iniciado com `dados/` como
diretorio de trabalho (nada documentado garantia isso). Import este modulo
em vez de repetir a conta de `Path(__file__)` em cada script.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "fase1"
FIG = RAIZ / "figs" / "fase1"
RAW = Path(__file__).resolve().parent / "_raw"

DADOS.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
