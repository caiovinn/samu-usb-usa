"""Avaliador hipercubo com DESEMPATE FIXO; fora isso, o mesmo calculo de fase4 hc_real.avalia.

Por que existe. Ha locais distintos com tempo IDENTICO ate o setor (encaixados
no mesmo no do OSM). No hc_real a ordem entre unidades empatadas sai do
argpartition, que nao e estavel: depende do mapa inteiro, e uma troca longe
pode inverter um empate num setor. Como as unidades empatadas tem ocupacoes
diferentes, isso muda o objetivo em ate ~2e-3 vidas por 1.000 PCR sem que nada
real tenha mudado -- e a busca aceita qualquer melhora > 1e-10, entao pode
aceitar trocas que sao so ruido de desempate.

Como. A ordem de cada lista passa a ser (tempo, local, USB antes de USA,
unidade). Para float32 positivo, o padrao de bits lido como inteiro tem a mesma
ordem que o numero; a chave inteira (bits do tempo << 8) | posicao_no_desempate
e unica e ordena exatamente como a tupla. O algoritmo e o do hc_real
(argpartition + argsort), so que sobre essa chave e no eixo contiguo.

Custo: ~0,18 s por avaliacao contra ~0,15 s do hc_real (+20%; argpartition em
int64 e mais lento que em float32). Tentativas de acelerar (ordem fixa dos
locais por setor + busca binaria; k+1 em float32 com correcao de empates na
fronteira) ficaram mais lentas: ~5 mil setores por lista tem empate na
fronteira (unidades da mesma base, setores inalcancaveis). O gargalo do
hc_real e montar as listas (~55%), nao o ponto fixo (~15%, ~35 iteracoes).

O ponto fixo, os fatores Q e as medidas sao os do hc_real, sem alteracao.
_teste() confere: listas = desempate canonico por forca bruta; resultado =
hc_real rodado com o mesmo desempate (diferenca < 1e-9); e mede o ruido.
"""
import numpy as np

from fase3_vidas.modelo import mip_vidas as MV
from fase3_vidas.modelo import sobrevida as SV
from fase4_hipercubo.modelo import hc_real as HR

def listas_canonicas(tu, nB, kB=HR.L_USB, kA=HR.L_USA, kA_resto=HR.L_USB_RESTO, loc=None):
    """hc_real.listas com desempate fixo (tempo, local, USB antes de USA, unidade).

    Ordena todas as unidades: lento, usado so nos setores em que o prefixo nao basta e no teste.
    """
    N = tu.shape[0]
    tipo = (np.arange(N) >= nB).astype(int)
    perm = np.lexsort((np.arange(N), tipo, loc))                    # ordem de desempate

    def ordena(sel, k):
        sel = sel[np.isin(sel, perm)]
        ordem = perm[np.isin(perm, sel)]
        o = np.argsort(tu[ordem].T, axis=1, kind="stable")[:, :min(k, len(ordem))]
        return ordem[o]
    oB = ordena(np.arange(nB), kB)
    oA = ordena(np.arange(nB, N), kA)
    basico = np.concatenate([oB, oA[:, :min(kA_resto, oA.shape[1])]], axis=1)
    return dict(grave=oA, basico=basico, usb=oB, pool=ordena(np.arange(N), kB))


class Avaliador:
    """hc_real.avalia com desempate fixo. Uma instancia por processo (guarda ~250 MB)."""

    def __init__(self, fator, atraso, s_min, taxas, variante="larson75"):
        D = HR.dados()
        self.D = D
        self.fator, self.atraso, self.s_min = fator, atraso, s_min
        self.taxas, self.variante = taxas, variante
        self.T = D["T"]                                             # (locais, setores), linhas contiguas
        self.TR = SV.resposta(self.T, fator, atraso)                # calibrado, float32, mesmo layout
        self.m, self.n = self.T.shape
        self.w = D["pop"] / D["pop"].sum()
        self.pz = D["pz"] / D["pz"].sum()
        self.n_aval = 0

    # ------------------------------------------------------------ listas
    @staticmethod
    def _k_menores(chave, k):
        """(linhas, k) colunas das k menores chaves (inteiras, unicas), em ordem."""
        n = chave.shape[1]
        k = min(k, n)
        idx = (np.argpartition(chave, k - 1, axis=1)[:, :k] if k < n
               else np.broadcast_to(np.arange(n), chave.shape).copy())
        o = np.argsort(np.take_along_axis(chave, idx, axis=1), axis=1)
        return np.take_along_axis(idx, o, axis=1)

    def listas(self, yB, yA, iB, iA):
        """Mesmo formato de hc_real.listas sobre os setores: grave, basico, usb, pool."""
        loc = np.concatenate([iB, iA])
        nB, N = len(iB), len(loc)
        tipo = (np.arange(N) >= nB).astype(np.int64)
        perm = np.lexsort((np.arange(N), tipo, loc))
        pos = np.empty(N, dtype=np.int64)
        pos[perm] = np.arange(N)                                    # posicao no desempate
        bits = self.T[loc].view(np.int32).astype(np.int64)         # tempos >= 0: ordem preservada
        chave = np.ascontiguousarray(((bits << 8) | pos[:, None]).T)  # (setores, N)
        oB = self._k_menores(chave[:, :nB], HR.L_USB)
        oA = nB + self._k_menores(chave[:, nB:], HR.L_USA)
        oP = self._k_menores(chave, HR.L_USB)
        basico = np.concatenate([oB, oA[:, :min(HR.L_USB_RESTO, oA.shape[1])]], axis=1)
        return dict(grave=oA, basico=basico, usb=oB, pool=oP)

    # ---------------------------------------------------------- avaliacao
    def avalia(self, yB, yA, detalhe=False, tau=SV.TAU_GUARDA, servico_ida=False, fase2=False):
        """Mesma saida de hc_real.avalia(yB, yA, fator, atraso, s_min, taxas, variante, ...)."""
        D = self.D
        yB = np.asarray(yB, dtype=np.int64)
        yA = np.asarray(yA, dtype=np.int64)
        iB, iA = MV.para_indices(yB, yA)
        loc = np.concatenate([iB, iA])
        nB, N = len(iB), len(iB) + len(iA)
        taxas, s_min, variante = self.taxas, self.s_min, self.variante
        mu = 60.0 / s_min
        ida_dep = None
        if servico_ida:
            from fase3_vidas.experimentos.simula_vidas import T_IDA
            ida_dep = (self.fator, self.atraso, self.atraso + self.fator * T_IDA, s_min)
        rho, it = HR.ocupacoes(loc, nB, taxas[0] * self.pz, taxas[1] * self.pz, mu, variante,
                               ida_dep=ida_dep)
        L = self.listas(yB, yA, iB, iA)
        tr_u = self.TR[loc].T                                       # (setores, N), vista
        a = (taxas[0] + taxas[1]) / mu
        nA = N - nB
        J = HR.JMAX
        if variante == "larson75":
            Qg = HR.q_larson75(N, a, J)
            Q = {k: Qg for k in ("grave", "basico", "usb", "pool")}
        elif variante == "local":
            Q = {"grave": HR.q_pool(nA, rho[nB:].mean(), J), "basico": HR.q_pool(N, rho.mean(), J),
                 "usb": HR.q_pool(nB, rho[:nB].mean(), J), "pool": HR.q_pool(N, rho.mean(), J)}
        else:
            Q = {k: np.ones(J) for k in ("grave", "basico", "usb", "pool")}

        def mede_lista(Lm, Qv):
            valido = Lm >= 0
            Ls = np.where(valido, Lm, 0)
            Pk = HR._p_lista(rho, Ls, valido, Qv[None, :Lm.shape[1]])
            t = np.take_along_axis(tr_u, Ls, axis=1).astype(np.float64)
            return Pk, t

        w = self.w
        out = {}
        Pk, t = mede_lista(L["pool"], Q["pool"])
        resto = np.clip(1.0 - Pk.sum(1), 0, None)
        S = (Pk * SV.s(t)).sum(1) + resto * SV.s(t[:, -1])
        out["vidas"] = float(1000 * np.sum(w * S))
        out["cvar10"] = float(1000 * SV.cvar_inferior(S, D["pop"]))
        for nome, chave in (("grave", "grave"), ("basico", "basico"), ("basico_usb", "usb")):
            Pk, t = mede_lista(L[chave], Q[chave])
            tot = Pk.sum(1)
            cob = ((Pk * (t <= tau)).sum(1)) / np.maximum(tot, 1e-12)
            et = (Pk * t).sum(1) / np.maximum(tot, 1e-12)
            out[f"cob_{nome}"] = float(100 * np.sum(w * cob))
            if not nome.endswith("usb"):
                out[f"et_{nome}"] = float(np.sum(w * et))
        if fase2:
            out.update(HR.metricas_fase2(L, Q, rho, loc, nB, iA, D["T"][loc]))
        out["q_usb"] = float(rho[:nB].mean())
        out["q_usa"] = float(rho[nB:].mean())
        out["iter"] = it
        if detalhe:
            out["S"], out["rho"] = S, rho
        self.n_aval += 1
        return out


# --------------------------------------------------------------------- teste
CAMPOS = ("vidas", "cvar10", "cob_grave", "cob_basico", "cob_basico_usb", "et_grave", "et_basico",
          "q_usb", "q_usa")


def compara(av, yB, yA, canonico=True, **kw):
    """Maior diferenca absoluta entre Avaliador.avalia e hc_real.avalia num mapa.

    canonico=True roda o hc_real com o mesmo desempate (listas_canonicas): a
    diferenca tem de ser so de arredondamento. False mede o ruido de desempate.
    """
    original = HR.listas
    if canonico:
        iB, iA = MV.para_indices(yB, yA)
        loc = np.concatenate([iB, iA])
        HR.listas = lambda tu, nB, *a, **k: (listas_canonicas(tu, nB, loc=loc)
                                             if tu.shape[1] == av.n else original(tu, nB, *a, **k))
    try:
        r0 = HR.avalia(yB, yA, av.fator, av.atraso, av.s_min, av.taxas, variante=av.variante, **kw)
    finally:
        HR.listas = original
    r1 = av.avalia(yB, yA, **kw)
    return max(abs(r0[c] - r1[c]) for c in CAMPOS), r0, r1


def mapas_teste(D, n_aleat=4, semente=0):
    """hoje + mapas com trocas aleatorias (inclusive concentrando unidades)."""
    rng = np.random.default_rng(semente)
    out = [("hoje", D["x0B"].copy(), D["x0A"].copy())]
    m = len(D["x0B"])
    for s in range(n_aleat):
        yB, yA = D["x0B"].copy(), D["x0A"].copy()
        for _ in range(10 + 20 * s):
            y = yB if rng.random() < 0.85 else yA
            j = rng.choice(np.nonzero(y)[0])
            y[j] -= 1
            y[rng.integers(m)] += 1
        out.append((f"aleatorio{s}", yB, yA))
    return out


def _teste():
    from fase3_vidas.experimentos import vidas as V
    f, a = V.fator()
    av = Avaliador(f, a, 70.0, HR.taxas_sia())
    pior, ruido = 0.0, 0.0
    for nome, yB, yA in mapas_teste(av.D):
        iB, iA = MV.para_indices(yB, yA)
        loc = np.concatenate([iB, iA])
        Lc = listas_canonicas(av.D["T"][loc], len(iB), loc=loc)
        Lr = av.listas(yB, yA, iB, iA)
        assert all(np.array_equal(Lc[k], Lr[k]) for k in Lc), f"listas diferentes em {nome}"
        d, r0, _ = compara(av, yB, yA, canonico=True)
        dr, _, _ = compara(av, yB, yA, canonico=False)
        pior, ruido = max(pior, d), max(ruido, dr)
        print(f"  {nome:11s} vidas {r0['vidas']:.4f}  dif. (mesmo desempate) {d:.1e}  "
              f"ruido de desempate do hc_real {dr:.1e}")
    assert pior < 1e-9, pior
    print(f"avaliador: listas identicas as canonicas; igual ao hc_real com o mesmo desempate "
          f"(max {pior:.1e}); ruido de desempate do original ate {ruido:.1e}")


if __name__ == "__main__":
    _teste()
