"""Busca local com o objetivo EXATO em todos os setores (Teitz-Bart generalizado).

Por que nao o MILP como otimizador principal: a sobrevida depende do tempo
exato de cada setor, e qualquer agregacao em zonas distorce a medida em ~20%
(media dos tempos: subestima; cobertura fracionaria: superestima, por Jensen).
Com zonas finas o MILP nao acha solucao em tempo util. Aqui o objetivo e o
mesmo do MILP — sobrevida em degraus, 1 - qB^nB qA^nA por faixa —, calculado
setor a setor, sem agregacao.

Estado: para cada faixa b e setor i, E_bi = qB^nB_bi * qA^nA_bi (chance de
nenhum desfibrilador a ate tau_b estar livre). Sobrevida S_i = soma_b d_b (1 - E_bi).

Movimento: tirar uma unidade do local j e por no local j' (mesmo tipo).
  ganho de por um tipo T em j'  = (1 - q_T) soma_b [C_b^T (w d_b E_b)]_j'
  perda de tirar um tipo T de j = (1/q_T - 1) soma_{b, i em C_b(j)} w_i d_b E_bi
O vetor de ganhos para TODOS os j' sai de um produto esparso por faixa (~50 ms
para as 15 faixas e 26.889 setores); depois de tirar a unidade de j, so as
linhas cobertas por j mudam, e a correcao e local. Os melhores candidatos sao
conferidos exatamente (objetivo, CVaR, guardas, limite de unidades movidas)
antes de aceitar.

Objetivo: J = vidas + lam * CVaR10 (ambos em sobrevida por PCR). lam = 0 e
"so vidas"; lam maior pesa mais os 10% piores. Na triagem o CVaR entra pelo
seu gradiente (peso extra lam/alfa nos setores do pior decil atual); a
aceitacao usa o valor exato.
"""
import numpy as np
from scipy import sparse

from fase3_vidas.modelo import sobrevida as SV

CAP = 10


def coberturas(T_setor, fator, atraso, bandas=SV.BANDAS, tau_guarda=SV.TAU_GUARDA):
    """Matrizes esparsas (setores, locais) de 'local a ate tau min de resposta'."""
    tau, _ = SV.degraus(bandas)
    C = [sparse.csr_matrix(T_setor <= l, dtype=np.float32)
         for l in SV.bruto(tau, fator, atraso)]
    G = sparse.csr_matrix(T_setor <= SV.bruto(tau_guarda, fator, atraso), dtype=np.float32)
    return C, G


class Busca:
    def __init__(self, C, G, pop, qB, qA, x0B, x0A, bandas=SV.BANDAS, cap=CAP,
                 inicio=SV.INICIO, d=None, tipos=None):
        """d, tipos: objetivo generico soma_b d_b (1 - E_b). Por padrao, d sao os
        degraus da curva de sobrevida e toda faixa conta os dois tipos (PCR: o
        primeiro de qualquer tipo). tipos (B, 2) de 0/1 diz que tipos contam em
        cada faixa (coluna 0 = USB, 1 = USA): o objetivo "por classe" usa uma
        faixa so de USA (chamado grave) e outra so de USB (chamado basico)."""
        self.C = C
        self.Cc = [c.tocsc() for c in C]          # colunas: setores cobertos por j
        self.G, self.Gc = G, G.tocsc()
        self.w = np.asarray(pop, dtype=np.float64) / np.sum(pop)
        self.d = SV.degraus(bandas, inicio)[1] if d is None else np.asarray(d, dtype=np.float64)
        self.B = len(self.d)
        self.tipos = np.ones((self.B, 2), int) if tipos is None else np.asarray(tipos, int)
        self.q = {"B": qB, "A": qA}
        self.lq = {"B": np.log(qB), "A": np.log(qA)}
        self.x0 = {"B": np.asarray(x0B, int), "A": np.asarray(x0A, int)}
        self.m = C[0].shape[1]
        self.cap = cap

    # ------------------------------------------------------------ medidas
    def estado(self, yB, yA):
        y = {"B": np.asarray(yB, int).copy(), "A": np.asarray(yA, int).copy()}
        L = np.stack([tb * self.lq["B"] * c.dot(y["B"]) + ta * self.lq["A"] * c.dot(y["A"])
                      for c, (tb, ta) in zip(self.C, self.tipos)])
        gB, gA = self.G.dot(y["B"]), self.G.dot(y["A"])
        return {"y": y, "E": np.exp(L), "gB": gB, "gA": gA}

    def S(self, st):
        return (self.d[:, None] * (1.0 - st["E"])).sum(axis=0)

    def medidas(self, st):
        S = self.S(st)
        return {"vidas": float(np.sum(self.w * S)),
                "cvar10": SV.cvar_inferior(S, self.w),
                "cob_basico": float(np.sum(self.w * -np.expm1(self.lq["B"] * st["gB"]))),
                "cob_grave": float(np.sum(self.w * -np.expm1(self.lq["A"] * st["gA"])))}

    def movidas(self, y):
        return int(sum(np.maximum(self.x0[t] - y[t], 0).sum() for t in ("B", "A")))

    # ------------------------------------------------------------ movimentos
    def _aplica(self, st, tipo, j, sinal):
        """Tira (sinal=-1) ou poe (+1) uma unidade do tipo no local j, in place."""
        fat = self.q[tipo] ** sinal
        col = 0 if tipo == "B" else 1
        for b in range(self.B):
            if not self.tipos[b, col]:
                continue
            c = self.Cc[b]
            r = c.indices[c.indptr[j]:c.indptr[j + 1]]
            st["E"][b, r] *= fat
        r = self.Gc.indices[self.Gc.indptr[j]:self.Gc.indptr[j + 1]]
        st["gB" if tipo == "B" else "gA"][r] += sinal
        st["y"][tipo][j] += sinal

    def _ganhos(self, st, peso, tipo):
        """Ganho (sem o fator 1 - q) de por uma unidade do tipo em cada local, dado E."""
        col = 0 if tipo == "B" else 1
        return sum(self.C[b].T.dot(peso * self.d[b] * st["E"][b])
                   for b in range(self.B) if self.tipos[b, col])

    def otimiza(self, yB, yA, lam=0.0, K=None, base=None, eps=None,
                semente=0, n_cand=4, max_passos=30, verbose=False):
        """Busca local a partir de (yB, yA). base = {'cob_basico', 'cob_grave'}
        (guardas, em fracao); eps = piso do CVaR; K = limite de unidades
        movidas em relacao a x0. Devolve (estado, medidas, historico)."""
        rng = np.random.default_rng(semente)
        st = self.estado(yB, yA)
        med = self.medidas(st)
        J = lambda md: md["vidas"] + lam * md["cvar10"]

        def viavel(md, y):
            if K is not None and self.movidas(y) > K:
                return False
            if base is not None and (md["cob_basico"] < base["cob_basico"] - 1e-12 or
                                     md["cob_grave"] < base["cob_grave"] - 1e-12):
                return False
            return eps is None or md["cvar10"] >= eps - 1e-12

        hist = [dict(med, passo=0, movidas=self.movidas(st["y"]))]
        for passo in range(1, max_passos + 1):
            melhorou = 0
            unid = [(t, j) for t in ("B", "A") for j in np.nonzero(st["y"][t])[0]]
            rng.shuffle(unid)
            for tipo, j in unid:
                if st["y"][tipo][j] == 0:
                    continue
                # peso de triagem: populacao + gradiente do CVaR no pior decil
                S = self.S(st)
                peso = self.w.copy()
                if lam > 0:
                    o = np.argsort(S)
                    pior = o[np.cumsum(self.w[o]) <= SV.ALFA_CVAR + 1e-12]
                    peso[pior] *= 1.0 + lam / SV.ALFA_CVAR
                self._aplica(st, tipo, j, -1)
                g = (1.0 - self.q[tipo]) * self._ganhos(st, peso, tipo)
                livre = (st["y"]["B"] + st["y"]["A"]) < self.cap
                g[~livre] = -np.inf
                g[j] = -np.inf
                cand = np.argsort(-g)[:n_cand]
                melhor, md_m = None, None
                for jj in cand:
                    if not np.isfinite(g[jj]):
                        break
                    self._aplica(st, tipo, jj, +1)
                    md = self.medidas(st)
                    if viavel(md, st["y"]) and J(md) > J(med) + 1e-10 and \
                            (md_m is None or J(md) > J(md_m)):
                        melhor, md_m = jj, md
                    self._aplica(st, tipo, jj, -1)
                if melhor is None:
                    self._aplica(st, tipo, j, +1)       # desfaz
                else:
                    self._aplica(st, tipo, melhor, +1)
                    med = md_m
                    melhorou += 1
            hist.append(dict(med, passo=passo, movidas=self.movidas(st["y"]), trocas=melhorou))
            if verbose:
                print(f"  passo {passo}: vidas {1000*med['vidas']:.2f} cvar {1000*med['cvar10']:.2f} "
                      f"movidas {self.movidas(st['y'])} trocas {melhorou}", flush=True)
            if melhorou == 0:
                break
        return st, med, hist

    def refina(self, yB, yA, lam=0.0, K=None, base=None, eps=None, chutes=10,
               tam=3, viz=None, semente=0, max_passos=30):
        """Busca local iterada: a partir do otimo local de (yB, yA), realoca
        `tam` unidades ao acaso (para um vizinho em `viz`, ou qualquer local),
        reotimiza e fica com o resultado se for melhor e viavel. A busca de um
        so movimento para em otimos locais (no caso de teste, -1,2% do otimo);
        os chutes deixam sair deles. Devolve (estado, medidas, ganhos por chute)."""
        rng = np.random.default_rng(10_000 + semente)
        J = lambda md: md["vidas"] + lam * md["cvar10"]
        st, med, _ = self.otimiza(yB, yA, lam=lam, K=K, base=base, eps=eps,
                                  semente=semente, max_passos=max_passos)
        melhor = {"B": st["y"]["B"].copy(), "A": st["y"]["A"].copy()}
        ganhos = []
        for c in range(chutes):
            y = {t: melhor[t].copy() for t in ("B", "A")}
            for _ in range(tam):
                t = "B" if rng.random() < len(np.nonzero(y["B"])[0]) / (
                    len(np.nonzero(y["B"])[0]) + len(np.nonzero(y["A"])[0])) else "A"
                j = rng.choice(np.nonzero(y[t])[0])
                destinos = viz[j] if viz is not None else np.arange(self.m)
                livres = [d for d in destinos if y["B"][d] + y["A"][d] < self.cap and d != j]
                if not livres:
                    continue
                y[t][j] -= 1
                y[t][rng.choice(livres)] += 1
            if K is not None and self.movidas(y) > K:
                ganhos.append(0.0)
                continue
            st2, md2, _ = self.otimiza(y["B"], y["A"], lam=lam, K=K, base=base, eps=eps,
                                       semente=semente + c + 1, max_passos=max_passos)
            ok = ((K is None or self.movidas(st2["y"]) <= K) and
                  (base is None or (md2["cob_basico"] >= base["cob_basico"] - 1e-12 and
                                    md2["cob_grave"] >= base["cob_grave"] - 1e-12)) and
                  (eps is None or md2["cvar10"] >= eps - 1e-12))
            ganho = J(md2) - J(med) if ok else 0.0
            ganhos.append(max(ganho, 0.0))
            if ok and ganho > 1e-10:
                melhor = {"B": st2["y"]["B"].copy(), "A": st2["y"]["A"].copy()}
                med = md2
        return self.estado(melhor["B"], melhor["A"]), med, ganhos


# ------------------------------------------------------------------- sanidade
def _teste():
    from itertools import combinations_with_replacement as cwr
    from fase3_vidas.modelo import mip_vidas as MV
    rng = np.random.default_rng(3)
    m, n = 7, 40
    ps, dm = rng.random((m, 2)) * 12, rng.random((n, 2)) * 12
    T = np.sqrt(((dm[:, None, :] - ps[None, :, :]) ** 2).sum(-1)).astype(np.float32)
    pop = rng.integers(100, 2000, n).astype(float)
    x0B, x0A = MV.por_local([0, 1], m), MV.por_local([2], m)
    bd = tuple(np.arange(1.0, 15.01, 1.0))
    C, G = coberturas(T, 1.0, 0.0, bandas=bd)
    bz = Busca(C, G, pop, 0.35, 0.21, x0B, x0A, bandas=bd, inicio=0.0)
    M = MV.Modelo.de_tempos(T, pop, x0B, x0A, 0.35, 0.21, passo=0.05, bandas=bd, inicio=0.0)

    # mesma conta que o MILP faz por zona (uma zona = um setor)
    st = bz.estado(x0B, x0A)
    assert abs(bz.medidas(st)["vidas"] - M.avalia(x0B, x0A)[0]) < 1e-12
    # aplicar e desfazer volta ao mesmo estado
    E0 = st["E"].copy()
    bz._aplica(st, "B", 3, +1); bz._aplica(st, "B", 3, -1)
    assert np.allclose(st["E"], E0)

    # forca bruta
    otimo = max(M.avalia(MV.por_local(b, m), MV.por_local([a], m))[0]
                for b in cwr(range(m), 2) for a in range(m))
    # um movimento por vez para em otimo local; a busca iterada chega ao otimo
    local = max(bz.otimiza(x0B, x0A, semente=s)[1]["vidas"] for s in range(5))
    _, mdr, _ = bz.refina(x0B, x0A, chutes=20, tam=2)
    assert local <= otimo + 1e-12 and abs(mdr["vidas"] - otimo) < 1e-12, (local, mdr["vidas"], otimo)
    # limite K = 0 nao mexe; guardas respeitadas
    _, md0, _ = bz.otimiza(x0B, x0A, K=0)
    assert abs(md0["vidas"] - M.avalia(x0B, x0A)[0]) < 1e-12
    base = bz.medidas(bz.estado(x0B, x0A))
    _, mdg, _ = bz.otimiza(x0B, x0A, base=base)
    assert mdg["cob_basico"] >= base["cob_basico"] - 1e-12 and mdg["cob_grave"] >= base["cob_grave"] - 1e-12
    # lam > 0 nao reduz o CVaR em relacao a lam = 0
    _, md1, _ = bz.otimiza(x0B, x0A, lam=4.0)
    _, md2, _ = bz.otimiza(x0B, x0A, lam=0.0)
    assert md1["cvar10"] >= md2["cvar10"] - 1e-12
    # objetivo por classe: th * P(USA <= tau) + (1 - th) * P(USB <= tau), sem PCR
    th, tau = 0.3, 6.0
    Cc, Gc = coberturas(T, 1.0, 0.0, bandas=(tau, tau))
    bc = Busca(Cc, Gc, pop, 0.35, 0.21, x0B, x0A, d=(th, 1 - th), tipos=((0, 1), (1, 0)))
    w = pop / pop.sum()
    def cls(yB, yA):
        nA, nB = (T <= tau).dot(yA), (T <= tau).dot(yB)
        return float(np.sum(w * (th * (1 - 0.21 ** nA) + (1 - th) * (1 - 0.35 ** nB))))
    assert abs(bc.medidas(bc.estado(x0B, x0A))["vidas"] - cls(x0B, x0A)) < 1e-12
    ot_c = max(cls(MV.por_local(b, m), MV.por_local([a], m)) for b in cwr(range(m), 2) for a in range(m))
    _, mdc, _ = bc.refina(x0B, x0A, chutes=20, tam=2)
    assert abs(mdc["vidas"] - ot_c) < 1e-12, (mdc["vidas"], ot_c)
    print(f"ok  otimo {otimo:.5f}: busca local {local:.5f} ({100*(local/otimo-1):+.2f}%), "
          f"iterada {mdr['vidas']:.5f}; K=0 fixo; guardas; "
          f"lam=4 CVaR {md1['cvar10']:.4f} >= lam=0 {md2['cvar10']:.4f}")


if __name__ == "__main__":
    _teste()
