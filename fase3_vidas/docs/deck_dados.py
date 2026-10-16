"""Numeros derivados que a apresentacao da fase 3 precisa e o JS nao calcula.

    uv run python -m fase3_vidas.docs.deck_dados

Grava dados/fase3/deck_vidas.json (derivado, regeneravel). O deck_vidas.js le
este arquivo e os JSONs de resultado (v1..v7); nada e digitado a mao. Aqui
ficam so o que depende de parquet ou das funcoes do modelo (populacao, curva
de sobrevida, tamanho do MILP), para que nenhuma definicao seja copiada para
o JavaScript.
"""
import json

import numpy as np
import pandas as pd

from fase3_vidas.caminhos import DADOS, DADOS_FASE2
from fase3_vidas.docs.relatorio_gera import INC_CENTRAL, INC_FAIXA
from fase3_vidas.modelo import busca as BU, mip_vidas as MV, sobrevida as SV


def main():
    st = pd.read_parquet(DADOS_FASE2 / "sp_setores.parquet")
    cd = pd.read_parquet(DADOS_FASE2 / "sp_candidatos.parquet")
    U = json.load(open(DADOS_FASE2 / "sp_utilizacao.json", encoding="utf-8"))
    pop = float(st["pop"].sum())
    n_cortes = int(np.ceil(-MV.L_MIN_CORTE / MV.PASSO_CORTE)) + 1
    t = np.arange(0, 20.01, 0.5)
    out = {
        "n_setores": int(len(st)), "pop_total": pop, "n_cand": int(len(cd)),
        "n_locais_hoje": int(((cd.n_usb + cd.n_usa) > 0).sum()),
        "n_usb": int(cd.n_usb.sum()), "n_usa": int(cd.n_usa.sum()),
        "cap": BU.CAP, "tau_guarda": SV.TAU_GUARDA, "alfa_cvar": SV.ALFA_CVAR,
        "n_bandas": len(SV.BANDAS), "n_cortes": n_cortes,
        "n_vars_y": 2 * int(len(cd)), "n_restr": len(st) * len(SV.BANDAS) * n_cortes,
        "curva_t": t.tolist(), "curva_s": SV.s(t).tolist(),
        "s5": float(SV.s(5)), "s9": float(SV.s(9)), "s15": float(SV.s(15)),
        # queda relativa por minuto entre 9 e 10 min (a faixa tipica de chegada)
        "queda_min": float(1 - SV.s(10) / SV.s(9)),
        "q_usb": U["q"]["central"]["q_usb"], "q_usa": U["q"]["central"]["q_usa"],
        "inc_central": INC_CENTRAL, "inc_faixa": list(INC_FAIXA),
        "pcr_ano": pop * INC_CENTRAL / 1e5,
        # saidas por dia no SIA (janela de 12 meses); a da Prefeitura sai de v6_robustez
        "sia_dia": sum(U["por_ano_12m"].values()) / 365.0,
    }
    destino = DADOS / "deck_vidas.json"
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {destino}")


if __name__ == "__main__":
    main()
