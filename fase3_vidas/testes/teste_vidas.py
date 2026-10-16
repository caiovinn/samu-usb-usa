"""Testes da fase 3 que nao dependem dos dados reais.

    uv run python -m fase3_vidas.testes.teste_vidas

Roda o _teste() de cada modulo (curva de sobrevida, degraus = despacho,
calibracao, MILP = forca bruta, busca local = forca bruta, simulacao sem
carga = analitico) e confere, alem disso, que a avaliacao por setor da busca e
a do modelo continuo concordam quando as faixas sao finas.
"""
import numpy as np

from fase3_vidas.experimentos import simula_vidas
from fase3_vidas.modelo import busca, mip_vidas, sobrevida

sobrevida._teste()
mip_vidas._teste()
busca._teste()
simula_vidas._teste()

# degraus finos -> sobrevida da busca (degraus) ~ avalia_vidas (curva continua)
rng = np.random.default_rng(7)
m, n = 30, 300
ps, dm = rng.random((m, 2)) * 15, rng.random((n, 2)) * 15
T = np.sqrt(((dm[:, None, :] - ps[None, :, :]) ** 2).sum(-1)).astype(np.float32)   # (setores, locais)
pop = rng.integers(100, 2000, n).astype(float)
yB, yA = mip_vidas.por_local(rng.choice(m, 12), m), mip_vidas.por_local(rng.choice(m, 3), m)
finas = tuple(np.arange(2.25, 40.0, 0.25))      # comecam no atraso (2 min)
C, G = busca.coberturas(T, 1.4, 2.0, bandas=finas)
bz = busca.Busca(C, G, pop, 0.3, 0.2, yB, yA, bandas=finas, inicio=2.0)
v_deg = bz.medidas(bz.estado(yB, yA))["vidas"]
iB, iA = mip_vidas.para_indices(yB, yA)
v_cont = sobrevida.avalia_vidas(np.ascontiguousarray(T.T), pop, iB, iA, 0.3, 0.2,
                                fator=1.4, atraso=2.0, k_desp=m)["vidas"] / 1000
assert abs(v_deg - v_cont) < 2e-3 * v_cont, (v_deg, v_cont)
print(f"ok  degraus finos {1000*v_deg:.3f} x curva continua {1000*v_cont:.3f} por 1.000 PCR")
