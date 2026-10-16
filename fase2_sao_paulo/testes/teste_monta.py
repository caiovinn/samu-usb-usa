"""Testa as partes de monta.py que nao dependem dos dados reais."""
import numpy as np
from fase2_sao_paulo.experimentos import monta

rng = np.random.default_rng(0)

# ---- grafo em grade 40x40, arestas nos dois sentidos, peso = 1 min
L = 40
gx, gy = np.meshgrid(np.arange(L), np.arange(L))
nx_ = (-46.8 + gx.ravel() * 0.005).astype(float)
ny_ = (-23.8 + gy.ravel() * 0.005).astype(float)
idx = np.arange(L * L).reshape(L, L)
U, V = [], []
for a in range(L):
    for b in range(L):
        if a + 1 < L: U += [idx[a, b], idx[a + 1, b]]; V += [idx[a + 1, b], idx[a, b]]
        if b + 1 < L: U += [idx[a, b], idx[a, b + 1]]; V += [idx[a, b + 1], idx[a, b]]
U, V = np.array(U), np.array(V)
W = np.ones(len(U))

# ---- 1. no mais proximo confere com forca bruta
px = nx_.min() + rng.random(300) * (nx_.max() - nx_.min())
py = ny_.min() + rng.random(300) * (ny_.max() - ny_.min())
got = monta.no_mais_proximo(px, py, nx_, ny_, celula=0.005)
cosl = np.cos(np.radians(ny_.mean()))
d = ((nx_[None, :] - px[:, None]) * cosl) ** 2 + (ny_[None, :] - py[:, None]) ** 2
esperado = d.argmin(axis=1)
assert (got == esperado).all(), f"{(got != esperado).sum()} pontos errados"
print(f"ok  no_mais_proximo: {len(px)} pontos batem com a forca bruta")

# ---- 2. Dijkstra confere com a distancia de Manhattan da grade
fontes = rng.choice(L * L, 12, replace=False)
alvos = rng.choice(L * L, 200, replace=False)
T = monta.matriz_tempos(fontes, alvos, U, V, W, L * L, corte=200.0, bloco=5)
fa, fb = np.array(np.unravel_index(fontes, (L, L)))
aa, ab = np.array(np.unravel_index(alvos, (L, L)))
man = (np.abs(aa[:, None] - fa[None, :]) + np.abs(ab[:, None] - fb[None, :])).astype(float)
assert np.allclose(T, man, atol=1e-6), np.abs(T - man).max()
print(f"ok  matriz_tempos: {T.shape} bate com a distancia de Manhattan")

# ---- 3. corte devolve INF_MIN alem do limite
T2 = monta.matriz_tempos(fontes[:3], alvos, U, V, W, L * L, corte=10.0, bloco=2)
assert (T2[man[:, :3] > 10] >= monta.INF_MIN).all(), "corte vazou"
assert np.allclose(T2[man[:, :3] <= 10], man[:, :3][man[:, :3] <= 10])
print("ok  corte de 10 min respeitado")

# ---- 4. arestas paralelas: a fusao deve pegar a menor, nao somar
import pandas as pd
u2 = np.array([0, 0, 1]); v2 = np.array([1, 1, 2]); w2 = np.array([5.0, 2.0, 1.0])
a = pd.DataFrame({"u": u2, "v": v2, "w": w2}).groupby(["u", "v"], as_index=False).w.min()
T3 = monta.matriz_tempos(np.array([0]), np.array([2]), a.u.values, a.v.values,
                         a.w.values, 3, corte=100.0)
assert np.isclose(T3[0, 0], 3.0), T3
print("ok  arestas paralelas fundidas pelo menor tempo (2+1=3)")
