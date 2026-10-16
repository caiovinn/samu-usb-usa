"""Hipercubo aproximado (ponto fixo nas ocupacoes), estilo Larson (1975).

Para a lista de preferencia l e a unidade na posicao k (ordem 1..N_l):

    P[l,u] = Q_k * prod_{j<k} rho[l_j] * (1 - rho[u])        (Daskin: Q_k = 1)
    rho[u] * mu[u] = sum_l lam[l] * P[l,u]                    (ponto fixo)

Q_k corrige a dependencia entre ocupacoes. Aqui e derivado de primeiros
principios para unidades intercambiaveis: com o numero de ocupadas m ~ perda
de Erlang (N_l servidores, carga a), P(as k-1 primeiras ocupadas e a k-esima
livre) = sum_m p_m C(N-k, m-k+1)/C(N, m); Q_k e essa razao sobre o produto
independente avaliado em rho_medio da lista (a escolhida de modo que a(1-B)=N*rho_medio).
Variantes:
  "daskin"   Q_k = 1 (ocupacao independente, a das fases 2b e 3).
  "local"    Q_k deduzido aqui (Erlang sobre a lista); NAO e de Larson.
  "larson75" Larson (1975, Oper. Res. 23(5):845-868), lido no texto: eqs. (14)-(16)
             para Q'(N,rho,j) do sistema de perda M/M/N/0, ponto fixo (21) com
             lambda_D = 0 e normalizacao de Larson (passo 2: media dos rho = r).
             Reproduz o exemplo de 3 unidades do artigo (ver _teste).
Budge, Ingolfsson & Erkut (2009) NAO foi lido (so metadados): servico por local e
varias unidades por local nao estao implementados como no artigo.
"""
import numpy as np
from math import factorial

from scipy.special import gammaln

from .hipercubo_exato import erlang_b


def _lcomb(n, k):
    return gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)


def _carga_erlang(N, rho_med):
    """Carga oferecida a tal que a(1-B(N,a)) = N*rho_med (bisecao)."""
    alvo = N * rho_med
    lo, hi = 0.0, max(10.0 * N, 1.0)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if mid * (1 - erlang_b(N, mid)) < alvo:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


_CACHE = {}


def fator_q(N, rho_med):
    """Vetor Q_k, k = 1..N+1 (o ultimo e o de 'todas ocupadas')."""
    rho_med = float(np.clip(rho_med, 1e-9, 1 - 1e-9))
    chave = (N, round(rho_med, 6))
    if chave in _CACHE:
        return _CACHE[chave]
    a = _carga_erlang(N, rho_med)
    m = np.arange(N + 1)
    lp = m * np.log(a) - gammaln(m + 1)
    p = np.exp(lp - lp.max())
    p /= p.sum()
    Q = np.ones(N + 1)
    for k in range(1, N + 1):
        ms = np.arange(k - 1, N)  # m de k-1 ate N-1
        t = p[ms] * np.exp(_lcomb(N - k, ms - (k - 1)) - _lcomb(N, ms))
        indep = rho_med ** (k - 1) * (1 - rho_med)
        Q[k - 1] = t.sum() / indep
    # todas as N ocupadas: p_N (so a configuracao cheia) vs rho^N
    Q[N] = p[N] / rho_med ** N
    _CACHE[chave] = Q
    return Q


def _empacota(listas):
    m = len(listas)
    kmax = max(len(x) for x in listas)
    L = -np.ones((m, kmax), dtype=np.int64)
    for i, x in enumerate(listas):
        L[i, : len(x)] = x
    return L


def aprox(mu, listas, lam, variante="local", tol=1e-10, max_iter=2000, amorte=0.2):
    """Ponto fixo. Retorna rho (n,), P (m,n) disperso como (m,kmax) em 'Pk', bloq (m,)."""
    mu = np.asarray(mu, float)
    lam = np.asarray(lam, float)
    n = len(mu)
    L = _empacota(listas)
    m, kmax = L.shape
    valido = L >= 0
    Ls = np.where(valido, L, 0)
    Nl = valido.sum(1)
    rho = np.full(n, 0.1)
    for it in range(max_iter):
        r = np.where(valido, rho[Ls], 0.0)  # ocupacao na posicao k
        antes = np.cumprod(np.concatenate([np.ones((m, 1)), r[:, :-1]], axis=1), axis=1)
        # as posicoes invalidas tem r=0: nao importa, P sera zerado pela mascara
        if variante == "local":
            Qk = np.ones((m, kmax + 1))
            rm = np.where(valido, rho[Ls], 0.0).sum(1) / Nl
            for N in np.unique(Nl):
                idx = np.where(Nl == N)[0]
                for i in idx:
                    Qk[i, : N + 1] = fator_q(int(N), rm[i])
        else:
            Qk = np.ones((m, kmax + 1))
        Pk = Qk[:, :kmax] * antes * (1 - r) * valido
        # bloqueio explicito (todas ocupadas) e renormalizacao: sum P + bloq = 1
        todas = np.prod(np.where(valido, r, 1.0), axis=1)
        qtodas = Qk[np.arange(m), Nl]
        bloq = qtodas * todas
        z = Pk.sum(1) + bloq
        Pk = Pk / z[:, None]
        bloq = bloq / z
        # taxa servida por unidade
        carga = np.zeros(n)
        np.add.at(carga, Ls[valido], (lam[:, None] * Pk)[valido])
        novo = np.clip(carga / mu, 0.0, 1 - 1e-9)
        if np.max(np.abs(novo - rho)) < tol:
            rho = novo
            break
        rho = (1 - amorte) * rho + amorte * novo
    return dict(rho=rho, Pk=Pk, L=L, bloq=bloq, iter=it + 1)


def q_linha(N, rho, j):
    """Q'(N,rho,j) de Larson (1975), eqs. (14)-(16), sistema de perda M/M/N/0."""
    P = np.array([N ** k * rho ** k / factorial(k) for k in range(N + 1)])
    P0 = 1.0 / P.sum()
    PN = P[N] * P0
    soma = sum(factorial(N - j - 1) * (N - k) / factorial(k - j) * (N ** k / factorial(N)) * rho ** (k - j)
               for k in range(j, N))
    qstar = soma * P0 / (1 - rho)  # eq. (3)/(5) com P0 -> P0'
    return qstar * (1.0 / (1 - PN)) ** j / (1 + rho * PN / (1 - rho))


def aprox_larson75(mu, listas, lam, tol=1e-12, max_iter=5000):
    """Ponto fixo de Larson (1975) para o sistema de perda.

    Mesmas entradas de aprox(). rho_global = lam_total/(N*mu_medio) (Larson usa mu
    unico; com mu distintos esta e uma generalizacao NOSSA, nao do artigo).
    Retorna rho, Pk (m,kmax), L, bloq, iter.
    """
    mu = np.asarray(mu, float)
    lam = np.asarray(lam, float)
    n = len(mu)
    L = _empacota(listas)
    m, kmax = L.shape
    valido = L >= 0
    Ls = np.where(valido, L, 0)
    a = lam.sum() / mu.mean()  # carga oferecida em Erlangs
    rho_g = a / n
    # r = rho(1-P_N'), eq. (13); soma dos rho_i*mu_i fixada em lam(1-P_N')
    PN = erlang_b(n, a)
    alvo = lam.sum() * (1 - PN)
    Q = np.array([q_linha(n, rho_g, j) if rho_g < 1 else 1.0 for j in range(kmax)])
    r0 = rho_g * (1 - PN)
    rho = np.full(n, r0)
    for it in range(max_iter):
        r = np.where(valido, rho[Ls], 0.0)
        antes = np.cumprod(np.concatenate([np.ones((m, 1)), r[:, :-1]], axis=1), axis=1)
        Pk = Q[None, :kmax] * antes * (1 - r) * valido
        carga = np.zeros(n)
        np.add.at(carga, Ls[valido], (lam[:, None] * Pk)[valido])
        # (21): 1 - rho = 1/(1+R) com R = carga/(1-rho_i) ; com mu_i: rho = R/(mu+R)
        R = carga / (1 - rho)
        novo = R / (mu + R)
        g = alvo / (novo * mu).sum()  # passo 2: normalizacao
        novo = np.clip(novo * g, 0, 1 - 1e-9)
        if np.max(np.abs(novo - rho)) < tol:
            rho = novo
            break
        rho = novo
    r = np.where(valido, rho[Ls], 0.0)
    antes = np.cumprod(np.concatenate([np.ones((m, 1)), r[:, :-1]], axis=1), axis=1)
    Pk = Q[None, :kmax] * antes * (1 - r) * valido
    bloq = np.clip(1.0 - Pk.sum(1), 0.0, 1.0)
    return dict(rho=rho, Pk=Pk, L=L, bloq=bloq, iter=it + 1)


def matriz_p(res, n):
    """P (m,n) densa a partir de Pk, para comparar com o exato."""
    L, Pk = res["L"], res["Pk"]
    P = np.zeros((L.shape[0], n))
    for k in range(L.shape[1]):
        ok = L[:, k] >= 0
        P[np.where(ok)[0], L[ok, k]] += Pk[ok, k]
    return P


def _teste():
    from .hipercubo_exato import exato

    # M/M/c homogenea: Larson deve reproduzir o exato quase exatamente
    for c, a in [(3, 1.5), (6, 4.0), (10, 3.0)]:
        ex = exato(np.ones(c), [tuple(range(c))], [a])
        ap = aprox(np.ones(c), [tuple(range(c))], [a])
        assert abs(ap["bloq"][0] - ex["bloq"][0]) < 0.02, (c, a, ap["bloq"], ex["bloq"])
    # exemplo de 3 unidades de Larson (1975), pp. 861-864: aproximado e exato publicados
    assert abs(q_linha(3, 0.4, 1) - 0.862) < 1e-3 and abs(q_linha(3, 0.4, 2) - 0.887) < 1e-3
    f = np.array([.125, .125, .125, .125, .25, .125, .125])
    listas_l = [(0, 1, 2)] * 3 + [(2, 1, 0), (1, 2, 0), (2, 1, 0), (2, 1, 0)]
    ap = aprox_larson75(np.ones(3), listas_l, 1.2 * f, tol=1e-6)
    assert np.allclose(ap["rho"], [0.351, 0.367, 0.374], atol=1.5e-3), ap["rho"]
    ex = exato(np.ones(3), listas_l, 1.2 * f)
    assert np.allclose(ex["rho"], [0.3548, 0.3650, 0.3724], atol=1e-4), ex["rho"]

    # instancia heterogenea: a correcao local erra menos que a ocupacao independente (Daskin)
    rng = np.random.default_rng(1)
    n = 8
    mu = rng.uniform(0.5, 2.0, n)
    listas = [tuple(rng.permutation(n)[:6]) for _ in range(6)]
    for esc in (1, 3):
        lam = rng.uniform(0.1, 0.5, 6) * esc
        ex = exato(mu, listas, lam)
        err = {}
        for v in ("daskin", "local", "larson75"):
            ap = aprox_larson75(mu, listas, lam) if v == "larson75" else aprox(mu, listas, lam, variante=v)
            assert ap["iter"] < 2000
            # conservacao no ponto fixo: carga atendida = sum rho*mu
            if v != "larson75":
                assert np.allclose(matriz_p(ap, n).sum(1) + ap["bloq"], 1, atol=1e-9)  # larson75 fixa a carga total por Erlang B, nao por lista
                assert abs((ap["rho"] * mu).sum() - (lam * (1 - ap["bloq"])).sum()) < 1e-6
            else:
                assert abs((ap["rho"] * mu).sum() - (lam * (1 - ap["bloq"])).sum()) < 0.05 * lam.sum()
            err[v] = np.abs(ap["rho"] - ex["rho"]).max()
        assert err["local"] < err["daskin"], (esc, err)
    print("hipercubo_aprox: testes ok")


if __name__ == "__main__":
    _teste()
