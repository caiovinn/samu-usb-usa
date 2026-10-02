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

# modelo "despacho": o regulador manda a unidade DISPONIVEL mais proxima
# (Daskin 1983, ReVelle & Hogan 1989). A unica aleatoriedade e quem esta
# ocupado; q e a ocupacao de cada unidade. 0,27 e o q equivalente ao
# BETA=4,5 pelo numero efetivo de unidades (ver n_ef_despacho); o valor
# estimado dos dados do SIA fica em dados/fase2/sp_utilizacao.json.
MODELO = "huff"   # "huff" (publicado) | "despacho"
Q = 0.27          # ocupacao de cada unidade
K_DESP = 12       # locais mais proximos considerados; o resto pesa ~q^12
T_INALC = 999.0   # tempo que monta.py grava para par inalcancavel
TAUS = (8.0, 10.0, 15.0, 20.0)   # min; limiares da cobertura probabilistica da USA


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


def despacho(t_sub, log_ocup, k=K_DESP):
    """P[j, i] sob a regra do despacho: atende a unidade DISPONIVEL mais proxima.

    log_ocup[j] = ln P(todas as unidades do local j ocupadas) = soma dos ln q
    das suas unidades, supondo ocupacoes independentes (Daskin). Entao

        P(j atende i) = prod_{l mais perto de i que j} e^{log_ocup_l}
                        * (1 - e^{log_ocup_j})

    A distancia decide a ORDEM, nao o peso: diferente do Huff gaussiano, a
    chance de o mais proximo estar ocupado nao depende de quao perto ele esta.
    So os k locais mais proximos entram (o que sobra pesa ~q^k); a massa de
    "todos ocupados" e dos inalcancaveis vai para o mais proximo — o chamado
    espera por ele.
    """
    m, n = t_sub.shape
    k = min(k, m)
    if k < m:
        part = np.argpartition(t_sub, k - 1, axis=0)[:k]
        o = np.argsort(np.take_along_axis(t_sub, part, axis=0), axis=0,
                       kind="stable")
        idx = np.take_along_axis(part, o, axis=0)
    else:
        idx = np.argsort(t_sub, axis=0, kind="stable")
    a = np.asarray(log_ocup, dtype=np.float64)[idx]            # (k, n)
    # soma EXCLUSIVA (so os mais proximos): subtrair a da soma inclusiva daria
    # -inf - (-inf) = nan quando q = 0
    antes = np.zeros_like(a)
    np.cumsum(a[:-1], axis=0, out=antes[1:])
    p = np.exp(antes) * -np.expm1(a)
    p[np.take_along_axis(t_sub, idx, axis=0) >= T_INALC] = 0.0
    p[0] += 1.0 - p.sum(axis=0)
    P = np.zeros((m, n), dtype=np.float32)
    np.put_along_axis(P, idx, p.astype(np.float32), axis=0)
    return P


def n_ef_despacho(q):
    """N_ef de uma fila infinita de unidades com ocupacao q: e^H da geometrica
    (1-q) q^(k-1). Forma fechada; e a ponte com o N_ef do Huff."""
    q = np.asarray(q, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = (-(1 - q) * np.log1p(-q) - np.where(q > 0, q * np.log(q), 0.0)) / (1 - q)
    return np.exp(h)


def _log_ocup(loc, inv, q_por_unidade):
    """ln P(local todo ocupado) = soma de ln q das unidades do local."""
    with np.errstate(divide="ignore"):
        lq = np.log(np.asarray(q_por_unidade, dtype=np.float64))
    return np.bincount(inv, weights=lq, minlength=len(loc))


def _q_unidades(q, idx):
    """q escalar, ou um q por candidato (indexado pelo local de cada unidade)."""
    q = np.asarray(q, dtype=np.float64)
    return np.full(len(idx), float(q)) if q.ndim == 0 else q[idx]


def acessibilidade(t_sub, cap, pop_pool, alfa=ALFA, beta=BETA, d0=D0,
                   f_sub=None, P=None):
    """H2SFCA de um pool de demanda. Devolve (A_i, P_ji, pressao_j).

    A_i        acessibilidade do setor i (unidades por habitante)
    pressao_j  demanda esperada sobre o local j, em habitantes
    P          probabilidades ja calculadas (modelo despacho); sem ela, Huff
    """
    if P is None:
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


def cobertura(t_sub, P, tau):
    """P(T_i <= tau): chance de a unidade que atende i chegar em ate tau min."""
    return np.einsum("ji,ji->i", P, (t_sub <= tau).astype(np.float32))


def media_pior_decil(x, w):
    """Media de x nos 10% da populacao com os MENORES valores de x."""
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    cw = np.cumsum(w) / w.sum()
    s = cw <= 0.10
    s[np.argmax(~s)] = True          # inclui o setor que cruza os 10%
    return float(np.average(x[s], weights=w[s]))


def avalia(t, pop, idx_usb, idx_usa, alfa=ALFA, beta=BETA, d0=D0,
           theta=THETA, f=None, modelo=MODELO, q_usb=Q, q_usa=Q,
           k_desp=K_DESP, detalhe=True, tau_restr=None):
    """Avalia uma configuracao da frota.

    Pools:
      avancado  theta * pop        -> so USA
      basico    (1 - theta) * pop  -> USB ou USA

    modelo="huff"      escolha de Huff gaussiana (beta, alfa, d0)
    modelo="despacho"  unidade disponivel mais proxima, ocupacao q_usb/q_usa
                       (escalar, ou um valor por candidato)
    detalhe=False pula as metricas que o otimizador nao usa.
    tau_restr      se dado, calcula "cob_restr_p10" (cobertura da USA em ate
                   tau_restr min no pior decil) mesmo com detalhe=False, para
                   a restricao do otimizador
    """
    idx_usb = np.asarray(idx_usb, dtype=np.int64)
    idx_usa = np.asarray(idx_usa, dtype=np.int64)
    desp = modelo == "despacho"

    # ---- pool avancado: apenas locais com USA
    loc_a, inv_a = np.unique(idx_usa, return_inverse=True)
    cap_a = np.bincount(inv_a, minlength=len(loc_a)).astype(np.float64)
    ta = t[loc_a]
    P = (despacho(ta, _log_ocup(loc_a, inv_a, _q_unidades(q_usa, idx_usa)),
                  k_desp) if desp else None)
    A_av, P_av, _ = acessibilidade(ta, cap_a, theta * pop, alfa, beta, d0,
                                   None if f is None else f[loc_a], P)
    T_av = tempo_esperado(ta, P_av)

    # ---- pool basico: locais com USB ou USA
    todos = np.concatenate([idx_usb, idx_usa])
    loc_b, inv_b = np.unique(todos, return_inverse=True)
    cap_b = np.bincount(inv_b, minlength=len(loc_b)).astype(np.float64)
    tb = t[loc_b]
    if desp:
        q_un = np.concatenate([_q_unidades(q_usb, idx_usb),
                               _q_unidades(q_usa, idx_usa)])
        P = despacho(tb, _log_ocup(loc_b, inv_b, q_un), k_desp)
    A_ba, P_ba, _ = acessibilidade(tb, cap_b, (1 - theta) * pop, alfa, beta, d0,
                                   None if f is None else f[loc_b], P)
    T_ba = tempo_esperado(tb, P_ba)

    w = pop / pop.sum()
    # objetivo 1 (minimizar): tempo esperado medio, ponderado pela gravidade
    f_tempo = float(theta * np.sum(w * T_av) + (1 - theta) * np.sum(w * T_ba))
    # objetivo 2 (minimizar): desigualdade da acessibilidade avancada, a
    # dimensao critica -- e onde a EDA achou 40,6 mi de pessoas descobertas
    f_gini = gini(A_av, pop)
    r = {"f_tempo": f_tempo, "f_gini": f_gini}
    if tau_restr is not None:
        r["cob_restr_p10"] = 100 * media_pior_decil(cobertura(ta, P_av, tau_restr), pop)
    if not detalhe:
        return r

    r.update({
        "A_av": A_av, "A_ba": A_ba, "T_av": T_av, "T_ba": T_ba,
        "pct_pop_usa_20min": float(100 * w[T_av <= 20].sum()),
        "pct_pop_usb_10min": float(100 * w[T_ba <= 10].sum()),
        "gini_basico": gini(A_ba, pop),
        "n_ef_usa": float(np.median(n_efetivo(P_av))),
        # mesma razao do Huff: chance de o mais proximo atender, mediana
        "p_mais_prox_usa": float(np.median(P_av.max(axis=0))),
    })
    # cobertura probabilistica da USA: "cada minuto conta" no objetivo, nao
    # na probabilidade de despacho
    for tau in TAUS:
        c = cobertura(ta, P_av, tau)
        r[f"cob_usa_{tau:g}"] = float(100 * np.sum(w * c))
        r[f"cob_usa_{tau:g}_p10"] = 100 * media_pior_decil(c, pop)
    return r


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

    # ---- modelo despacho
    loc, inv = np.unique(idx_usb, return_inverse=True)
    tl = t[loc]
    # q = 0: ninguem ocupado -> exatamente a regra do mais proximo
    P0 = despacho(tl, _log_ocup(loc, inv, np.zeros(len(idx_usb))))
    assert np.array_equal(P0.argmax(axis=0), tl.argmin(axis=0)) and \
        np.allclose(P0.max(axis=0), 1.0), "q=0 nao e o mais proximo"
    for q in (0.1, 0.3, 0.6):
        Pq = despacho(tl, _log_ocup(loc, inv, np.full(len(idx_usb), q)))
        assert np.allclose(Pq.sum(axis=0), 1.0, atol=1e-5), "despacho nao soma 1"
    # conservacao do 2SFCA vale para qualquer P que some 1 por setor
    rd = avalia(t, pop, idx_usb, idx_usa, modelo="despacho", q_usb=0.3, q_usa=0.3)
    assert np.isclose((rd["A_av"] * pop * THETA).sum(), len(idx_usa), rtol=1e-4)
    # com 40 locais de 1 unidade e k=40, o N_ef empirico e o da geometrica
    um = np.arange(m)
    Pg = despacho(t, _log_ocup(um, um, np.full(m, 0.3)), k=m)
    assert abs(np.median(n_efetivo(Pg)) - n_ef_despacho(0.3)) < 1e-3
    assert abs(n_ef_despacho(0.27) - 2.22) < 0.01 and n_ef_despacho(0.0) == 1.0
    # q por candidato: um local quase sempre ocupado perde a demanda
    qc = np.full(m, 0.2)
    qc[idx_usa[0]] = 0.99
    rh = avalia(t, pop, idx_usb, idx_usa, modelo="despacho", q_usb=qc, q_usa=qc)
    assert rh["f_tempo"] > rd["f_tempo"] - 1.0 and 0 <= rh["f_gini"] <= 1
    print(f"ok  despacho q=0,3: tempo={rd['f_tempo']:.2f}  gini={rd['f_gini']:.3f}"
          f"  n_ef={rd['n_ef_usa']:.2f} (geometrica {n_ef_despacho(0.3):.2f})"
          f"  cob8={rd['cob_usa_8']:.0f}%")


if __name__ == "__main__":
    _teste()
