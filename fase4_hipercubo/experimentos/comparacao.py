"""Comparacao das fases com AS MESMAS metricas, avaliando cada mapa de bases de duas formas:

  modelo anterior  ocupacao independente e igual por classe (fases 2b e 3)
  hipercubo        ocupacao endogena por unidade (Larson 1975), fase 4

Metricas (as da fase 2/2b/3): tempo medio (f_tempo, min, tempos brutos do OSM), Gini da
acessibilidade avancada (f_gini), cobertura da USA em 10 min nos 10% piores (cob_usa_10_p10),
vidas por 1.000 PCR, CVaR10 (sobrevida nos 10% piores, por 1.000 PCR), ambulancias movidas e km.
A simulacao (independente) entra como referencia nas vidas, no CVaR e no tempo do grave.

Uso: uv run python -m fase4_hipercubo.experimentos.comparacao
Saida: dados/fase4/h_comparacao.json
"""
import json

import numpy as np
import pandas as pd

from fase2_sao_paulo.modelo import huff2sfca as H
from fase3_vidas.experimentos import vidas as V

from ..caminhos import DADOS, DADOS_FASE3
from ..modelo import hc_real as HR

# (rotulo, fase, chave no finalistas() da fase 3  ou  chave em h_simulacao.json)
CONFIGS = (
    ("hoje (rede atual)", "base", "hoje"),
    ("p-median (clássico)", "fase 2", "p-median"),
    ("fase 2: Huff + Gini, lam=0,1", "fase 2", "fase2 lam=0.1"),
    ("fase 2b: despacho + Gini, lam=0,1", "fase 2b", "fase2b central lam=0.1"),
    # objetivo: so vidas (lam = 0)
    ("fase 3: vidas, K=20", "fase 3", "vidas lam=0 K=20"),
    ("fase 3: vidas, K=40", "fase 3", "vidas lam=0 K=40"),
    ("fase 3: vidas, K livre", "fase 3", "vidas lam=0 K=livre"),
    ("fase 4: hipercubo, K=20", "fase 4", "hc lam=0 K=20"),
    ("fase 4: hipercubo, K=40", "fase 4", "hc lam=0 K=40"),
    ("fase 4: hipercubo, K livre", "fase 4", "hc lam=0 K=livre"),
    ("fase 4: reotimiza a fase 3, K livre", "fase 4", "reot vidas lam=0 K=livre"),
    # objetivo: vidas + CVaR10 (lam = 1)
    ("fase 3: vidas + CVaR, K=40", "fase 3", "vidas lam=1 K=40"),
    ("fase 3: vidas + CVaR, K livre", "fase 3", "vidas lam=1 K=livre"),
    ("fase 4: hipercubo + CVaR, K=40", "fase 4", "hc lam=1 K=40"),
    ("fase 4: hipercubo + CVaR, K livre", "fase 4", "hc lam=1 K=livre"),
    ("fase 4: reotimiza a fase 3 + CVaR, K livre", "fase 4", "reot vidas lam=1 K=livre"),
)


def main():
    f, a = V.fator()
    D = V.dados()
    th = D["U"]["theta_dados"]
    qb, qa = V.qs()
    tx = HR.taxas_sia()
    fin = V.finalistas()
    h4 = json.load(open(DADOS / "h_simulacao.json", encoding="utf-8"))
    sim3 = pd.DataFrame(json.load(open(DADOS_FASE3 / "v5_simulacao.json", encoding="utf-8"))["rodadas"])
    sim3 = sim3[sim3.servico == "central"].groupby("config", sort=False).mean(numeric_only=True)
    sim4 = pd.DataFrame(h4["rodadas"]).groupby("config", sort=False).mean(numeric_only=True)
    out = {}
    for rot, fase, chave in CONFIGS:
        if chave in fin:
            yB, yA = fin[chave]
        else:
            yB, yA = np.array(h4["hc"][chave]["yB"]), np.array(h4["hc"][chave]["yA"])
        iB, iA = V.indices(yB, yA)
        ant2 = H.avalia(D["T"], D["pop"], iB, iA, modelo="despacho", q_usb=qb, q_usa=qa, theta=th, detalhe=True)
        ant3 = V.mede(yB, yA, f, a)
        hc = HR.avalia(yB, yA, f, a, 70.0, tx, variante="larson75", fase2=True)
        mv, km = V.mudanca(yB, yA)
        sim = sim3.loc[chave] if chave in sim3.index else (sim4.loc[chave] if chave in sim4.index else None)
        out[rot] = dict(
            fase=fase, chave=chave, movidas=mv, km=km,
            anterior=dict(f_tempo=ant2["f_tempo"], f_gini=ant2["f_gini"], cob_usa_10_p10=ant2["cob_usa_10_p10"],
                          vidas=ant3["vidas"], cvar10=ant3["cvar10"], et_grave=ant3["et_grave"]),
            hipercubo=dict(f_tempo=hc["f_tempo"], f_gini=hc["f_gini"], cob_usa_10_p10=hc["cob_usa_10_p10"],
                           vidas=hc["vidas"], cvar10=hc["cvar10"], et_grave=hc["et_grave"]),
            simulacao=None if sim is None else dict(vidas=float(sim["sim_vidas"]), vidas_pior_decil=float(sim["sim_vidas_pior_decil"]),
                                                    et_grave=float(sim["sim_et_grave"])))
    (DADOS / "h_comparacao.json").write_text(json.dumps(dict(theta=th, fator=f, atraso=a, servico_min=70.0, configs=out),
                                                         indent=1, ensure_ascii=False), encoding="utf-8")
    cab = f"{'configuracao':38s} mov | tempo(min) ant/HC | Gini ant/HC | cob10 p10(%) ant/HC | vidas ant/HC/sim | CVaR10 ant/HC/sim"
    print(cab)
    for k, v in out.items():
        a_, h_, s_ = v["anterior"], v["hipercubo"], v["simulacao"]
        sv = f"{s_['vidas']:5.1f}" if s_ else "  -  "
        sc = f"{s_['vidas_pior_decil']:5.1f}" if s_ else "  -  "
        print(f"{k:38s} {v['movidas']:3d} | {a_['f_tempo']:.2f}/{h_['f_tempo']:.2f} | {a_['f_gini']:.3f}/{h_['f_gini']:.3f} | "
              f"{a_['cob_usa_10_p10']:5.1f}/{h_['cob_usa_10_p10']:5.1f} | {a_['vidas']:5.1f}/{h_['vidas']:5.1f}/{sv} | "
              f"{a_['cvar10']:5.1f}/{h_['cvar10']:5.1f}/{sc}")


if __name__ == "__main__":
    main()
