"""Baseline classico: p-median sobre a regra da unidade mais proxima.

E o que o prototipo atual do projeto faz — toda ambulancia e equivalente e todo
setor e atendido pela mais proxima. Serve para responder a pergunta que o
artigo precisa responder: se voce PLANEJA com a hipotese classica mas a demanda
se comporta segundo Huff, quanto voce perde?

Guloso aditivo + substituicao de vertices (Teitz-Bart). Sem solver: o guloso
vetorizado gasta ~30 ms por iteracao porque avalia os 1107 candidatos de uma
vez contra a matriz inteira.
"""
import numpy as np


def custo_pmedian(T, pop, sel):
    """Tempo medio ponderado ate a unidade mais proxima."""
    return float((T[sel].min(axis=0) * pop).sum() / pop.sum())


def guloso(T, pop, p, verbose=False):
    """Escolhe p locais somando um de cada vez o que mais reduz o custo."""
    n = T.shape[1]
    melhor = np.full(n, np.inf, dtype=np.float32)
    sel = []
    for k in range(p):
        # custo resultante de acrescentar cada candidato, todos de uma vez
        cand = np.minimum(T, melhor[None, :]).dot(pop.astype(np.float32))
        cand[sel] = np.inf
        j = int(np.argmin(cand))
        sel.append(j)
        melhor = np.minimum(melhor, T[j])
        if verbose and (k + 1) % 20 == 0:
            print(f"    guloso {k+1}/{p}: {custo_pmedian(T, pop, sel):.3f} min",
                  flush=True)
    return np.array(sel)


def troca_vertices(T, pop, sel, n_passes=3, verbose=False):
    """Teitz-Bart: tenta trocar cada local selecionado por um de fora."""
    sel = list(map(int, sel))
    n_cand = T.shape[0]
    atual = custo_pmedian(T, pop, sel)
    popf = pop.astype(np.float32)
    for passo in range(n_passes):
        mudou = False
        for pos in range(len(sel)):
            resto = sel[:pos] + sel[pos + 1:]
            base = T[resto].min(axis=0)
            # custo de cada candidato ocupando a vaga, vetorizado
            cand = np.minimum(T, base[None, :]).dot(popf) / popf.sum()
            cand[resto] = np.inf
            j = int(np.argmin(cand))
            if cand[j] < atual - 1e-9:
                sel[pos], atual, mudou = j, float(cand[j]), True
        if verbose:
            print(f"    troca passo {passo+1}: {atual:.4f} min", flush=True)
        if not mudou:
            break
    return np.array(sel), atual


def resolve(T, pop, p, n_passes=3, verbose=False):
    sel = guloso(T, pop, p, verbose)
    return troca_vertices(T, pop, sel, n_passes, verbose)


def _teste():
    rng = np.random.default_rng(0)
    m, n = 60, 400
    ps, dm = rng.random((m, 2)) * 20, rng.random((n, 2)) * 20
    T = np.sqrt(((ps[:, None, :] - dm[None, :, :]) ** 2).sum(-1)).astype(np.float32)
    pop = rng.integers(100, 2000, n).astype(float)

    sel_g = guloso(T, pop, 5)
    c_g = custo_pmedian(T, pop, sel_g)
    sel_t, c_t = troca_vertices(T, pop, sel_g)
    assert c_t <= c_g + 1e-9, "troca de vertices piorou o custo"
    assert len(set(map(int, sel_t))) == 5, "locais repetidos no p-median"

    # contra a otimizacao exata por forca bruta (p pequeno)
    from itertools import combinations
    otimo = min(custo_pmedian(T, pop, list(c)) for c in combinations(range(m), 3))
    _, c3 = resolve(T, pop, 3)
    assert c3 >= otimo - 1e-6
    print(f"ok  p-median: guloso {c_g:.3f} -> troca {c_t:.3f} min | "
          f"p=3 heuristica {c3:.4f} x otimo exato {otimo:.4f} "
          f"({100*(c3/otimo-1):+.2f}%)")


if __name__ == "__main__":
    _teste()
