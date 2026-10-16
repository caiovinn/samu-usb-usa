import json
import numpy as np, pandas as pd
from fase1_nacional.caminhos import DADOS
from fase1_nacional.modelo.agg_mun import gini

df = pd.read_parquet(DADOS / "frota.parquet")
m = pd.read_parquet(DADOS / "municipal.parquet")
a = df[df.ativo]
pub = a[a.setor.isin(["publico", "sem_fins_lucrativos"])]
P = m.populacao.sum()
R = {}

R["universo"] = {
    "tipo42_cadastradas": int(len(df)),
    "ativas": int(df.ativo.sum()),
    "desabilitadas": int((~df.ativo).sum()),
    "ativas_publicas": int(len(pub)),
    "ativas_privadas": int((a.setor == "privado").sum()),
    "sem_coordenada": int(df.lat.isna().sum()),
    "class_por_servico_cnes": int((a.fonte_class == "servico_cnes").sum()),
    "class_por_nome": int((a.fonte_class == "nome_fantasia").sum()),
    "nao_classificada": int((a.fonte_class == "nao_classificada").sum()),
    "nome_indeterminado_pct": float((a.cls_nome == "INDETERMINADO").mean() * 100),
}
R["modalidades"] = {k: int(v) for k, v in pub.modalidade.value_counts().items()}
R["razao_usb_usa"] = float(R["modalidades"]["USB"] / R["modalidades"]["USA"])
R["hab_por_USB"] = float(P / R["modalidades"]["USB"])
R["hab_por_USA"] = float(P / R["modalidades"]["USA"])
R["pop_total"] = float(P)

R["presenca"] = {
    "mun_com_qualquer": int(m.tem_qualquer.sum()),
    "mun_com_usb": int(m.tem_usb.sum()),
    "mun_com_usa": int(m.tem_usa.sum()),
    "pct_pop_mun_com_usb": float(m.loc[m.tem_usb, "populacao"].sum() / P * 100),
    "pct_pop_mun_com_usa": float(m.loc[m.tem_usa, "populacao"].sum() / P * 100),
}
R["gini"] = {"USB": gini(m.USB.values, m.populacao.values),
             "USA": gini(m.USA.values, m.populacao.values)}

for suf, nome in [("", "sede"), ("_cent", "centroide")]:
    d = {}
    for mod in ("USB", "USA"):
        t = m[f"t_{mod}{suf}"]
        d[mod] = {"mediana": float(t.median()), "p90": float(t.quantile(.9))}
        for L in (10, 20, 30, 60):
            d[mod][f"pop_{L}min"] = float(m.loc[t <= L, "populacao"].sum() / P * 100)
            d[mod][f"mun_{L}min"] = float((t <= L).mean() * 100)
    R[f"acesso_{nome}"] = d

usb20, usa20 = m.t_USB <= 20, m.t_USA <= 20
R["lacuna_20min"] = {
    "ambos": float(m.loc[usb20 & usa20, "populacao"].sum() / P * 100),
    "so_usb": float(m.loc[usb20 & ~usa20, "populacao"].sum() / P * 100),
    "so_usb_mi": float(m.loc[usb20 & ~usa20, "populacao"].sum() / 1e6),
    "nenhum": float(m.loc[~usb20 & ~usa20, "populacao"].sum() / P * 100),
    "nenhum_mi": float(m.loc[~usb20 & ~usa20, "populacao"].sum() / 1e6),
}

c = m[m.total > 0]
for rot, sub, col in [("total", c, "total"), ("USB", m[m.USB > 0], "USB"),
                      ("USA", m[m.USA > 0], "USA")]:
    b, a0 = np.polyfit(np.log(sub.populacao), np.log(sub[col]), 1)
    yh = a0 + b * np.log(sub.populacao)
    r2 = 1 - ((np.log(sub[col]) - yh) ** 2).sum() / \
             ((np.log(sub[col]) - np.log(sub[col]).mean()) ** 2).sum()
    R.setdefault("elasticidade", {})[rot] = {"beta": float(b), "r2": float(r2),
                                             "n": int(len(sub))}

pop_uf = m.groupby("uf_sigla").populacao.sum()
u = pub.pivot_table(index="uf_sigla", columns="modalidade",
                    values="codigo_cnes", aggfunc="count").fillna(0)
uf = pd.DataFrame({
    "pop_mi": pop_uf / 1e6,
    "USB": u.USB, "USA": u.USA,
    "USB_100k": u.USB / pop_uf * 1e5, "USA_100k": u.USA / pop_uf * 1e5,
    "cob_USB_20": m.groupby("uf_sigla").apply(
        lambda d: d.loc[d.t_USB <= 20, "populacao"].sum() / d.populacao.sum() * 100,
        include_groups=False),
    "cob_USA_20": m.groupby("uf_sigla").apply(
        lambda d: d.loc[d.t_USA <= 20, "populacao"].sum() / d.populacao.sum() * 100,
        include_groups=False),
}).round(2)
uf["lacuna_pp"] = (uf.cob_USB_20 - uf.cob_USA_20).round(2)
uf.sort_values("cob_USA_20").to_csv(DADOS / "tabela_uf.csv")

faixas = [0, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5, 5e5, 1e10]
rot = ["<5k", "5-10k", "10-20k", "20-50k", "50-100k", "100-200k", "200-500k", ">=500k"]
m["faixa"] = pd.cut(m.populacao, faixas, labels=rot, right=False)
fx = m.groupby("faixa", observed=True).apply(lambda d: pd.Series({
    "municipios": len(d), "pop_mi": d.populacao.sum() / 1e6,
    "pct_com_USB": d.tem_usb.mean() * 100, "pct_com_USA": d.tem_usa.mean() * 100,
    "USB": d.USB.sum(), "USA": d.USA.sum(),
    "hab_por_USB": d.populacao.sum() / max(d.USB.sum(), 1),
    "hab_por_USA": d.populacao.sum() / max(d.USA.sum(), 1),
    "cob_USA_20": d.loc[d.t_USA <= 20, "populacao"].sum() / d.populacao.sum() * 100,
}), include_groups=False).round(1)
fx.to_csv(DADOS / "tabela_faixas.csv")

json.dump(R, open(DADOS / "resultados.json", "w"), indent=2, ensure_ascii=False)
print(json.dumps(R, indent=2, ensure_ascii=False))
print(); print(uf.to_string()); print(); print(fx.to_string())
