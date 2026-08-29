import numpy as np, pandas as pd
from agg_mun import base_municipal
from acesso import haversine_km, tempo_ate_mais_proxima

df = pd.read_parquet("frota.parquet")
mun = pd.read_parquet("municipios_ibge.parquet")
cen = pd.read_parquet("centroides.parquet")
sed = (pd.read_parquet("sedes.parquet")
       .rename(columns={"codigo_ibge": "cod_mun", "latitude": "lat_sede",
                        "longitude": "lon_sede"})
       [["cod_mun", "lat_sede", "lon_sede"]])

m = (base_municipal(df, mun)
     .merge(cen.rename(columns={"lat_mun": "lat_cent", "lon_mun": "lon_cent"}),
            on="cod_mun", how="left")
     .merge(sed, on="cod_mun", how="left"))

m["d_cent_sede_km"] = np.diag(haversine_km(m.lat_cent.values, m.lon_cent.values,
                                           m.lat_sede.values, m.lon_sede.values))

# 6 sedes do CSV caem fora do proprio municipio (erro da fonte). Onde a
# distancia passa de 2,5x o raio do circulo de area equivalente, usa o centroide.
raio = np.sqrt(m.area_km2 / np.pi)
suspeita = m.d_cent_sede_km > 2.5 * raio
m.loc[suspeita, ["lat_sede", "lon_sede"]] = m.loc[suspeita, ["lat_cent", "lon_cent"]].values
m["sede_corrigida"] = suspeita

frota = df[df.ativo & df.setor.isin(["publico", "sem_fins_lucrativos"])]
for suf, (clat, clon) in {"": ("lat_sede", "lon_sede"),
                          "_cent": ("lat_cent", "lon_cent")}.items():
    ref = m[[clat, clon]].rename(columns={clat: "lat_mun", clon: "lon_mun"})
    for mod in ("USB", "USA"):
        m[f"t_{mod}{suf}"] = tempo_ate_mais_proxima(ref, frota[frota.modalidade == mod])

m.to_parquet("municipal.parquet")
print(m.shape, "-> municipal.parquet")
