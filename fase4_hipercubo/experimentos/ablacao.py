"""Ablacao: de onde vem a melhora do hipercubo sobre o modelo da fase 3?

Mesmo codigo de avaliacao (hc_real.avalia), tres ocupacoes por unidade:
  fixa      rho = q da classe (0,35 USB / 0,21 USA): reproduz o modelo da fase 3
  endogena  rho do ponto fixo de Larson, SEM fator de correcao (daskin)
  larson75  rho do ponto fixo COM o fator Q' do artigo
A diferenca fixa -> endogena e o efeito da ocupacao diferente por unidade; a diferenca
endogena -> larson75 e o efeito da dependencia entre ocupacoes (a correcao de Larson).

Uso: uv run python -m fase4_hipercubo.experimentos.ablacao
Saida: dados/fase4/h_ablacao.json
"""
import json

import numpy as np
import pandas as pd

from fase3_vidas.experimentos import vidas as V

from ..caminhos import DADOS, DADOS_FASE3
from ..modelo import hc_real as HR

CONFIGS = ("hoje", "p-median", "fase2b central lam=0.1", "vidas lam=0 K=20", "vidas lam=0 K=40",
           "vidas lam=0 K=livre", "vidas lam=1 K=livre")


def main():
    f, a = V.fator()
    tx = HR.taxas_sia()
    fin = V.finalistas()
    q = V.qs("central")
    sim = pd.DataFrame(json.load(open(DADOS_FASE3 / "v5_simulacao.json", encoding="utf-8"))["rodadas"])
    sim = sim[sim.servico == "central"].groupby("config", sort=False).mean(numeric_only=True)
    orig = HR.ocupacoes
    out = {}
    for c in CONFIGS:
        yB, yA = fin[c]
        nB = int(yB.sum())

        def fixa(loc, nB_, lg, lb, mu, variante="larson75", **k):
            return np.concatenate([np.full(nB_, q[0]), np.full(len(loc) - nB_, q[1])]), 0
        HR.ocupacoes = fixa
        x = HR.avalia(yB, yA, f, a, 70.0, tx, variante="daskin")
        HR.ocupacoes = orig
        e = HR.avalia(yB, yA, f, a, 70.0, tx, variante="daskin", detalhe=True)
        l = HR.avalia(yB, yA, f, a, 70.0, tx, variante="larson75")
        r = e["rho"]
        out[c] = dict(sim=float(sim.loc[c, "sim_vidas"]), fase3=float(sim.loc[c, "an_vidas"]),
                      fixa=x["vidas"], endogena=e["vidas"], larson75=l["vidas"],
                      rho_usb=[float(r[:nB].min()), float(r[:nB].mean()), float(r[:nB].max())],
                      rho_usa=[float(r[nB:].min()), float(r[nB:].mean()), float(r[nB:].max())])
    (DADOS / "h_ablacao.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("config | sim | fase3 | HC ocupacao fixa | endogena sem Q | larson75")
    for c, v in out.items():
        print(f"{c:24s} {v['sim']:6.2f} {v['fase3']:6.2f} {v['fixa']:6.2f} {v['endogena']:6.2f} {v['larson75']:6.2f}  "
              f"rho USB {v['rho_usb'][0]:.2f}-{v['rho_usb'][2]:.2f}")


if __name__ == "__main__":
    main()
