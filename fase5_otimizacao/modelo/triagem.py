"""Triagem de movimentos da busca local: qual destino testar para cada unidade.

A busca local (Teitz-Bart) nao pode avaliar no hipercubo os ~1.000 destinos de
cada uma das 123 unidades a cada passo. Ela ordena os destinos por um ganho
aproximado e avalia so os melhores.

  metodo "q"    o da fase 3/4 (fase3_vidas.modelo.busca): cada unidade ocupada
                com o q do seu TIPO, igual para todas. Chance de nenhum
                desfibrilador livre a ate tau_b do setor i:
                    E_bi = q_B ^ nB_bi * q_A ^ nA_bi
  metodo "rho"  fase 5: cada unidade com a SUA ocupacao rho_u, a do hipercubo
                no mapa atual:
                    E_bi = prod_{u a ate tau_b de i} rho_u
                Uma area congestionada (rho alto) tem E alto, e por uma unidade
                la vale mais -- o efeito que a triagem "q" nao enxerga.

Ganho aproximado de mover a unidade u (tipo T, no local j) para j':
    tira u:  E_b[setores cobertos por j] /= ocupacao de u
    poe em j': (1 - rho_novo) * soma_b [C_b^T (peso * d_b * E_b)]_j'
O termo de tirar u e o mesmo para todo j': para ordenar destinos so o de por
importa. rho_novo: q do tipo ("q") ou a ocupacao media do tipo no mapa ("rho").
Mesmas faixas em degraus e mesmo peso (populacao + gradiente do CVaR) da fase 3.
"""
import numpy as np

from fase3_vidas.modelo import busca as BU
from fase3_vidas.modelo import mip_vidas as MV
from fase3_vidas.modelo import sobrevida as SV


class Triagem:
    def __init__(self, Ts, pop, fator, atraso, qB, qA, x0B, x0A, cap=BU.CAP):
        """Ts: (setores, locais) tempos brutos. qB, qA: os q da fase 3 (metodo "q")."""
        C, G = BU.coberturas(Ts, fator, atraso)
        self.bz = BU.Busca(C, G, pop, qB, qA, x0B, x0A, cap=cap)
        self.m = self.bz.m
        self.cap = cap

    def peso(self, S, lam):
        """Peso de triagem da fase 3: populacao + gradiente do CVaR no pior decil."""
        bz = self.bz
        p = bz.w.copy()
        if lam > 0:
            o = np.argsort(S)
            pior = o[np.cumsum(bz.w[o]) <= SV.ALFA_CVAR + 1e-12]
            p[pior] *= 1.0 + lam / SV.ALFA_CVAR
        return p

    def estado(self, yB, yA, rho=None):
        """Estado de triagem. rho=None: metodo "q"; senao rho por unidade (USB primeiro)."""
        bz = self.bz
        if rho is None:
            st = bz.estado(yB, yA)
            st["metodo"] = "q"
            return st
        yB = np.asarray(yB, int)
        yA = np.asarray(yA, int)
        iB, iA = MV.para_indices(yB, yA)
        nB = len(iB)
        lr = np.log(np.clip(np.asarray(rho, float), 1e-9, 1.0))
        lrB = np.bincount(iB, weights=lr[:nB], minlength=self.m)
        lrA = np.bincount(iA, weights=lr[nB:], minlength=self.m)
        L = np.stack([tb * c.dot(lrB) + ta * c.dot(lrA) for c, (tb, ta) in zip(bz.C, bz.tipos)])
        return {"y": {"B": yB.copy(), "A": yA.copy()}, "E": np.exp(L), "metodo": "rho",
                "rho": np.asarray(rho, float), "iB": iB, "iA": iA,
                "rho_med": {"B": float(np.mean(rho[:nB])), "A": float(np.mean(rho[nB:]))}}

    def ganhos(self, st, tipo, j, peso, unidade=None):
        """Ganho aproximado de por, em cada local j', a unidade do tipo que sai de j.

        unidade: indice (USB primeiro) da unidade que sai, para o metodo "rho".
        Devolve vetor (m,) com -inf onde nao cabe (cap) e em j.
        """
        bz = self.bz
        col = 0 if tipo == "B" else 1
        if st["metodo"] == "q":
            q_sai = q_novo = bz.q[tipo]
        else:
            q_sai = st["rho"][unidade]
            q_novo = st["rho_med"][tipo]
        cobre = []
        for b in range(bz.B):
            if bz.tipos[b, col]:
                c = bz.Cc[b]
                r = c.indices[c.indptr[j]:c.indptr[j + 1]]
                st["E"][b, r] /= q_sai
                cobre.append((b, r))
        try:
            g = (1.0 - q_novo) * bz._ganhos(st, peso, tipo)
        finally:
            for b, r in cobre:
                st["E"][b, r] *= q_sai
        livre = (st["y"]["B"] + st["y"]["A"]) < self.cap
        g = np.where(livre, g, -np.inf)
        g[j] = -np.inf
        return g

    def S(self, st):
        return self.bz.S(st)
