"""Centroides municipais a partir da malha do IBGE.

Sem shapely de proposito: o shapely 2.0.2 instalado neste ambiente nao carrega
com numpy 2.4.6. O centroide sai do anel externo de maior area, via formula do
poligono (shoelace) — nao e o representative_point do shapely, mas para
municipio convexo-ish a diferenca e irrelevante no protótipo.
"""
import time
import numpy as np, pandas as pd, requests

from fase1_nacional.caminhos import DADOS

UFS = [11,12,13,14,15,16,17,21,22,23,24,25,26,27,28,29,31,32,33,35,
       41,42,43,50,51,52,53]


def aneis(geom):
    """Devolve a lista de aneis externos (lista de pares lon/lat)."""
    t, c = geom["type"], geom["coordinates"]
    return [c[0]] if t == "Polygon" else [p[0] for p in c]


def centroide(geom):
    melhor, area_max = None, -1.0
    for anel in aneis(geom):
        p = np.asarray(anel, dtype=float)
        x, y = p[:, 0], p[:, 1]
        cross = x[:-1] * y[1:] - x[1:] * y[:-1]
        a = cross.sum() / 2.0
        if abs(a) < 1e-12:
            continue
        cx = ((x[:-1] + x[1:]) * cross).sum() / (6 * a)
        cy = ((y[:-1] + y[1:]) * cross).sum() / (6 * a)
        if abs(a) > area_max:
            melhor, area_max = (cx, cy), abs(a)
    return melhor


linhas = []
for uf in UFS:
    url = (f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}"
           f"?formato=application/vnd.geo+json&intrarregiao=municipio"
           f"&qualidade=minima")
    for t in range(4):
        try:
            geo = requests.get(url, timeout=300).json(); break
        except Exception:
            if t == 3: raise
            time.sleep(3 * (t + 1))
    for f in geo["features"]:
        c = centroide(f["geometry"])
        if c is None:
            continue
        linhas.append({"cod_mun": int(f["properties"]["codarea"]),
                       "lon_mun": c[0], "lat_mun": c[1]})
    print(f"UF {uf}: {len(geo['features'])} municipios", flush=True)

pd.DataFrame(linhas).to_parquet(DADOS / "centroides.parquet")
print("FIM", len(linhas))
