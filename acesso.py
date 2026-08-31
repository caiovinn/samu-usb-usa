"""Distância/tempo estimado até a unidade mais próxima de cada modalidade."""
import numpy as np, pandas as pd

VEL_KMH, SINUOSIDADE = 55.0, 1.35


def haversine_km(lat1, lon1, lat2, lon2):
    """Matriz (n1 x n2) de distâncias em km."""
    la1, lo1 = np.radians(lat1)[:, None], np.radians(lon1)[:, None]
    la2, lo2 = np.radians(lat2)[None, :], np.radians(lon2)[None, :]
    a = (np.sin((la1 - la2) / 2) ** 2
         + np.cos(la1) * np.cos(la2) * np.sin((lo1 - lo2) / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def coords_validas(df):
    """Coordenada plausível dentro do território brasileiro."""
    return (df.lat.between(-34.0, 5.5) & df.lon.between(-74.0, -34.0)
            & df.lat.notna() & df.lon.notna())


def tempo_ate_mais_proxima(m, unidades, bloco=400):
    """m: base municipal com lat_mun/lon_mun. unidades: subset da frota."""
    u = unidades[coords_validas(unidades)]
    if len(u) == 0:
        return np.full(len(m), np.nan)
    mins = np.empty(len(m))
    for i in range(0, len(m), bloco):
        s = slice(i, min(i + bloco, len(m)))
        d = haversine_km(m.lat_mun.values[s], m.lon_mun.values[s],
                         u.lat.values, u.lon.values)
        mins[s] = d.min(axis=1)
    return mins * SINUOSIDADE / VEL_KMH * 60.0


