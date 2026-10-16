"""Coordenadas das sedes municipais.

FONTE DE TERCEIROS — declarar no trabalho. O repositório
kelvins/municipios-brasileiros republica as coordenadas de sede de origem IBGE
em CSV. Não é endpoint oficial do IBGE e não tem SLA nem versionamento formal;
foi usado porque a API de localidades do IBGE (v1) devolve nome e hierarquia
mas *não* devolve coordenada de sede.

Alternativas oficiais, se a procedência precisar ser inatacável:
  - BCIM / Base Cartográfica Contínua do IBGE, camada de sedes municipais
    (download manual, shapefile);
  - IBGE Geociências > Localidades > "Localidades v1" (arquivo fixo, não API).

O uso aqui é como *ponto de referência da população* do município. A alternativa
já implementada e sem dependência externa é o centroide do polígono
(pull_malha.py) — a §8 do caderno mostra que a escolha entre os dois vale ~15
p.p. de cobertura.
"""
import io

import pandas as pd
import requests

from fase1_nacional.caminhos import DADOS

URL = ("https://raw.githubusercontent.com/kelvins/municipios-brasileiros"
       "/main/csv/municipios.csv")

r = requests.get(URL, timeout=120)
r.raise_for_status()
df = pd.read_csv(io.StringIO(r.text))

esperado = {"codigo_ibge", "latitude", "longitude"}
faltando = esperado - set(df.columns)
assert not faltando, f"colunas ausentes na fonte: {faltando}"

df.to_parquet(DADOS / "sedes.parquet")
print(f"{len(df)} sedes -> sedes.parquet")
print(df[["codigo_ibge", "nome", "latitude", "longitude"]].head())
