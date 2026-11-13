"""Busca global com o hipercubo como avaliador (fase 5, etapa 3).

Mesmo problema da fase 3/4:
    max J = vidas + lam * CVaR10
    s.a. cob_basico_usb e cob_grave >= as de hoje (mesmo avaliador)
         unidades movidas desde hoje <= K
         no maximo `cap` unidades por local

Diferencas para a busca da fase 4 (fase4 busca_hc.BuscaHC), cada uma atras de
uma opcao para poder medir o efeito isolado:

1. triagem="rho": os destinos testados vem da triagem com a ocupacao de CADA
   unidade (modelo/triagem.py), atualizada depois de cada troca aceita. A fase 4
   usava o q igual por tipo ("q").
2. Mascara de K na triagem: destinos que estourariam o limite de unidades
   movidas nao entram entre os candidatos. Na fase 4 eles eram propostos,
   gastavam avaliacoes e eram recusados depois.
3. Chutes que respeitam K (busca iterada, ILS): no limite, o chute so mexe em
   unidades JA deslocadas (nao aumenta as movidas). Na fase 4 todo chute a
   partir de uma solucao no limite passava de K e era descartado sem avaliar
   (h_refina: 0 de 10 chutes testados com K = 20 e 40).
4. Avaliador com desempate fixo (modelo/avaliador.py): o objetivo nao oscila
   por empate de tempos, e a busca nao aceita "melhoras" que sao so ruido.

Movidas, como na fase 3: soma sobre locais e tipos de max(x0 - y, 0).
Mover uma unidade do tipo T de j para j' muda as movidas em
    +1 se y_T[j] <= x0_T[j]  (abre ou aumenta um deficit em j)
    -1 se y_T[j'] < x0_T[j'] (devolve uma unidade a um local que perdeu)
"""
import hashlib

import numpy as np


CAMPOS = ("vidas", "cvar10", "cob_grave", "cob_basico_usb", "et_grave", "q_usb", "q_usa")


class BuscaGlobal:
    def __init__(self, av, tr, x0B, x0A, lam=0.0, K=None, base=None, n_cand=4,
                 triagem="rho", cap=10, viz=None):
        """av: Avaliador; tr: Triagem; base: medidas de hoje (guardas); viz: vizinhos por local."""
        self.av, self.tr = av, tr
        self.x0 = {"B": np.asarray(x0B, int), "A": np.asarray(x0A, int)}
        self.lam, self.K, self.base = lam, K, base
        self.n_cand, self.triagem, self.cap, self.viz = n_cand, triagem, cap, viz
        self.m = len(x0B)
        self._cache = {}
        self.n_aval = 0

    # ------------------------------------------------------------ medidas
    @staticmethod
    def _chave(y):
        return hashlib.blake2b(y["B"].tobytes() + y["A"].tobytes(), digest_size=16).digest()

    def mede(self, y):
        """(medidas escalares, rho por unidade) do mapa y, com cache."""
        k = self._chave(y)
        if k not in self._cache:
            r = self.av.avalia(y["B"], y["A"], detalhe=True)
            self._cache[k] = ({c: r[c] for c in CAMPOS}, r["rho"].astype(np.float64))
            self.n_aval += 1
        return self._cache[k]

    def J(self, md):
        return md["vidas"] + self.lam * md["cvar10"]

    def movidas(self, y):
        return int(sum(np.maximum(self.x0[t] - y[t], 0).sum() for t in ("B", "A")))

    def viavel(self, md, y):
        if self.K is not None and self.movidas(y) > self.K:
            return False
        if self.base is not None and (md["cob_basico_usb"] < self.base["cob_basico_usb"] - 1e-9 or
                                      md["cob_grave"] < self.base["cob_grave"] - 1e-9):
            return False
        return True

    # ------------------------------------------------------------ triagem
    def _estado(self, y, rho):
        if self.triagem == "q":
            return self.tr.estado(y["B"], y["A"])
        return self.tr.estado(y["B"], y["A"], rho)

    def _mascara_K(self, g, y, tipo, j):
        """-inf nos destinos que levariam as movidas acima de K."""
        if self.K is None:
            return g
        M = self.movidas(y)
        sai = 1 if y[tipo][j] <= self.x0[tipo][j] else 0
        entra = -(y[tipo] < self.x0[tipo]).astype(int)
        return np.where(M + sai + entra <= self.K, g, -np.inf)

    @staticmethod
    def _unidade(y, tipo, j):
        """Indice (USB primeiro) da primeira unidade do tipo no local j."""
        if tipo == "B":
            return int(y["B"][:j].sum())
        return int(y["B"].sum() + y["A"][:j].sum())

    # ------------------------------------------------------- busca local
    def busca_local(self, y0, rng, max_passos=30, log=None):
        """Teitz-Bart com triagem. Devolve (y, medidas, historico)."""
        y = {t: np.asarray(y0[t], int).copy() for t in ("B", "A")}
        md, rho = self.mede(y)
        st = self._estado(y, rho)
        hist = [dict(md, passo=0, movidas=self.movidas(y), avaliacoes=self.n_aval)]
        for passo in range(1, max_passos + 1):
            trocas = 0
            locais = [(t, int(j)) for t in ("B", "A") for j in np.nonzero(y[t])[0]]
            rng.shuffle(locais)
            for tipo, j in locais:
                if y[tipo][j] == 0:
                    continue
                peso = self.tr.peso(self.tr.S(st), self.lam)
                g = self.tr.ganhos(st, tipo, j, peso, unidade=self._unidade(y, tipo, j))
                g = self._mascara_K(g, y, tipo, j)
                cand = [int(c) for c in np.argsort(-g)[:self.n_cand] if np.isfinite(g[c])]
                melhor = None
                for jj in cand:
                    y[tipo][j] -= 1
                    y[tipo][jj] += 1
                    m2, r2 = self.mede(y)
                    if self.viavel(m2, y) and self.J(m2) > self.J(md) + 1e-9 and \
                            (melhor is None or self.J(m2) > self.J(melhor[1])):
                        melhor = (jj, m2, r2)
                    y[tipo][jj] -= 1
                    y[tipo][j] += 1
                if melhor is not None:
                    jj, md, rho = melhor
                    y[tipo][j] -= 1
                    y[tipo][jj] += 1
                    st = self._estado(y, rho)
                    trocas += 1
            hist.append(dict(md, passo=passo, movidas=self.movidas(y), trocas=trocas,
                             avaliacoes=self.n_aval))
            if log:
                log(f"    passo {passo}: J {self.J(md):.3f} vidas {md['vidas']:.3f} "
                    f"movidas {self.movidas(y)} trocas {trocas} aval {self.n_aval}")
            if trocas == 0:
                break
        return y, md, hist

    # ------------------------------------------------------------- chutes
    def chute(self, y, rng, tam):
        """Realoca `tam` unidades ao acaso (para um vizinho), sem passar de K.

        No limite de K so unidades ja deslocadas (y > x0 no local) se movem, e
        o destino nao pode abrir um deficit novo.
        """
        y = {t: y[t].copy() for t in ("B", "A")}
        for _ in range(tam):
            no_limite = self.K is not None and self.movidas(y) >= self.K
            opc = []
            for t in ("B", "A"):
                js = np.nonzero(y[t] > self.x0[t])[0] if no_limite else np.nonzero(y[t])[0]
                opc += [(t, int(j)) for j in js]
            if not opc:
                break
            t, j = opc[rng.integers(len(opc))]
            dest = np.asarray(self.viz[j] if self.viz is not None else np.arange(self.m))
            dest = dest[(dest != j) & ((y["B"][dest] + y["A"][dest]) < self.cap)]
            if self.K is not None:
                M = self.movidas(y)
                sai = 1 if y[t][j] <= self.x0[t][j] else 0
                entra = -(y[t][dest] < self.x0[t][dest]).astype(int)
                dest = dest[M + sai + entra <= self.K]
            if len(dest) == 0:
                continue
            y[t][j] -= 1
            y[t][int(dest[rng.integers(len(dest))])] += 1
        return y

    def ils(self, y0, semente=0, chutes=10, tam=3, max_passos=30, log=None):
        """Busca local iterada: otimo local, chute, nova busca local; fica com o melhor viavel."""
        rng = np.random.default_rng(semente)
        y, md, hist = self.busca_local(y0, rng, max_passos, log)
        melhor = (y, md) if self.viavel(md, y) else (None, None)
        registro = [{"chute": 0, "J": self.J(md), "viavel": self.viavel(md, y),
                     "avaliacoes": self.n_aval}]
        base_y = y
        for c in range(1, chutes + 1):
            yc = self.chute(base_y if melhor[0] is None else melhor[0], rng, tam)
            y2, md2, _ = self.busca_local(yc, rng, max_passos, log)
            ok = self.viavel(md2, y2)
            registro.append({"chute": c, "J": self.J(md2), "viavel": ok,
                             "avaliacoes": self.n_aval})
            if log:
                log(f"  chute {c}: J {self.J(md2):.3f} viavel {ok} "
                    f"(melhor {self.J(melhor[1]) if melhor[1] else float('nan'):.3f})")
            if ok and (melhor[1] is None or self.J(md2) > self.J(melhor[1]) + 1e-9):
                melhor = (y2, md2)
        return melhor[0], melhor[1], registro


# --------------------------------------------------------------------- teste
def _teste():
    """Contas de movidas e mascara de K num caso pequeno (sem hipercubo)."""
    class _Tr:
        pass
    x0B = np.array([2, 1, 0, 0, 0])
    x0A = np.array([0, 0, 1, 0, 0])
    b = BuscaGlobal(None, _Tr(), x0B, x0A, K=1)
    y = {"B": x0B.copy(), "A": x0A.copy()}
    assert b.movidas(y) == 0
    g = np.zeros(5)
    # tirar USB de 0 (original) para 3: movidas 1 <= K
    assert np.isfinite(b._mascara_K(g, y, "B", 0)[3])
    y["B"][0] -= 1
    y["B"][3] += 1
    assert b.movidas(y) == 1
    # no limite: tirar outra original (local 1) para 4 estoura; devolver ao 0 nao
    gm = b._mascara_K(g, y, "B", 1)
    assert not np.isfinite(gm[4]) and np.isfinite(gm[0])
    # a unidade deslocada (local 3) pode ir a qualquer lugar sem mudar as movidas
    assert np.all(np.isfinite(b._mascara_K(g, y, "B", 3)))
    # chute no limite so move unidade deslocada e nunca passa de K
    rng = np.random.default_rng(0)
    for _ in range(200):
        y2 = b.chute(y, rng, 3)
        assert b.movidas(y2) <= 1 and y2["B"].sum() == 3 and y2["A"].sum() == 1
    assert b._unidade({"B": np.array([2, 1, 0]), "A": np.array([0, 1, 1])}, "A", 2) == 4
    print("busca_global: movidas, mascara de K, chutes e indices ok")


if __name__ == "__main__":
    _teste()
