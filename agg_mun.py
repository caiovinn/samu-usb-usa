import numpy as np
import pandas as pd


def base_municipal(df, mun, apenas_publico=True):
    a = df[df.ativo].copy()
    if apenas_publico:
        a = a[a.setor.isin(["publico", "sem_fins_lucrativos"])]
    piv = (a.pivot_table(index="cod_mun", columns="modalidade",
                         values="codigo_cnes", aggfunc="count")
           .fillna(0).astype(int))
    m = mun.merge(piv, on="cod_mun", how="left")
    for c in ["USB", "USA", "MOTOLANCIA", "AEREA", "AQUATICA", "VIR",
              "RESGATE/OUTROS", "INDETERMINADO"]:
        if c not in m:
            m[c] = 0
        m[c] = m[c].fillna(0).astype(int)
    m["total"] = m[["USB", "USA", "MOTOLANCIA", "AEREA", "AQUATICA", "VIR",
                    "RESGATE/OUTROS", "INDETERMINADO"]].sum(axis=1)
    m["tem_usb"] = m.USB > 0
    m["tem_usa"] = m.USA > 0
    m["tem_qualquer"] = m.total > 0
    return m


def gini(x, w):
    """Gini de x (unidades) ponderado por w (população) — 0 = proporcional."""
    o = np.argsort(x / np.where(w == 0, np.nan, w))
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    cx, cw = np.cumsum(x) / x.sum(), np.cumsum(w) / w.sum()
    return float(1 - np.sum((cw[1:] - cw[:-1]) * (cx[1:] + cx[:-1])))
