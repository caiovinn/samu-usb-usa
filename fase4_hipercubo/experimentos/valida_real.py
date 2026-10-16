"""Hipercubo aproximado x simulacao de eventos discretos, nos dados reais de SP.

Reusa, SEM refazer, a simulacao da fase 3 (dados/fase3/v5_simulacao.json): 13
configuracoes (hoje, p-median, fases 2/2b, solucoes da fase 3) x 3 tempos de
servico x 3 sementes. Para as mesmas configuracoes e servicos, calcula o modelo
hipercubo (variantes larson75, local, daskin) e compara com a simulacao, ao lado
do modelo da fase 3 (ocupacao independente e igual por classe, 'an_*').

Atencao a diferenca de definicao: a guarda cob_basico da fase 3 ('an_cob_basico')
e so USB; a simulacao e o hipercubo aqui usam a regra real (USB, depois USA).

Uso: uv run python -m fase4_hipercubo.experimentos.valida_real
Saida: dados/fase4/v_real_vs_sim.json
"""
import json
import time

import numpy as np
import pandas as pd

from fase3_vidas.experimentos import vidas as V

from ..caminhos import DADOS, DADOS_FASE3
from ..modelo import hc_real as HR

MODELOS = HR.VARIANTES + ("larson75_ida",)      # _ida = servico dependente do deslocamento
METRICAS = (("vidas", "sim_vidas", "an_vidas"), ("cob_grave", "sim_cob_grave", "an_cob_grave"),
            ("cob_basico", "sim_cob_basico", "an_cob_basico"), ("et_grave", "sim_et_grave", "an_et_grave"),
            ("et_basico", "sim_et_basico", "an_et_basico"))


def roda():
    sim = json.load(open(DADOS_FASE3 / "v5_simulacao.json", encoding="utf-8"))
    servicos = sim["servicos"]
    df = pd.DataFrame(sim["rodadas"]).groupby(["config", "servico"], sort=False).mean(numeric_only=True).reset_index()
    fin = V.finalistas()
    f, a = V.fator()
    tx = HR.taxas_sia()
    linhas = []
    for _, r in df.iterrows():
        yB, yA = fin[r["config"]]
        l = {"config": r["config"], "servico": r["servico"]}
        for m, s, an in METRICAS:
            l[f"sim_{m}"], l[f"fase3_{m}"] = float(r[s]), float(r[an])
        l["sim_q_usb"], l["sim_q_usa"] = float(r["sim_q_usb"]), float(r["sim_q_usa"])
        for var in MODELOS:
            h = HR.avalia(yB, yA, f, a, servicos[r["servico"]], tx, variante=var.replace("_ida", ""),
                          servico_ida=var.endswith("_ida"))
            for m, _, _ in METRICAS:
                l[f"{var}_{m}"] = h[m]
            l[f"{var}_q_usb"], l[f"{var}_q_usa"], l[f"{var}_cob_basico_usb"] = h["q_usb"], h["q_usa"], h["cob_basico_usb"]
        linhas.append(l)
    return pd.DataFrame(linhas)


def resume(df):
    out = {}
    mods = ("fase3",) + MODELOS
    for serv in ["central", "baixo", "alto", "todos"]:
        d = df if serv == "todos" else df[df.servico == serv]
        for m, _, _ in METRICAS:
            e = {}
            for mod in mods:
                dif = d[f"{mod}_{m}"] - d[f"sim_{m}"]
                e[mod] = dict(vies=float(dif.mean()), mae=float(dif.abs().mean()), max_abs=float(dif.abs().max()))
            out[f"{serv}:{m}"] = e
        # ordem das configuracoes por vidas: correlacao de Spearman com a simulacao
        rk = {}
        for mod in mods:
            rk[mod] = float(d[f"{mod}_vidas"].rank().corr(d["sim_vidas"].rank()))
        out[f"{serv}:spearman_vidas"] = rk
    return out


if __name__ == "__main__":
    t0 = time.time()
    df = roda()
    res = resume(df)
    (DADOS / "v_real_vs_sim.json").write_text(json.dumps(dict(
        nota="sim = media de 3 sementes (v5_simulacao.json); fase3 = modelo independente; "
             "cob_basico: fase3 e so USB, sim e hipercubo usam USB depois USA",
        linhas=df.to_dict("records"), resumo=res), indent=1), encoding="utf-8")
    print(f"{len(df)} casos em {time.time() - t0:.0f}s")
    mods = ("fase3",) + MODELOS
    for serv in ("central", "todos"):
        print(f"\n=== servico {serv}: vies | erro absoluto medio (modelo - simulacao) ===")
        print(f"{'metrica':12s}" + "".join(f"{m:>26s}" for m in mods))
        for m, _, _ in METRICAS:
            e = res[f"{serv}:{m}"]
            print(f"{m:12s}" + "".join(f"{e[k]['vies']:>+13.3f}{e[k]['mae']:>13.3f}" for k in mods))
        print("Spearman(vidas, sim):", {k: round(v, 3) for k, v in res[f"{serv}:spearman_vidas"].items()})
    c = df[df.servico == "central"]
    print("\nvidas, servico central: config | sim | fase3 | larson75 | local | daskin | larson75_ida")
    for _, r in c.iterrows():
        print(f"  {r['config']:28s} {r['sim_vidas']:6.2f} {r['fase3_vidas']:6.2f} {r['larson75_vidas']:6.2f} "
              f"{r['local_vidas']:6.2f} {r['daskin_vidas']:6.2f} {r['larson75_ida_vidas']:6.2f}")
