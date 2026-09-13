"""NSGA-II para realocar a frota de SP: tempo esperado x equidade.

Sem dependencia nova: o projeto ja evita scipy/shapely, e um NSGA-II com
codificacao inteira cabe em ~150 linhas. `t` vem com os candidatos nas linhas
(ver huff2sfca). A codificacao e um vetor de tamanho
p = n_usb + n_usa em que cada gene guarda o indice do candidato que hospeda
aquela unidade; repeticao e permitida (varias ambulancias na mesma base).
"""
import time
from pathlib import Path

import numpy as np

import mudanca
from huff2sfca import ALFA, BETA, D0, THETA, avalia, prepara


# ------------------------------------------------------------------ dominancia
def fronteiras(F):
    """Fast non-dominated sort. F: (n, 2) objetivos a MINIMIZAR."""
    n = len(F)
    domina = [[] for _ in range(n)]
    contador = np.zeros(n, dtype=int)
    for i in range(n):
        me, ou = F[i], F
        pior = np.all(ou >= me, axis=1) & np.any(ou > me, axis=1)
        melhor = np.all(ou <= me, axis=1) & np.any(ou < me, axis=1)
        domina[i] = np.nonzero(pior)[0].tolist()
        contador[i] = melhor.sum()
    fr, atual = [], np.nonzero(contador == 0)[0].tolist()
    while atual:
        fr.append(atual)
        prox = []
        for i in atual:
            for j in domina[i]:
                contador[j] -= 1
                if contador[j] == 0:
                    prox.append(j)
        atual = prox
    return fr


def aglomeracao(F):
    """Crowding distance dentro de uma fronteira."""
    n = len(F)
    d = np.zeros(n)
    if n <= 2:
        return np.full(n, np.inf)
    for k in range(F.shape[1]):
        o = np.argsort(F[:, k])
        d[o[0]] = d[o[-1]] = np.inf
        faixa = F[o[-1], k] - F[o[0], k]
        if faixa > 0:
            d[o[1:-1]] += (F[o[2:], k] - F[o[:-2], k]) / faixa
    return d


def joelho(F):
    """Indice do ponto da frente mais proximo do ideal, em escala normalizada.

    Uma definicao so, usada pelo experimento e pelas figuras: ja houve
    divergencia entre as duas, e o mapa saiu com 16 setas para uma solucao que
    o resumo dizia ter 12 realocacoes.
    """
    F = np.asarray(F, dtype=float)
    amp = np.ptp(F, axis=0)
    z = (F - F.min(axis=0)) / np.where(amp > 0, amp, 1.0)
    return int(np.argmin((z ** 2).sum(axis=1)))


# ------------------------------------------------------------------- operadores
class Problema:
    def __init__(self, t, pop, n_usb, n_usa, cand_validos=None, viz=None,
                 cap_max=None, x0=None, d_km=None, lam=0.0, **kw):
        self.t, self.pop = t, pop
        self.n_usb, self.n_usa = n_usb, n_usa
        self.m = t.shape[0]
        self.validos = (np.arange(self.m) if cand_validos is None
                        else np.asarray(cand_validos))
        self.viz = viz              # (m, k) candidatos vizinhos, para mutacao local
        self.cap_max = cap_max
        self.kw = dict(alfa=kw.get("alfa", ALFA), beta=kw.get("beta", BETA),
                       d0=kw.get("d0", D0), theta=kw.get("theta", THETA))
        # decaimento calculado uma vez so; e o que torna o laco viavel
        self.f = prepara(t, self.kw["beta"], self.kw["d0"])
        # custo de mudanca: lam minutos por km medio deslocado por unidade
        self.x0 = None if x0 is None else np.asarray(x0)
        self.d_km, self.lam = d_km, float(lam)
        self._cache = {}

    def custo_km(self, x):
        """Quilometros totais que a frota percorre para sair da configuracao
        atual e chegar em x (emparelhamento otimo por modalidade)."""
        if self.x0 is None or self.d_km is None:
            return 0.0
        return mudanca.custo(x, self.x0, self.d_km, self.n_usb)

    def objetivos(self, x):
        ch = x.tobytes()
        if ch in self._cache:
            return self._cache[ch]
        r = avalia(self.t, self.pop, x[:self.n_usb], x[self.n_usb:],
                   f=self.f, **self.kw)
        # objetivo 1 = tempo de resposta + preco da mudanca, na mesma unidade
        pen = (self.lam * self.custo_km(x) / (self.n_usb + self.n_usa)
               if self.lam else 0.0)
        v = np.array([r["f_tempo"] + pen, r["f_gini"]])
        self._cache[ch] = v
        return v

    def viavel(self, x):
        if self.cap_max is None:
            return True
        return np.bincount(x, minlength=self.m).max() <= self.cap_max

    def repara(self, x, rng):
        if self.cap_max is None:
            return x
        for _ in range(200):
            c = np.bincount(x, minlength=self.m)
            if c.max() <= self.cap_max:
                break
            j = np.argmax(c)
            g = rng.choice(np.nonzero(x == j)[0])
            x[g] = rng.choice(self.validos)
        return x


def _muta(x, pr, prob, rng):
    x = x.copy()
    alvo = rng.random(len(x)) < pr
    for g in np.nonzero(alvo)[0]:
        if prob.viz is not None and rng.random() < 0.7:
            x[g] = rng.choice(prob.viz[x[g]])      # move para um local vizinho
        else:
            x[g] = rng.choice(prob.validos)        # salto longo
    return prob.repara(x, rng)


def _cruza(a, b, rng):
    mask = rng.random(len(a)) < 0.5
    return np.where(mask, a, b), np.where(mask, b, a)


def _torneio(F, rank, crowd, rng, k=2):
    i, j = rng.integers(0, len(F), 2)
    if rank[i] != rank[j]:
        return i if rank[i] < rank[j] else j
    return i if crowd[i] > crowd[j] else j


# ------------------------------------------------------------------------ loop
def nsga2(prob, n_pop=80, n_ger=120, pr_mut=None, semente=None, x0=None,
          verbose=True, checkpoint=None, salvar_cada=10, orcamento=None):
    """Devolve (X_frente, F_frente, completo).

    `checkpoint` e um .npz com a populacao inteira: a rodada retoma de onde
    parou. `orcamento` e um teto de segundos — ao estourar, salva e devolve
    completo=False, para o chamador invocar de novo. Necessario porque cada
    chamada do shell remoto tem um limite de tempo proprio.
    """
    t_ini = time.time()
    rng = np.random.default_rng(semente)
    p = prob.n_usb + prob.n_usa
    pr_mut = pr_mut if pr_mut is not None else 2.0 / p
    ger0, X, F = 0, None, None

    if checkpoint is not None and Path(checkpoint).exists():
        d = np.load(checkpoint)
        if d["X"].shape == (n_pop, p):
            X, F, ger0 = d["X"], d["F"], int(d["ger"])
            rng = np.random.default_rng((semente or 0) + ger0)
            if verbose:
                print(f"  retomando da geracao {ger0}", flush=True)
    if X is None:
        X = rng.choice(prob.validos, size=(n_pop, p))
        # x0 pode ser uma solucao ou varias (configuracao atual, p-median...).
        # Semear com boas solucoes conhecidas importa: sem o p-median na
        # populacao inicial, o NSGA-II ficava atras dele no eixo do tempo.
        if x0 is not None:
            sementes = np.atleast_2d(np.asarray(x0))
            k = 0
            for s in sementes:
                X[k] = s
                k += 1
                for _ in range(3):          # perturbacoes de cada semente
                    if k < n_pop:
                        X[k] = _muta(np.asarray(s), 0.15, prob, rng)
                        k += 1
        X = np.array([prob.repara(x, rng) for x in X])
        F = np.array([prob.objetivos(x) for x in X])

    def salva(ger):
        if checkpoint is not None:
            np.savez(checkpoint, X=X, F=F, ger=ger)

    for ger in range(ger0, n_ger):
        fr = fronteiras(F)
        rank = np.empty(len(X), dtype=int)
        crowd = np.empty(len(X))
        for r, f in enumerate(fr):
            rank[f] = r
            crowd[f] = aglomeracao(F[f])

        filhos = []
        while len(filhos) < n_pop:
            a = X[_torneio(F, rank, crowd, rng)]
            b = X[_torneio(F, rank, crowd, rng)]
            c1, c2 = _cruza(a, b, rng)
            filhos += [_muta(c1, pr_mut, prob, rng),
                       _muta(c2, pr_mut, prob, rng)]
        Y = np.array(filhos[:n_pop])
        G = np.array([prob.objetivos(y) for y in Y])

        # sobrevivencia elitista (mu + lambda)
        XT, FT = np.vstack([X, Y]), np.vstack([F, G])
        fr = fronteiras(FT)
        sel = []
        for f in fr:
            if len(sel) + len(f) <= n_pop:
                sel += f
            else:
                d = aglomeracao(FT[f])
                sel += [f[i] for i in np.argsort(-d)[: n_pop - len(sel)]]
                break
        X, F = XT[sel], FT[sel]

        if verbose and (ger % 10 == 0 or ger == n_ger - 1):
            print(f"  ger {ger:3d}  tempo {F[:,0].min():6.2f} min   "
                  f"gini {F[:,1].min():.4f}   frentes {len(fronteiras(F))}",
                  flush=True)
        if (ger + 1) % salvar_cada == 0:
            salva(ger + 1)
        if orcamento is not None and time.time() - t_ini > orcamento:
            salva(ger + 1)
            if verbose:
                print(f"  orcamento de {orcamento}s esgotado na geracao "
                      f"{ger+1}/{n_ger}; rode de novo para continuar", flush=True)
            fr = fronteiras(F)[0]
            o = np.argsort(F[fr, 0])
            return X[np.array(fr)[o]], F[np.array(fr)[o]], False

    salva(n_ger)
    fr0 = fronteiras(F)[0]
    o = np.argsort(F[fr0, 0])
    return X[np.array(fr0)[o]], F[np.array(fr0)[o]], True


# ---------------------------------------------------------------- busca local
def busca_local(prob, x, n_iter=300, peso=0.5, semente=None, verbose=False):
    """Swap 1-opt escalarizado; serve de baseline e de refino do NSGA-II."""
    rng = np.random.default_rng(semente)
    f = prob.objetivos(x)
    esc = lambda v: peso * v[0] / 10.0 + (1 - peso) * v[1]
    melhor, fm = x.copy(), f
    for it in range(n_iter):
        y = melhor.copy()
        g = rng.integers(0, len(y))
        y[g] = (rng.choice(prob.viz[y[g]]) if prob.viz is not None
                else rng.choice(prob.validos))
        y = prob.repara(y, rng)
        fy = prob.objetivos(y)
        if esc(fy) < esc(fm):
            melhor, fm = y, fy
            if verbose:
                print(f"   it {it:4d}  tempo {fm[0]:.2f}  gini {fm[1]:.4f}")
    return melhor, fm


# ------------------------------------------------------------------- sanidade
def _teste():
    rng = np.random.default_rng(1)
    n, m = 400, 60
    dm, ps = rng.random((n, 2)) * 30, rng.random((m, 2)) * 30
    t = np.sqrt(((ps[:, None, :] - dm[None, :, :]) ** 2).sum(-1)).astype(np.float32)
    pop = rng.integers(200, 3000, n).astype(float)
    dcc = np.sqrt(((ps[:, None, :] - ps[None, :, :]) ** 2).sum(-1))
    viz = np.argsort(dcc, axis=1)[:, 1:9]

    prob = Problema(t, pop, n_usb=24, n_usa=6, viz=viz, cap_max=4)
    x0 = rng.choice(m, 30)
    f0 = prob.objetivos(x0)
    X, F, ok = nsga2(prob, n_pop=40, n_ger=40, semente=0, x0=x0, verbose=False)
    assert ok

    assert len(X) >= 1 and F.shape[1] == 2
    assert np.all(np.diff(F[:, 0]) >= -1e-9), "frente nao ordenada por tempo"
    assert np.all(np.diff(F[:, 1]) <= 1e-9), "frente deveria trocar tempo por gini"
    assert F[:, 0].min() < f0[0], "NSGA-II nao melhorou o tempo do ponto inicial"
    print(f"ok  inicial tempo={f0[0]:.2f} gini={f0[1]:.3f} | "
          f"frente: {len(F)} pontos, tempo {F[:,0].min():.2f}-{F[:,0].max():.2f}, "
          f"gini {F[:,1].min():.3f}-{F[:,1].max():.3f}")


if __name__ == "__main__":
    _teste()
