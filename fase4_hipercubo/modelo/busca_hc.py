"""Busca local da fase 3 (Teitz-Bart generalizado) com o hipercubo como avaliador.

Herda fase3_vidas.modelo.busca.Busca SEM altera-la. Triagem dos candidatos:
os ganhos esperados da ocupacao independente (rapidos, esparsos) propoem os
`n_cand` melhores destinos de cada unidade. Aceitacao: o objetivo, o CVaR10 e as
guardas sao reavaliados pelo hipercubo (hc_real.avalia), com a ocupacao endogena
de cada unidade. Objetivo, restricao K e guardas sao os da fase 3:

    J = vidas + lam * CVaR10;  cob_basico_usb e cob_grave >= valor de hoje (medido
    pelo mesmo avaliador);  unidades movidas <= K.

Limite honesto: a triagem nao enxerga a ocupacao endogena, entao um destino bom
so pelo alivio de uma area congestionada pode nao ser proposto. O hipercubo
decide a aceitacao, mas nao o espaco de busca.
"""
import numpy as np

from fase3_vidas.modelo import busca as BU

from . import hc_real as HR


class BuscaHC(BU.Busca):
    def __init__(self, *args, fator, atraso, s_min, taxas, variante="larson75", **kw):
        super().__init__(*args, **kw)
        self.hc = dict(fator=fator, atraso=atraso, s_min=s_min, taxas=taxas, variante=variante)
        self._cache = {}
        self.n_aval = 0

    def avalia_hc(self, yB, yA):
        chave = (np.asarray(yB, int).tobytes(), np.asarray(yA, int).tobytes())
        if chave not in self._cache:
            r = HR.avalia(yB, yA, self.hc["fator"], self.hc["atraso"], self.hc["s_min"],
                          self.hc["taxas"], variante=self.hc["variante"])
            self._cache[chave] = r
            self.n_aval += 1
        return self._cache[chave]

    def medidas(self, st):
        r = self.avalia_hc(st["y"]["B"], st["y"]["A"])
        return {"vidas": r["vidas"] / 1000.0, "cvar10": r["cvar10"] / 1000.0,
                "cob_basico": r["cob_basico_usb"] / 100.0, "cob_grave": r["cob_grave"] / 100.0}
