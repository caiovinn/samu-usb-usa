"""Classificação USB / USA das unidades móveis (CNES TP_UNID = 42)."""
import glob
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- nome fantasia
PADROES = [
    ("AEREA",   r"A[EÉ]REO|A[EÉ]REA|HELIC|AEROM|AEROTAXI|AEROMEDIC"),
    ("AQUATICA", r"FLUVIAL|LANCHA|EMBARCA|AQUAT|BARCO|AMBULANCHA"),
    ("MOTOLANCIA", r"MOTOL[AÂ]NCIA|MOTOCICL|\bURAM\b|\bMOTO\b|\bMC\d"),
    ("USA",     r"\bUSA\b|\bUSAV?\b|SUPORTE\s+AVAN[CÇ]|UTI\s*M[OÓ]VEL|"
                r"\bSAV\b|AVAN[CÇ]AD"),
    ("USB",     r"\bUSB\b|\bUSBV?\b|SUPORTE\s+B[AÁ]SIC|\bB[AÁ]SIC"),
]

def classifica_nome(s):
    n = s.fillna("").str.upper()
    out = pd.Series("INDETERMINADO", index=n.index, dtype=object)
    for rot, pat in PADROES:                  # ordem importa: aereo/moto antes
        out = out.mask((out == "INDETERMINADO") & n.str.contains(pat, regex=True),
                       rot)
    return out


def carrega_api():
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob("cnes42/*.parquet"))],
                   ignore_index=True)
    df = df.drop_duplicates("codigo_cnes")
    df["ativo"] = df.codigo_motivo_desabilitacao_estabelecimento.isna()
    df["cls_nome"] = classifica_nome(df.nome_fantasia)
    return df


def carrega_sr():
    sr = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob("cnes_sr/*.parquet"))],
                   ignore_index=True)
    sr["codigo_cnes"] = pd.to_numeric(sr.CNES, errors="coerce").astype("Int64")
    return sr
