"""Custo de realocacao: quanto a frota precisa se deslocar para sair da
configuracao atual e chegar na proposta.

Nao basta contar quantas unidades mudaram de lugar: mover uma ambulancia para
uma base a 2 km e muito mais barato que manda-la para o outro extremo da
cidade. Como as unidades da mesma modalidade sao intercambiaveis, o custo e o
de um emparelhamento de custo minimo entre as posicoes de origem e as de
destino.

Usamos o emparelhamento OTIMO (Hungaro, via scipy). A suspeita inicial era de
que O(p^3) fosse caro demais para rodar dentro do NSGA-II, mas medindo: 0,27 ms
contra 0,67 ms de um guloso em laco Python — a implementacao em C ganha com
folga no tamanho deste problema (100x100). O guloso fica so como alternativa
caso scipy falte; ele custa em media 9% a mais que o otimo, sempre por cima.

Em ambos os casos as unidades que ficam onde estao sao canceladas antes, o que
reduz a matriz e garante custo zero para a configuracao atual.
"""
from collections import Counter

import numpy as np

RAIO_KM = 6371.0


def matriz_km(lat, lon):
    """(m, m) distancias em km entre todos os candidatos (haversine)."""
    la, lo = np.radians(np.asarray(lat)), np.radians(np.asarray(lon))
    a = (np.sin((la[:, None] - la[None, :]) / 2) ** 2
         + np.cos(la)[:, None] * np.cos(la)[None, :]
         * np.sin((lo[:, None] - lo[None, :]) / 2) ** 2)
    return (RAIO_KM * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))).astype(np.float32)


def _guloso(orig, novo, D):
    """Emparelhamento guloso entre dois multiconjuntos de locais."""
    co, cn = Counter(map(int, orig)), Counter(map(int, novo))
    fica = co & cn                       # quem nao precisa sair
    o = np.array(list((co - fica).elements()), dtype=np.int64)
    n = np.array(list((cn - fica).elements()), dtype=np.int64)
    if len(o) == 0:
        return 0.0
    C = D[np.ix_(o, n)].astype(np.float64).copy()
    total = 0.0
    for _ in range(len(o)):
        k = int(np.argmin(C))
        i, j = divmod(k, C.shape[1])
        total += C[i, j]
        C[i, :] = np.inf
        C[:, j] = np.inf
    return float(total)


try:
    from scipy.optimize import linear_sum_assignment as _lsa
except ImportError:                      # pragma: no cover
    _lsa = None


def _par(orig, novo, D):
    """Custo minimo de emparelhar dois multiconjuntos de locais."""
    co, cn = Counter(map(int, orig)), Counter(map(int, novo))
    fica = co & cn                       # quem nao precisa sair: custo zero
    o = np.array(list((co - fica).elements()), dtype=np.int64)
    n = np.array(list((cn - fica).elements()), dtype=np.int64)
    if len(o) == 0:
        return 0.0
    if _lsa is None:
        return _guloso(orig, novo, D)
    C = D[np.ix_(o, n)].astype(np.float64)
    i, j = _lsa(C)
    return float(C[i, j].sum())


def custo(x, x0, D, n_usb):
    """Quilometros totais de deslocamento, somando USB e USA separadamente."""
    x, x0 = np.asarray(x), np.asarray(x0)
    return (_par(x0[:n_usb], x[:n_usb], D)
            + _par(x0[n_usb:], x[n_usb:], D))


def movidas(x, x0, n_usb):
    """Quantas unidades trocam de local (comparando multiconjuntos)."""
    x, x0 = np.asarray(x), np.asarray(x0)
    n = 0
    for a, b in ((x0[:n_usb], x[:n_usb]), (x0[n_usb:], x[n_usb:])):
        ca, cb = Counter(map(int, a)), Counter(map(int, b))
        n += sum((ca - (ca & cb)).values())
    return n


# ------------------------------------------------------------------- sanidade
def _otimo(orig, novo, D):
    """Emparelhamento exato, para conferir o guloso no teste."""
    from scipy.optimize import linear_sum_assignment
    o, n = np.asarray(orig, dtype=int), np.asarray(novo, dtype=int)
    C = D[np.ix_(o, n)].astype(np.float64)
    i, j = linear_sum_assignment(C)
    return float(C[i, j].sum())


def _otimo_multi(orig, novo, D):
    """Otimo depois de cancelar os que ficam no lugar (para o teste)."""
    co, cn = Counter(map(int, orig)), Counter(map(int, novo))
    fica = co & cn
    o = np.array(list((co - fica).elements()), dtype=int)
    n = np.array(list((cn - fica).elements()), dtype=int)
    return _otimo(o, n, D) if len(o) else 0.0


def _teste():
    rng = np.random.default_rng(0)
    m = 30
    lat = -23.6 + rng.random(m) * 0.4
    lon = -46.7 + rng.random(m) * 0.4
    D = matriz_km(lat, lon)
    assert np.allclose(np.diag(D), 0) and np.allclose(D, D.T), "matriz nao e metrica"

    x0 = rng.integers(0, m, 12)
    assert custo(x0, x0, D, 8) == 0.0, "configuracao identica tem de custar zero"
    assert movidas(x0, x0, 8) == 0
    perm = np.concatenate([rng.permutation(x0[:8]), rng.permutation(x0[8:])])
    assert custo(perm, x0, D, 8) == 0.0, "permutar as mesmas bases custa zero"

    # uma unica unidade trocada: o custo e exatamente a distancia entre as bases
    y = x0.copy()
    y[0] = (x0[0] + 7) % m
    assert np.isclose(custo(y, x0, D, 8), D[x0[0], y[0]]), custo(y, x0, D, 8)
    assert movidas(y, x0, 8) == 1

    # o guloso (fallback) nunca fica abaixo do otimo; mede-se a folga
    for p in (6, 20, 107):
        folga = []
        for _ in range(200 if p < 50 else 40):
            a, b = rng.integers(0, m, p), rng.integers(0, m, p)
            co, cn = Counter(map(int, a)), Counter(map(int, b))
            fica = co & cn
            ro = np.array(list((co - fica).elements()), dtype=int)
            rn = np.array(list((cn - fica).elements()), dtype=int)
            if len(ro) == 0:
                continue
            g, ot = _guloso(a, b, D), _otimo(ro, rn, D)
            assert g >= ot - 1e-6, "guloso abaixo do otimo, impossivel"
            folga.append(g / ot if ot > 0 else 1.0)
        folga = np.array(folga)
        print(f"  p={p:3d}: guloso/otimo mediana {np.median(folga):.3f}x  "
              f"media {folga.mean():.3f}x  pior {folga.max():.3f}x  "
              f"exato em {100*(folga < 1.0001).mean():.0f}%")
    # custo() usa o Hungaro: tem de bater com o otimo, nao com o guloso
    a, b = rng.integers(0, m, 12), rng.integers(0, m, 12)
    x = np.concatenate([b[:8], b[8:]])
    esperado = (_otimo_multi(a[:8], x[:8], D) + _otimo_multi(a[8:], x[8:], D))
    assert np.isclose(custo(x, a, D, 8), esperado), (custo(x, a, D, 8), esperado)
    print("ok  custo() usa o emparelhamento otimo; guloso so como reserva")


if __name__ == "__main__":
    _teste()
