"""Huff + 2SFCA hierarquico para USB/USA.

Substitui a regra do "sempre a unidade mais proxima" por uma escolha
probabilistica de Huff, e usa essa probabilidade como peso nas duas etapas do
2SFCA (Luo 2014). Hierarquia do SAMU: chamado grave so pode ser atendido por
USA; chamado basico pode ser atendido por USB ou USA.

Contrato de entrada
-------------------
t      (n_candidatos, n_setores) float32, tempo de viagem em minutos
pop    (n_setores,)  float, populacao residente
idx_*  indices de LINHAS de t ocupadas por USB / USA (repeticao = mais de uma
       unidade no mesmo local)

A matriz vem com os candidatos nas LINHAS de proposito: o otimizador so usa as
linhas dos locais ocupados, e fatiar linhas de um array contiguo custa 2,6 ms
contra 34 ms de fatiar as colunas equivalentes.
"""
import numpy as np

# ---------------------------------------------------------------- parametros
# beta ancorado no despacho, nao no desfecho clinico: 4,5 min deixa cada setor
# com ~2,2 unidades efetivas (exp da entropia da distribuicao de Huff), que e a
# leitura operacional de "a mais proxima disponivel" quando a primeira esta
# ocupada. Ancorar na meia-vida de sobrevivencia (beta=8,5) espalharia a escolha
# por ~6,7 unidades e inflaria E[T] de 7,5 para 10,9 min. Ver sensibilidade.
BETA = 4.5      # min; decaimento gaussiano da escolha
ALFA = 1.0      # elasticidade da atratividade (S^alfa) no Huff
D0 = 30.0       # min; raio da area de captacao
THETA = 0.10    # fracao dos chamados que exige suporte avancado


def decai(t, beta=BETA, d0=D0):
    """Decaimento gaussiano truncado. Fora de d0 o peso e zero."""
    f = np.exp(-(t * t) / (2.0 * beta * beta))
    return np.where(t <= d0, f, 0.0)


def prepara(t, beta=BETA, d0=D0):
    """Matriz de decaimento f(t_ij), calculada uma unica vez.

    Nao depende de onde as ambulancias estao, so dos tempos. Guardar essa
    matriz tira a exponencial de dentro do laco do otimizador.
    """
    return decai(t, beta, d0).astype(np.float32)


def huff(t_sub, cap, alfa=ALFA, beta=BETA, d0=D0, f_sub=None):
    """P[j, i] = prob. de o setor i ser atendido pelo local j.

    t_sub: (m, n_setores) tempos apenas dos locais ocupados
    cap:   (m,) unidades em cada local (atratividade S)
    f_sub: decaimento ja calculado para esses locais (ver `prepara`)
    """
    f = decai(t_sub, beta, d0) if f_sub is None else f_sub
    # float32 de ponta a ponta: a matriz tem milhoes de celulas e o gargalo e
    # trafego de memoria, nao aritmetica
    w = np.asarray(cap, dtype=np.float32)[:, None] ** np.float32(alfa) \
        * np.asarray(f, dtype=np.float32)
    soma = w.sum(axis=0)
    orfao = soma <= 0            # setor sem local dentro de d0: vai no mais proximo
    if orfao.any():
        col = np.nonzero(orfao)[0]
        j = np.argmin(t_sub[:, col], axis=0)
        w[:, col] = 0.0
        w[j, col] = 1.0
        soma[col] = 1.0
    w /= soma[None, :]           # in place: evita mais uma copia
    return w


def acessibilidade(t_sub, cap, pop_pool, alfa=ALFA, beta=BETA, d0=D0,
                   f_sub=None):
    """H2SFCA de um pool de demanda. Devolve (A_i, P_ji, pressao_j).

    A_i        acessibilidade do setor i (unidades por habitante)
    pressao_j  demanda esperada sobre o local j, em habitantes
    """
    P = huff(t_sub, cap, alfa, beta, d0, f_sub)
    # P @ pop e R @ P passam pelo BLAS e nao criam matriz temporaria
    pressao = P.dot(np.asarray(pop_pool, dtype=np.float32))
    R = np.divide(cap, pressao, out=np.zeros(len(cap), dtype=np.float32),
                  where=pressao > 0).astype(np.float32)
    return R.dot(P), P, pressao


def tempo_esperado(t_sub, P):
    """E[T_i] sob a escolha de Huff."""
    return np.einsum("ji,ji->i", P, t_sub)   # sem temporario de (m, n)


def gini(x, w):
    """Gini de x ponderado por w. 0 = todo mundo com a mesma acessibilidade.

    A curva de Lorenz comeca na ORIGEM: o (0, 0) tem de entrar no somatorio
    dos trapezios. Sem ele falta a primeira fatia, (cw[0]-0)*(cx[0]+0), e o
    Gini de uma distribuicao perfeitamente igual nao da 0 e sim cw[0]*cx[0] —
    um piso que depende de qual elemento o argsort deixou em primeiro no
    empate. Com x constante isso ia de 6e-8 a 1,4e-5 conforme o setor que
    caisse ali, e derrubava a assercao do caso degenerado em _teste().

    O vies e da ordem de 1/n_setores ao quadrado, ~1e-9 nos 26.889 setores de
    SP: nenhum numero publicado muda. O que ele quebrava era o teste.
    """
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    cw = np.cumsum(w) / w.sum()
    cx = np.cumsum(x * w)
    if cx[-1] <= 0:
        return 0.0
    cx = cx / cx[-1]
    z = np.float64(0.0)
    cw = np.concatenate(([z], cw))      # origem da Lorenz
    cx = np.concatenate(([z], cx))
    return float(1 - np.sum((cw[1:] - cw[:-1]) * (cx[1:] + cx[:-1])))


def n_efetivo(P):
    """Numero efetivo de unidades que atendem cada setor (exp da entropia)."""
    return np.exp(-(P * np.log(np.maximum(P, 1e-12))).sum(axis=0))


def avalia(t, pop, idx_usb, idx_usa, alfa=ALFA, beta=BETA, d0=D0,
           theta=THETA, f=None):
    """Avalia uma configuracao da frota.

    Pools:
      avancado  theta * pop        -> so USA
      basico    (1 - theta) * pop  -> USB ou USA
    """
    idx_usb = np.asarray(idx_usb, dtype=np.int64)
    idx_usa = np.asarray(idx_usa, dtype=np.int64)

    # ---- pool avancado: apenas locais com USA
    loc_a, inv_a = np.unique(idx_usa, return_inverse=True)
    cap_a = np.bincount(inv_a, minlength=len(loc_a)).astype(np.float64)
    ta = t[loc_a]
    A_av, P_av, _ = acessibilidade(ta, cap_a, theta * pop, alfa, beta, d0,
                                   None if f is None else f[loc_a])
    T_av = tempo_esperado(ta, P_av)

    # ---- pool basico: locais com USB ou USA
    loc_b, inv_b = np.unique(np.concatenate([idx_usb, idx_usa]),
                             return_inverse=True)
    cap_b = np.bincount(inv_b, minlength=len(loc_b)).astype(np.float64)
    tb = t[loc_b]
    A_ba, P_ba, _ = acessibilidade(tb, cap_b, (1 - theta) * pop, alfa, beta, d0,
                                   None if f is None else f[loc_b])
    T_ba = tempo_esperado(tb, P_ba)

    w = pop / pop.sum()
    # objetivo 1 (minimizar): tempo esperado medio, ponderado pela gravidade
    f_tempo = float(theta * np.sum(w * T_av) + (1 - theta) * np.sum(w * T_ba))
    # objetivo 2 (minimizar): desigualdade da acessibilidade avancada, a
    # dimensao critica -- e onde a EDA achou 40,6 mi de pessoas descobertas
    f_gini = gini(A_av, pop)

    return {
        "f_tempo": f_tempo, "f_gini": f_gini,
        "A_av": A_av, "A_ba": A_ba, "T_av": T_av, "T_ba": T_ba,
        "pct_pop_usa_20min": float(100 * w[T_av <= 20].sum()),
        "pct_pop_usb_10min": float(100 * w[T_ba <= 10].sum()),
        "gini_basico": gini(A_ba, pop),
        "n_ef_usa": float(np.median(n_efetivo(P_av))),
    }


# ------------------------------------------------------------------- sanidade
def _teste():
    rng = np.random.default_rng(0)
    n, m = 500, 40
    ps, dm = rng.random((m, 2)) * 30, rng.random((n, 2)) * 30
    t = np.sqrt(((ps[:, None, :] - dm[None, :, :]) ** 2).sum(-1)).astype(np.float32)
    pop = rng.integers(200, 3000, n).astype(float)
    idx_usb, idx_usa = rng.integers(0, m, 30), rng.integers(0, m, 6)

    r = avalia(t, pop, idx_usb, idx_usa)
    loc = np.unique(idx_usb)
    P = huff(t[loc], np.bincount(idx_usb)[loc].astype(float))
    assert np.allclose(P.sum(axis=0), 1.0), "Huff nao soma 1 por setor"
    assert 0 <= r["f_gini"] <= 1 and r["f_tempo"] > 0
    # conservacao: acessibilidade ponderada pela populacao = oferta total
    assert np.isclose((r["A_av"] * pop * THETA).sum(), len(idx_usa), rtol=1e-4)
    # o decaimento pre-calculado tem de dar exatamente o mesmo
    r2 = avalia(t, pop, idx_usb, idx_usa, f=prepara(t))
    assert abs(r["f_tempo"] - r2["f_tempo"]) < 1e-4
    assert abs(r["f_gini"] - r2["f_gini"]) < 1e-9
    # distribuicao perfeitamente igual tem de dar Gini 0 EXATO, qualquer que
    # seja a ordem em que o argsort desempata (ver a docstring de gini)
    for ordem in (np.arange(n), np.argsort(pop), np.argsort(-pop)):
        assert abs(gini(np.full(n, 1.234), pop[ordem])) < 1e-12, "Gini com piso"

    # concentrar tudo num ponto piora o tempo e zera a desigualdade
    r3 = avalia(t, pop, np.zeros(30, int), np.zeros(6, int))
    assert r3["f_tempo"] > r["f_tempo"] and r3["f_gini"] < 1e-6
    print(f"ok  tempo={r['f_tempo']:.2f} min  gini={r['f_gini']:.3f}  "
          f"n_ef={r['n_ef_usa']:.1f}  (concentrado: tempo={r3['f_tempo']:.2f})")


if __name__ == "__main__":
    _teste()
