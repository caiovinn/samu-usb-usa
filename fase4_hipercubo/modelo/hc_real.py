"""Avaliador hipercubo aproximado sobre os dados reais de Sao Paulo.

Carga: zonas de 1 km (lista de preferencia por zona e classe), ponto fixo de
Larson (1975) nas ocupacoes das N unidades. Medidas: por setor (26.889), pela
ocupacao e pelos fatores Q obtidos. Mesmas medidas da fase 3 (vidas por 1.000
PCR, CVaR10, coberturas, tempos), so trocando a ocupacao independente e igual
por classe pela ocupacao endogena do hipercubo.

Regras de despacho (iguais as da simulacao, simula_vidas.py):
  grave  -> USA livre mais proxima
  basico -> USB livre mais proxima, senao USA livre mais proxima
  PCR (tracadora, nao gera carga) -> livre mais proxima de qualquer tipo

Sistema de PERDA (sem fila): na simulacao a fila e ~0% dos chamados (v5).
Servico exponencial de media `s_min` (o hipercubo exige); na simulacao e Gamma(2)
com a mesma media. A taxa de chamados por zona e a taxa total x populacao (como a
simulacao; nao ha taxa por zona nos dados).

Variantes do fator de correcao Q (hipercubo_aprox):
  "larson75"  Q'(N, rho, j) do artigo, N = todas as unidades, rho = a/N global.
  "local"     Q deduzido para o conjunto elegivel de cada lista (nosso, nao e do artigo).
  "daskin"    Q = 1 (ocupacao independente, mas com a ocupacao ENDOGENA de cada unidade).

Uso: ver experimentos/valida_real.py.
"""
import json

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.special import gammaln, logsumexp

from fase2_sao_paulo.modelo import huff2sfca as H
from fase3_vidas.modelo import mip_vidas as MV
from fase3_vidas.modelo import sobrevida as SV

from ..caminhos import DADOS_FASE2
from .hipercubo_aprox import fator_q

LADO_KM = 1.0
L_USB, L_USA = 12, 16          # unidades por lista (as mais proximas): resto pesa ~rho^12
L_USB_RESTO = 4                # USA apos as USB na lista do chamado basico
VARIANTES = ("larson75", "local", "daskin")
JMAX = 40                      # comprimento maximo de lista para os vetores Q

_C = {}


def dados():
    """Carrega uma vez por processo (leitura apenas das fases 2)."""
    if not _C:
        st = pd.read_parquet(DADOS_FASE2 / "sp_setores.parquet")
        cd = pd.read_parquet(DADOS_FASE2 / "sp_candidatos.parquet")
        Ts = np.load(DADOS_FASE2 / "sp_tempos.npy")                      # (setores, locais)
        U = json.load(open(DADOS_FASE2 / "sp_utilizacao.json", encoding="utf-8"))
        pop = st["pop"].values.astype(float)
        z = MV.zonas(st.lat.values, st.lon.values, LADO_KM)
        nz = int(z.max()) + 1
        w = pop + 1e-9
        A = sparse.csr_matrix((w, (z, np.arange(len(z)))), shape=(nz, len(z)))
        pz = np.asarray(A.sum(axis=1)).ravel()
        A = sparse.diags(1.0 / pz) @ A
        Tz = np.ascontiguousarray(np.minimum(A @ Ts, H.T_INALC).T.astype(np.float32))   # (locais, zonas)
        _C.update(st=st, cd=cd, T=np.ascontiguousarray(Ts.T), pop=pop, U=U, z=z, nz=nz,
                  pz=pz, Tz=Tz, x0B=cd.n_usb.values.astype(int), x0A=cd.n_usa.values.astype(int))
    return _C


# ------------------------------------------------------------------ fatores Q
def q_larson75(N, a, jmax):
    """Q'(N, rho=a/N, j), j = 0..jmax-1, eqs. (14)-(16) de Larson (1975), em log."""
    rho = a / N
    # P_N' (Erlang B) e P0' do sistema de perda com N servidores e carga a
    i = np.arange(N + 1)
    lp = i * np.log(a) - gammaln(i + 1)
    lse = logsumexp(lp)
    P0, PN = np.exp(-lse), np.exp(lp[N] - lse)
    out = np.empty(jmax)
    for j in range(jmax):
        k = np.arange(j, N)
        lt = (gammaln(N - j) + np.log(N - k) - gammaln(k - j + 1)
              + k * np.log(N) - gammaln(N + 1) + (k - j) * np.log(rho))
        qstar = np.exp(logsumexp(lt)) * P0 / (1 - rho)
        out[j] = qstar * (1.0 / (1 - PN)) ** j / (1 + rho * PN / (1 - rho))
    return out


def q_pool(Np, rho_med, jmax):
    """Fator 'local' (nosso) para um conjunto de Np unidades com ocupacao media rho_med."""
    q = fator_q(int(Np), float(rho_med))
    out = np.ones(jmax)
    n = min(jmax, len(q))
    out[:n] = q[:n]
    return out


# ------------------------------------------------------------------ listas
def _ordena(tl, k):
    """Indices das k menores linhas de tl (n, colunas), ordenadas, por coluna: (colunas, k)."""
    n = tl.shape[0]
    k = min(k, n)
    if k < n:
        idx = np.argpartition(tl, k - 1, axis=0)[:k]
    else:
        idx = np.broadcast_to(np.arange(n)[:, None], tl.shape).copy()
    v = np.take_along_axis(tl, idx, axis=0)
    o = np.argsort(v, axis=0, kind="stable")
    return np.take_along_axis(idx, o, axis=0).T


def listas(tu, nB, kB=L_USB, kA=L_USA, kA_resto=L_USB_RESTO):
    """Listas de preferencia por coluna de tu (unidades, colunas): grave, basico, USB-so, pool.

    Retorna indices de unidade (USB = 0..nB-1, USA = nB..N-1). Basico = USB mais
    proximas e depois as USA mais proximas, como a simulacao.
    """
    usb, usa = tu[:nB], tu[nB:]
    oB = _ordena(usb, kB)
    oA = _ordena(usa, kA) + nB
    grave = oA
    basico = np.concatenate([oB, oA[:, :min(kA_resto, oA.shape[1])]], axis=1)
    pool = _ordena(tu, kB)
    return dict(grave=grave, basico=basico, usb=oB, pool=pool)


# -------------------------------------------------------------- ponto fixo
def _empilha(Lg, Lb):
    kmax = max(Lg.shape[1], Lb.shape[1])
    pad = lambda L: np.pad(L, ((0, 0), (0, kmax - L.shape[1])), constant_values=-1)
    return np.concatenate([pad(Lg), pad(Lb)], axis=0)


def ocupacoes(loc, nB, lam_g_z, lam_b_z, mu, variante="larson75", tol=1e-10, max_iter=3000,
              ida_dep=None):
    """Ponto fixo nas ocupacoes das N unidades (zonas de 1 km). loc: local de cada unidade.

    lam_*_z: taxa de chamados por zona (por hora); mu: taxa de servico por hora.
    Retorna rho (N,) e o numero de iteracoes.

    ida_dep = (fator, atraso, ida_nominal, s_min) liga o servico DEPENDENTE DO DESLOCAMENTO
    (extensao nossa, inspirada na ideia de servico por local de Budge et al. 2009, cujo
    texto nao foi lido): como na simulacao da fase 3, o tempo ocupado da unidade u vale
    s_min + (ida media de u - ida_nominal). Sem o fator de normalizacao de Larson (a carga
    total passa a depender de rho). Padrao None: o hipercubo classico, mu fixo.
    """
    D = dados()
    N = len(loc)
    tz = D["Tz"][np.asarray(loc)]                          # (N, zonas)
    L = listas(tz, nB)
    Lm = _empilha(L["grave"], L["basico"])                 # (2Z, kmax)
    lam = np.concatenate([lam_g_z, lam_b_z])
    m, kmax = Lm.shape
    valido = Lm >= 0
    Ls = np.where(valido, Lm, 0)
    nA = N - nB
    a = lam.sum() / mu
    PN = float(np.exp(-logsumexp(np.arange(N + 1) * np.log(a) - gammaln(np.arange(N + 1) + 1))
                      + N * np.log(a) - gammaln(N + 1)))
    alvo = a * (1 - PN)                                    # soma dos rho = carga atendida (Erlangs)
    nz = len(lam_g_z)
    if variante == "larson75":
        Qg = q_larson75(N, a, kmax)
        Qrow = np.broadcast_to(Qg, (m, kmax))
    rho = np.full(N, alvo / N)
    mu = np.full(N, float(mu))
    if ida_dep is not None:
        f_c, a_c, ida_nom, s_min = ida_dep
        zona = np.tile(np.arange(nz), 2)[:, None]          # zona de cada linha (grave, basico)
        tcal = a_c + f_c * tz[Ls, zona]                    # (2Z, kmax) tempo calibrado ate a unidade
    for it in range(max_iter):
        if variante == "local":
            rA = rho[nB:].mean() if nA else 0.0
            rAll = rho.mean()
            Qrow = np.concatenate([np.broadcast_to(q_pool(nA, rA, kmax), (nz, kmax)),
                                   np.broadcast_to(q_pool(N, rAll, kmax), (nz, kmax))])
        elif variante == "daskin":
            Qrow = 1.0
        r = np.where(valido, rho[Ls], 0.0)
        antes = np.cumprod(np.concatenate([np.ones((m, 1)), r[:, :-1]], axis=1), axis=1)
        Pk = Qrow * antes * (1 - r) * valido
        wk = (lam[:, None] * Pk)[valido]
        carga = np.bincount(Ls[valido], weights=wk, minlength=N) / mu
        R = carga / (1 - rho)
        novo = R / (1 + R)
        if ida_dep is None:
            novo = novo * (alvo / novo.sum())
        else:
            ida_u = np.bincount(Ls[valido], weights=wk * tcal[valido], minlength=N) / np.maximum(
                np.bincount(Ls[valido], weights=wk, minlength=N), 1e-12)
            ida_u = np.where(np.bincount(Ls[valido], weights=wk, minlength=N) > 1e-12, ida_u, ida_nom)
            mu = 60.0 / np.maximum(s_min + (ida_u - ida_nom), 10.0)
        novo = np.clip(novo, 0, 1 - 1e-9)
        dif = np.max(np.abs(novo - rho))
        rho = 0.5 * rho + 0.5 * novo if dif > 1e-3 else novo
        if dif < tol:
            break
    return rho, it + 1


# ---------------------------------------------------------------- avaliacao
def _p_lista(rho, Ls, valido, Qrow):
    r = np.where(valido, rho[Ls], 0.0)
    antes = np.cumprod(np.concatenate([np.ones((r.shape[0], 1)), r[:, :-1]], axis=1), axis=1)
    return Qrow * antes * (1 - r) * valido


def avalia(yB, yA, fator, atraso, s_min, taxas, variante="larson75", detalhe=False,
           tau=SV.TAU_GUARDA, servico_ida=False, fase2=False):
    """Medidas por setor com a ocupacao do hipercubo.

    yB, yA: unidades por local. taxas = (taxa_usa, taxa_usb) em chamados/hora.
    Devolve vidas e cvar10 (por 1.000 PCR), cob_grave, cob_basico (%, regra real:
    USB depois USA), cob_basico_usb (so USB, como a guarda da fase 3), et_grave,
    et_basico (min, calibrados) e as ocupacoes medias q_usb, q_usa.
    """
    D = dados()
    iB, iA = MV.para_indices(yB, yA)
    loc = np.concatenate([iB, iA])
    nB, N = len(iB), len(iB) + len(iA)
    pz = D["pz"] / D["pz"].sum()
    mu = 60.0 / s_min
    ida_dep = None
    if servico_ida:
        from fase3_vidas.experimentos.simula_vidas import T_IDA
        ida_dep = (fator, atraso, atraso + fator * T_IDA, s_min)
    rho, it = ocupacoes(loc, nB, taxas[0] * pz, taxas[1] * pz, mu, variante, ida_dep=ida_dep)

    w = D["pop"] / D["pop"].sum()
    tu_b = D["T"][loc]                                      # (N, setores) bruto
    L = listas(tu_b, nB)
    tr = SV.resposta(tu_b, fator, atraso).astype(np.float64)   # (N, setores) calibrado
    a = (taxas[0] + taxas[1]) / mu
    nA = N - nB
    if variante == "larson75":
        Qg = q_larson75(N, a, JMAX)
        Q = {k: Qg for k in ("grave", "basico", "usb", "pool")}
    elif variante == "local":
        Q = {"grave": q_pool(nA, rho[nB:].mean(), JMAX), "basico": q_pool(N, rho.mean(), JMAX),
             "usb": q_pool(nB, rho[:nB].mean(), JMAX), "pool": q_pool(N, rho.mean(), JMAX)}
    else:
        Q = {k: np.ones(JMAX) for k in ("grave", "basico", "usb", "pool")}

    def mede_lista(Lm, Qv):
        valido = Lm >= 0
        Ls = np.where(valido, Lm, 0)
        Pk = _p_lista(rho, Ls, valido, Qv[None, :Lm.shape[1]])
        t = np.take_along_axis(tr.T, Ls, axis=1)             # (setores, k) tempos calibrados
        return Pk, t

    out = {}
    # PCR: unidade livre mais proxima de qualquer tipo; massa restante na ultima da lista
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
        out.update(metricas_fase2(L, Q, rho, loc, nB, iA, tu_b))
    out["q_usb"] = float(rho[:nB].mean())
    out["q_usa"] = float(rho[nB:].mean())
    out["iter"] = it
    if detalhe:
        out["S"], out["rho"] = S, rho
    return out


def metricas_fase2(L, Q, rho, loc, nB, iA, tu_b):
    """Tempo medio, Gini e pior decil no formato EXATO da fase 2b (huff2sfca.avalia, despacho).

    Mesmas definicoes: tempos BRUTOS do OSM, theta = fracao de graves dos dados; pool
    avancado = so USA; pool basico = livre mais proxima de QUALQUER tipo (a regra do pool
    basico da fase 2; a simulacao usa USB primeiro, e por isso cob_basico acima difere).
    Unica mudanca: as probabilidades de despacho vem do hipercubo, nao da ocupacao
    independente e igual. A massa 'todos ocupados' vai para o primeiro da lista, como
    huff2sfca.despacho.
    """
    D = dados()
    th = D["U"]["theta_dados"]
    pop = D["pop"]
    w = pop / pop.sum()
    m = len(D["cd"])

    def lista(Lm, Qv):
        valido = Lm >= 0
        Ls = np.where(valido, Lm, 0)
        Pk = _p_lista(rho, Ls, valido, Qv[None, :Lm.shape[1]])
        Pk[:, 0] += 1.0 - Pk.sum(1)
        return Pk, Ls, np.take_along_axis(tu_b.T, Ls, axis=1)

    Pg, Lg, tg = lista(L["grave"], Q["grave"])
    Pp, Lp, tp = lista(L["pool"], Q["pool"])
    # H2SFCA do pool avancado: A_i = sum_j R_j P_ji, R_j = unidades_j / demanda esperada em j
    cap = np.bincount(np.asarray(iA), minlength=m).astype(float)
    pressao = np.bincount(loc[Lg].ravel(), weights=(Pg * (th * pop)[:, None]).ravel(), minlength=m)
    R = np.divide(cap, pressao, out=np.zeros(m), where=pressao > 0)
    A_av = (Pg * R[loc[Lg]]).sum(1)
    T_av, T_ba = (Pg * tg).sum(1), (Pp * tp).sum(1)
    c10 = (Pg * (tg <= 10.0)).sum(1)
    return {"f_tempo": float(th * np.sum(w * T_av) + (1 - th) * np.sum(w * T_ba)),
            "f_gini": H.gini(A_av, pop),
            "cob_usa_10": float(100 * np.sum(w * c10)),
            "cob_usa_10_p10": float(100 * H.media_pior_decil(c10, pop)),
            "T_av": float(np.sum(w * T_av)), "T_ba": float(np.sum(w * T_ba))}


def taxas_sia():
    U = dados()["U"]["por_ano_12m"]
    return U["usa"] / 8760.0, U["usb"] / 8760.0


# --------------------------------------------------------------------- teste
def _teste():
    # Q'(N,rho,j) com N pequeno reproduz o artigo (Larson 1975, p. 863): N=3, rho=0,4
    q = q_larson75(3, 1.2, 3)
    assert abs(q[0] - 1) < 1e-9 and abs(q[1] - 0.862) < 1e-3 and abs(q[2] - 0.887) < 1e-3, q
    # N grande nao estoura (factoriais em log) e Q(j=0) = 1
    qg = q_larson75(123, 40.8, 16)
    assert np.all(np.isfinite(qg)) and abs(qg[0] - 1) < 1e-9, qg
    print("hc_real: Q' ok; Q'(123, 0,33, j=1..4) =", np.round(qg[1:5], 3))


if __name__ == "__main__":
    _teste()
