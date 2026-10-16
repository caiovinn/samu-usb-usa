"""Otimizacao EXATA do mapa de bases pela sobrevida a PCR (MILP, HiGHS).

Por que da para resolver exatamente: com despacho "unidade livre mais proxima"
e ocupacoes independentes, a chance de ALGUM desfibrilador chegar ao setor i em
ate tau minutos e

    P(T_i <= tau) = 1 - qB^nB_i(tau) * qA^nA_i(tau) = 1 - exp(L_i(tau)),
    L_i(tau) = ln qB * nB_i(tau) + ln qA * nA_i(tau),

com n_i(tau) = unidades a ate tau minutos (o regulador acha alguem dentro de
tau se e so se alguem dentro de tau esta livre). Com a curva de sobrevida em
degraus (sobrevida.degraus), a sobrevida esperada do setor e
soma_b d_b (1 - exp(L_ib)): L e LINEAR nas unidades por local e 1 - e^L e
concava em L, entao cortes tangentes em L representam a funcao por cima
(estrutura do MEXCLP de Daskin 1983). O erro dos cortes e x0 * delta^2 / 8 no
pior caso; a avaliacao final de toda solucao e feita sem aproximacao nenhuma,
setor a setor (sobrevida.avalia_vidas).

Variaveis (unidades por local, inteiras): yB_j, yA_j. Restricoes:
  frota fixa (107 USB, 16 USA); no maximo CAP unidades por local;
  unidades movidas <= K (m_j >= x0_j - y_j);
  guardas: cobertura em TAU_GUARDA min do chamado basico (USB) e do grave
  (USA) nao pior que a de hoje;
  CVaR10 da sobrevida >= eps (Rockafellar-Uryasev).
Objetivo: sobreviventes esperados por PCR (ou o CVaR10, para achar o maximo).

A demanda entra por ZONAS (grade de lado_km), com o tempo medio da zona
ponderado pela populacao: a matriz setor x local tem 30 milhoes de celulas.
O erro dessa agregacao e medido reavaliando a solucao em todos os setores.
"""
import time

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp

from fase3_vidas.modelo import sobrevida as SV

CAP = 10                 # unidades por local, como CAP_MAX da fase 2
PASSO_CORTE = 0.35       # espacamento dos cortes tangentes em L
L_MIN_CORTE = np.log(1e-5)


# ------------------------------------------------------------------- zonas
def zonas(lat, lon, lado_km=1.0):
    """Indice de zona (grade quadrada de lado_km) de cada setor."""
    la0 = np.radians(np.mean(lat))
    x = np.radians(lon) * 6371.0 * np.cos(la0)
    y = np.radians(lat) * 6371.0
    ix = np.floor((x - x.min()) / lado_km).astype(np.int64)
    iy = np.floor((y - y.min()) / lado_km).astype(np.int64)
    _, z = np.unique(ix * (iy.max() + 1) + iy, return_inverse=True)
    return z


def agrega(T_setor, z, pop, lim):
    """Cobertura FRACIONARIA por zona: a[z, j] = fracao da populacao da zona z a
    ate `lim` minutos (brutos) do local j. Media de L exata dentro da zona; o que
    a agregacao perde e so a variacao de L entre setores da mesma zona.
    T_setor e (setores, locais)."""
    nz = int(z.max()) + 1
    w = np.asarray(pop, dtype=np.float64) + 1e-9
    A = sparse.csr_matrix((w, (z, np.arange(len(z)))), shape=(nz, len(z)))
    soma = np.asarray(A.sum(axis=1)).ravel()
    A = sparse.diags(1.0 / soma) @ A
    return (A @ sparse.csr_matrix(T_setor <= lim)).tocsr(), soma


# ----------------------------------------------------------------- modelo
class Modelo:
    """MILP de um cenario (q, fator, atraso) sobre zonas.

    cobre: lista (uma por faixa) de matrizes (n_zonas, m) com a fracao da zona a
    ate tau_b de cada local; guarda: idem para TAU_GUARDA; wz pesos das zonas;
    x0B, x0A unidades por local hoje. Use `de_setores` (dados reais) ou
    `de_tempos` (testes, uma zona = um ponto).
    """

    def __init__(self, cobre, guarda, wz, x0B, x0A, qB, qA, bandas=SV.BANDAS,
                 cap=CAP, passo=PASSO_CORTE, inicio=SV.INICIO):
        self.cobre, self.guarda = cobre, guarda
        self.nz, self.m = guarda.shape
        self.wz = np.asarray(wz, dtype=np.float64) / np.sum(wz)
        self.x0B = np.asarray(x0B, dtype=np.int64)
        self.x0A = np.asarray(x0A, dtype=np.int64)
        self.NB, self.NA = int(self.x0B.sum()), int(self.x0A.sum())
        self.lqB, self.lqA = np.log(qB), np.log(qA)
        self.cap = cap
        self.tau, self.d = SV.degraus(bandas, inicio)
        self.B = len(self.tau)
        self.L0 = -passo * np.arange(int(np.ceil(-L_MIN_CORTE / passo)) + 1)
        self._indices()

    @classmethod
    def de_tempos(cls, Tz, wz, x0B, x0A, qB, qA, fator=1.0, atraso=0.0,
                  bandas=SV.BANDAS, tau_guarda=SV.TAU_GUARDA, **kw):
        tau, _ = SV.degraus(bandas)
        lim = SV.bruto(tau, fator, atraso)
        cobre = [sparse.csr_matrix((Tz <= l).astype(np.float64)) for l in lim]
        guarda = sparse.csr_matrix((Tz <= SV.bruto(tau_guarda, fator, atraso)).astype(np.float64))
        return cls(cobre, guarda, wz, x0B, x0A, qB, qA, bandas=bandas, **kw)

    @classmethod
    def de_setores(cls, T_setor, z, pop, x0B, x0A, qB, qA, fator=1.0, atraso=0.0,
                   bandas=SV.BANDAS, tau_guarda=SV.TAU_GUARDA, **kw):
        tau, _ = SV.degraus(bandas)
        cobre = [agrega(T_setor, z, pop, l)[0] for l in SV.bruto(tau, fator, atraso)]
        guarda, wz = agrega(T_setor, z, pop, SV.bruto(tau_guarda, fator, atraso))
        return cls(cobre, guarda, wz, x0B, x0A, qB, qA, bandas=bandas, **kw)

    # ---- disposicao das variaveis no vetor x
    def _indices(self):
        m, nz, B = self.m, self.nz, self.B
        tam = {"yB": m, "yA": m, "mB": m, "mA": m, "L": nz * B, "u": nz * B,
               "Lb": nz, "ub": nz, "La": nz, "ua": nz, "eta": 1, "v": nz}
        self.ix, ini = {}, 0
        for k, n in tam.items():
            self.ix[k] = np.arange(ini, ini + n)
            ini += n
        self.nvar = ini

    def _monta(self, K, eps, base_basico, base_grave):
        ix, m, nz, B = self.ix, self.m, self.nz, self.B
        R, C, V, lo, hi = [], [], [], [], []
        nlin = [0]

        def linhas(r, c, v, l, h):
            """r: indices LOCAIS de linha (0..k-1) do bloco; l, h por linha."""
            l, h = np.atleast_1d(l), np.atleast_1d(h)
            R.append(np.asarray(r) + nlin[0]); C.append(np.asarray(c)); V.append(np.asarray(v, float))
            lo.append(np.broadcast_to(l, (len(l),)).astype(float)); hi.append(h.astype(float))
            nlin[0] += len(l)

        um = lambda k: np.ones(k)
        # frota
        linhas(np.zeros(m, int), ix["yB"], um(m), [self.NB], [self.NB])
        linhas(np.zeros(m, int), ix["yA"], um(m), [self.NA], [self.NA])
        # capacidade por local
        j = np.arange(m)
        linhas(np.r_[j, j], np.r_[ix["yB"], ix["yA"]], um(2 * m), np.full(m, -np.inf), np.full(m, self.cap))
        # unidades movidas: y_j + m_j >= x0_j ; soma m <= K
        for y, mm, x0 in (("yB", "mB", self.x0B), ("yA", "mA", self.x0A)):
            linhas(np.r_[j, j], np.r_[ix[y], ix[mm]], um(2 * m), x0, np.full(m, np.inf))
        if K is not None:
            linhas(np.zeros(2 * m, int), np.r_[ix["mB"], ix["mA"]], um(2 * m), [-np.inf], [K])

        # L_zb = lnqB * nB_zb + lnqA * nA_zb
        z = np.arange(nz)
        for b in range(B):
            c = self.cobre[b].tocoo()
            Lb = ix["L"][b * nz:(b + 1) * nz]
            linhas(np.r_[z, c.row, c.row], np.r_[Lb, ix["yB"][c.col], ix["yA"][c.col]],
                   np.r_[um(nz), -self.lqB * c.data, -self.lqA * c.data],
                   np.zeros(nz), np.zeros(nz))
        # cortes tangentes: u + x0 L <= 1 - x0 + x0 L0
        self._cortes(linhas, ix["u"], ix["L"])

        # guardas (cobertura so de USB, chamado basico; so de USA, grave)
        g = self.guarda.tocoo()
        linhas(np.r_[z, g.row], np.r_[ix["Lb"], ix["yB"][g.col]],
               np.r_[um(nz), -self.lqB * g.data], np.zeros(nz), np.zeros(nz))
        linhas(np.r_[z, g.row], np.r_[ix["La"], ix["yA"][g.col]],
               np.r_[um(nz), -self.lqA * g.data], np.zeros(nz), np.zeros(nz))
        self._cortes(linhas, ix["ub"], ix["Lb"])
        self._cortes(linhas, ix["ua"], ix["La"])
        if base_basico is not None:
            linhas(np.zeros(nz, int), ix["ub"], self.wz, [base_basico], [np.inf])
        if base_grave is not None:
            linhas(np.zeros(nz, int), ix["ua"], self.wz, [base_grave], [np.inf])

        # CVaR (Rockafellar-Uryasev): v_z >= eta - S_z, S_z = soma_b d_b u_zb
        zz = np.repeat(z, B)
        uu = ix["u"].reshape(B, nz).T.ravel()             # (z, b) em ordem de z
        linhas(np.r_[z, z, zz], np.r_[ix["v"], np.full(nz, ix["eta"][0]), uu],
               np.r_[um(nz), -um(nz), np.tile(self.d, nz)], np.zeros(nz), np.full(nz, np.inf))
        if eps is not None:
            linhas(np.zeros(nz + 1, int), np.r_[ix["eta"], ix["v"]],
                   np.r_[[1.0], -self.wz / SV.ALFA_CVAR], [eps], [np.inf])

        A = sparse.csr_matrix((np.concatenate(V), (np.concatenate(R), np.concatenate(C))),
                              shape=(nlin[0], self.nvar))
        return LinearConstraint(A, np.concatenate(lo), np.concatenate(hi))

    def _cortes(self, linhas, iu, iL):
        n = len(iu)
        for L0 in self.L0:
            x0 = np.exp(L0)
            r = np.arange(n)
            linhas(np.r_[r, r], np.r_[iu, iL], np.r_[np.ones(n), np.full(n, x0)],
                   np.full(n, -np.inf), np.full(n, 1 - x0 + x0 * L0))

    def _limites(self, fixa):
        lo, hi = np.zeros(self.nvar), np.ones(self.nvar)
        ix = self.ix
        for k in ("yB", "yA", "mB", "mA"):
            hi[ix[k]] = self.cap
        lmin = self.lqB * self.NB + self.lqA * self.NA
        for k in ("L", "Lb", "La"):
            lo[ix[k]], hi[ix[k]] = lmin, 0.0
        if fixa is not None:
            for k, y in (("yB", fixa[0]), ("yA", fixa[1])):
                lo[ix[k]] = hi[ix[k]] = y
        return Bounds(lo, hi)

    def resolve(self, objetivo="vidas", K=None, eps=None, base_basico=None,
                base_grave=None, tempo_max=600.0, gap=1e-4, fixa=None):
        """Resolve e devolve dict com yB, yA (unidades por local), valor do
        objetivo (por PCR), limite dual, gap e tempo."""
        ix = self.ix
        c = np.zeros(self.nvar)
        if objetivo == "vidas":
            c[ix["u"]] = -np.repeat(self.d, self.nz) * np.tile(self.wz, self.B)
        elif objetivo == "cvar":
            c[ix["eta"]] = -1.0
            c[ix["v"]] = self.wz / SV.ALFA_CVAR
        else:
            raise ValueError(objetivo)
        integ = np.zeros(self.nvar)
        integ[ix["yB"]] = integ[ix["yA"]] = 1
        t0 = time.time()
        res = milp(c, constraints=self._monta(K, eps, base_basico, base_grave),
                   integrality=integ, bounds=self._limites(fixa),
                   options={"time_limit": tempo_max, "mip_rel_gap": gap, "disp": False})
        out = {"status": int(res.status), "msg": str(res.message),
               "segundos": round(time.time() - t0, 1)}
        # o limite dual vale mesmo sem solucao viavel encontrada (parou no tempo)
        lim = getattr(res, "mip_dual_bound", None)
        if lim is not None and np.isfinite(lim):
            out["limite"] = float(-lim)
        if res.x is None:
            return out
        x = res.x
        out.update({
            "yB": np.rint(x[ix["yB"]]).astype(int), "yA": np.rint(x[ix["yA"]]).astype(int),
            "valor": float(-res.fun),
            "gap": float(getattr(res, "mip_gap", 0.0) or 0.0),
        })
        out.setdefault("limite", out["valor"])
        return out

    # ---- avaliacao exata nas zonas (sem cortes), para conferir o MILP
    def avalia(self, yB, yA):
        nB = np.stack([c.dot(yB) for c in self.cobre])            # (B, nz)
        nA = np.stack([c.dot(yA) for c in self.cobre])
        S = (self.d[:, None] * -np.expm1(self.lqB * nB + self.lqA * nA)).sum(axis=0)
        return float(np.sum(self.wz * S)), SV.cvar_inferior(S, self.wz), S


def para_indices(yB, yA):
    """Unidades por local -> vetor de locais por unidade (USB primeiro)."""
    loc = np.arange(len(yB))
    return np.repeat(loc, yB), np.repeat(loc, yA)


def por_local(idx, m):
    return np.bincount(np.asarray(idx, dtype=np.int64), minlength=m)


# ------------------------------------------------------------------- sanidade
def _teste():
    from itertools import combinations_with_replacement as cwr
    rng = np.random.default_rng(3)
    m, nz = 7, 40
    ps, dm = rng.random((m, 2)) * 12, rng.random((nz, 2)) * 12
    Tz = np.sqrt(((dm[:, None, :] - ps[None, :, :]) ** 2).sum(-1)).astype(np.float32)
    wz = rng.integers(100, 2000, nz).astype(float)
    x0B, x0A = por_local([0, 1], m), por_local([2], m)
    bd = tuple(np.arange(1.0, 15.01, 1.0))      # tempos brutos: faixas desde 0
    M = Modelo.de_tempos(Tz, wz, x0B, x0A, qB=0.35, qA=0.21, passo=0.05, bandas=bd, inicio=0.0)

    # forca bruta: todas as posicoes de 2 USB e 1 USA
    melhor = -1.0
    for b in cwr(range(m), 2):
        for a in range(m):
            v, _, _ = M.avalia(por_local(b, m), por_local([a], m))
            melhor = max(melhor, v)
    r = M.resolve()
    v_mip, _, _ = M.avalia(r["yB"], r["yA"])
    assert abs(v_mip - melhor) < 1e-9, (v_mip, melhor)       # achou o otimo
    assert r["valor"] >= melhor - 1e-9 and r["valor"] - melhor < 1e-3, (r["valor"], melhor)

    # K = 0 devolve a rede de hoje
    r0 = M.resolve(K=0)
    assert (r0["yB"] == x0B).all() and (r0["yA"] == x0A).all()
    # K maior nunca piora
    r1 = M.resolve(K=1)
    assert r1["valor"] >= r0["valor"] - 1e-9 and r["valor"] >= r1["valor"] - 1e-9

    # CVaR do MILP com o mapa fixo = cvar_inferior exato (a menos dos cortes)
    rc = M.resolve(objetivo="cvar", fixa=(x0B, x0A))
    _, cv, _ = M.avalia(x0B, x0A)
    assert abs(rc["valor"] - cv) < 2e-4, (rc["valor"], cv)
    # restricao de CVaR respeitada
    rmx = M.resolve(objetivo="cvar")
    alvo = 0.5 * (cv + rmx["valor"])
    re = M.resolve(eps=alvo)
    assert M.avalia(re["yB"], re["yA"])[1] >= alvo - 2e-4
    print(f"ok  MILP = forca bruta ({melhor:.5f}); K=0 -> hoje; K monotono; "
          f"CVaR linearizado = exato ({cv:.5f}); eps respeitado; "
          f"{r['segundos']:.1f} s")


if __name__ == "__main__":
    _teste()
