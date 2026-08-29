"""Monta a base analítica: uma linha por unidade móvel (CNES TP_UNID = 42)."""
import numpy as np
import pandas as pd
from classif import carrega_api, carrega_sr

# CLASS_SR -> modalidade. Mapa derivado empiricamente (ver 03_validacao):
# a concordância com o nome fantasia é > 98% em 002 e 003.
MAPA_CLASS = {
    "001": "RESGATE/OUTROS",
    "002": "USB",
    "003": "USA",
    "005": "AQUATICA",
    "006": "VIR",
    "007": "RESGATE/OUTROS",
    "008": "RESGATE/OUTROS",
    "010": "MOTOLANCIA",
    "011": "AQUATICA",
    "012": "AEREA",
}
MODALIDADES = ["USB", "USA", "MOTOLANCIA", "AEREA", "AQUATICA", "VIR",
               "RESGATE/OUTROS", "INDETERMINADO"]


def monta():
    api = carrega_api()
    sr = carrega_sr()

    s103 = (sr[sr.SERV_ESP == "103"]
            .drop_duplicates(["codigo_cnes", "CLASS_SR"])
            .sort_values("CLASS_SR"))
    # unidade com mais de uma classificação: fica a primeira (raro, ~180 casos)
    s103 = s103.drop_duplicates("codigo_cnes")[["codigo_cnes", "CLASS_SR"]]

    df = api.merge(s103, on="codigo_cnes", how="left")
    df["cls_servico"] = df.CLASS_SR.map(MAPA_CLASS)
    df["modalidade"] = df.cls_servico.fillna(df.cls_nome)
    df["fonte_class"] = np.where(df.cls_servico.notna(), "servico_cnes",
                        np.where(df.cls_nome != "INDETERMINADO", "nome_fantasia",
                                 "nao_classificada"))

    nj = df.descricao_natureza_juridica_estabelecimento.astype(str).str[:1]
    df["setor"] = np.select([nj == "1", nj == "2", nj == "3"],
                            ["publico", "privado", "sem_fins_lucrativos"],
                            default="outro")

    mun = pd.read_parquet("municipios_ibge.parquet")
    df = df.merge(mun[["cod_mun6", "cod_mun", "municipio", "populacao",
                       "area_km2", "densidade", "uf_sigla", "regiao"]],
                  left_on="codigo_municipio", right_on="cod_mun6", how="left")

    df["lat"] = df.latitude_estabelecimento_decimo_grau
    df["lon"] = df.longitude_estabelecimento_decimo_grau
    return df, mun
