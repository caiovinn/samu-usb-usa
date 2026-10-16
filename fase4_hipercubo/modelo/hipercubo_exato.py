"""Hipercubo de Larson (1974), solucao exata para poucas unidades.

Estado = mascara de bits de ocupacao das n unidades (2^n estados). Chamados
chegam em Poisson; cada tipo de chamado tem uma lista de preferencia de
unidades (a primeira LIVRE da lista atende). Servico exponencial, taxa mu_u.

Sistema de PERDA: se todas as unidades da lista estao ocupadas o chamado e
bloqueado (nao entra em fila). Para a frota real a fila e rara (fase 2:
frac_fila ~ 0), entao P(bloqueio) aproxima a fracao de chamados que esperariam.
Esta e a validacao exata da aproximacao em hipercubo_aprox.py (n <= ~16).

Uso: exato(mu, listas, lam) -> dict(rho, P, bloq, pi)
"""
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator, bicgstab, spsolve

N_MAX = 22  # 2^22 = 4M estados; acima disso o solver esparso nao cabe


def _primeiro_livre(estados, lista):
    """Para cada estado, indice (posicao na lista) da primeira unidade livre; -1 se nenhuma."""
    n_est = estados.shape[0]
    achou = np.full(n_est, -1, dtype=np.int16)
    for pos, u in enumerate(lista):
        livre = ((estados >> u) & 1) == 0
        novo = livre & (achou < 0)
        achou[novo] = pos
    return achou


def exato(mu, listas, lam):
    """Distribuicao estacionaria exata do hipercubo (sistema de perda).

    mu: (n,) taxa de servico de cada unidade (1/tempo medio de servico)
    listas: lista de tuplas de indices de unidades, em ordem de preferencia
    lam: (m,) taxa de chegada de cada tipo (mesmas unidades de tempo de mu)
    Retorna rho (n,) fracao ocupada; P (m,n) prob. de a unidade u atender o
    tipo l; bloq (m,) prob. de bloqueio do tipo l; pi (2^n,) distribuicao.
    """
    mu = np.asarray(mu, float)
    lam = np.asarray(lam, float)
    n = len(mu)
    assert n <= N_MAX, f"n={n} grande demais para o hipercubo exato"
    assert len(listas) == len(lam)
    n_est = 1 << n
    est = np.arange(n_est, dtype=np.int64)

    # primeira unidade livre de cada lista em cada estado
    escolha = []  # por lista: (n_est,) unidade que atende, -1 se bloqueado
    for lista in listas:
        lista = tuple(lista)
        pos = _primeiro_livre(est, lista)
        u = np.where(pos >= 0, np.asarray(lista)[np.maximum(pos, 0)], -1)
        escolha.append(u)

    # gerador: chegadas (b -> b | bit u) e partidas (b -> b & ~bit u, taxa mu_u)
    linhas, colunas, vals = [], [], []
    for l, u in enumerate(escolha):
        ok = u >= 0
        de = est[ok]
        para = de | (1 << u[ok].astype(np.int64))
        linhas.append(de)
        colunas.append(para)
        vals.append(np.full(de.shape[0], lam[l]))
    for u in range(n):
        ocup = ((est >> u) & 1) == 1
        de = est[ocup]
        linhas.append(de)
        colunas.append(de & ~(1 << u))
        vals.append(np.full(de.shape[0], mu[u]))
    L = np.concatenate(linhas)
    C = np.concatenate(colunas)
    V = np.concatenate(vals)
    taxas = sp.coo_matrix((V, (L, C)), shape=(n_est, n_est)).tocsr()
    saida = np.asarray(taxas.sum(axis=1)).ravel()
    Q = taxas - sp.diags(saida)

    # pi Q = 0: fixa pi do ultimo estado em 1 (sistema esparso, sem linha densa)
    # e normaliza depois; o ultimo estado (todas ocupadas) tem prob. > 0.
    A = Q.T.tocsr()
    pi = np.empty(n_est)
    pi[-1] = 1.0
    B = A[:-1, :-1].tocsr()
    rhs = -A[:-1, -1].toarray().ravel()
    if n_est <= 2048:
        pi[:-1] = spsolve(B.tocsc(), rhs)
    else:  # fill-in do LU explode; iterativo com precondicionador diagonal
        dg = B.diagonal()
        M = LinearOperator(B.shape, matvec=lambda v: v / dg)
        x, info = bicgstab(B, rhs, rtol=1e-13, atol=0.0, maxiter=20000, M=M)
        assert info == 0, f"bicgstab nao convergiu (info={info})"
        pi[:-1] = x
    pi = np.clip(pi, 0, None)
    pi /= pi.sum()

    rho = np.array([pi[((est >> u) & 1) == 1].sum() for u in range(n)])
    m = len(listas)
    P = np.zeros((m, n))
    bloq = np.zeros(m)
    for l, u in enumerate(escolha):
        for k in range(n):
            P[l, k] = pi[u == k].sum()
        bloq[l] = pi[u < 0].sum()
    return dict(rho=rho, P=P, bloq=bloq, pi=pi)


def erlang_b(c, a):
    """Probabilidade de bloqueio de Erlang B (recursao estavel)."""
    b = 1.0
    for k in range(1, c + 1):
        b = a * b / (k + a * b)
    return b


def _teste():
    # 1) M/M/c: todas as unidades na mesma lista -> Erlang B, media de rho = a(1-B)/c
    for c, a in [(1, 0.4), (3, 1.5), (6, 4.0), (10, 3.0)]:
        r = exato(np.ones(c), [tuple(range(c))], [a])
        B = erlang_b(c, a)
        assert abs(r["bloq"][0] - B) < 1e-9, (c, a, r["bloq"][0], B)
        # a ordem fixa da lista desigualha as unidades; so a media e a/c*(1-B)
        assert abs(r["rho"].mean() - a * (1 - B) / c) < 1e-9
        assert np.all(np.diff(r["rho"]) <= 1e-12)  # quem esta na frente trabalha mais
        assert abs(r["P"][0].sum() + r["bloq"][0] - 1) < 1e-9

    # 2) conservacao: sum rho_u mu_u = sum lam_l (1 - bloq_l), com mu e listas distintas
    rng = np.random.default_rng(0)
    n = 7
    mu = rng.uniform(0.5, 2.0, n)
    listas = [tuple(rng.permutation(n)[:rng.integers(2, n)]) for _ in range(5)]
    lam = rng.uniform(0.2, 1.0, 5)
    r = exato(mu, listas, lam)
    assert abs((r["rho"] * mu).sum() - (lam * (1 - r["bloq"])).sum()) < 1e-9
    assert np.allclose(r["P"].sum(1) + r["bloq"], 1, atol=1e-9)

    # 3) carga -> 0: o primeiro da lista atende com prob. -> 1
    r = exato(mu, listas, lam * 1e-6)
    for l, lista in enumerate(listas):
        assert r["P"][l, lista[0]] > 1 - 1e-4

    # 4) forca bruta independente (n=3, solucao densa por iteracao de potencia)
    mu3 = np.array([1.0, 2.0, 1.5])
    listas3 = [(0, 1, 2), (2, 1)]
    lam3 = np.array([0.7, 0.5])
    r = exato(mu3, listas3, lam3)
    n_est = 8
    G = np.zeros((n_est, n_est))
    for b in range(n_est):
        for l, lista in enumerate(listas3):
            for u in lista:
                if not (b >> u) & 1:
                    G[b, b | (1 << u)] += lam3[l]
                    break
        for u in range(3):
            if (b >> u) & 1:
                G[b, b & ~(1 << u)] += mu3[u]
    G -= np.diag(G.sum(1))
    w, v = np.linalg.eig(G.T)
    pi = np.real(v[:, np.argmin(np.abs(w))])
    pi /= pi.sum()
    assert np.allclose(r["pi"], pi, atol=1e-9)
    print("hipercubo_exato: testes ok")


if __name__ == "__main__":
    _teste()
