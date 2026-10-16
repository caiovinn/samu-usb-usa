"""Vidas salvas: sobrevida a parada cardiorrespiratoria (PCR) como medida.

A PCR e a condicao "tracadora" da fase 3. E a unica urgencia em que a relacao
entre minutos e mortes esta bem medida, e as duas modalidades desfibrilam
(USB com DEA, USA com medico). Por isso ela NAO e uma terceira classe de
despacho: nao sabemos quantos chamados sao PCR (o SIA do SAMU-SP e
consolidado, sem CID), e esses chamados ja estao dentro dos volumes
observados. A carga das unidades (ocupacao q) vem so das duas classes
observadas; a PCR e avaliada por cima do mapa de bases:

    um setor com PCR recebe a USB livre mais proxima E a USA livre mais
    proxima (18% dos envios do SAMU-SP usam multiplos meios); quem chegar
    primeiro desfibrila. O primeiro a chegar e, entao, a unidade livre mais
    proxima de QUALQUER tipo — o pool combinado de huff2sfca.despacho.

Curva de sobrevida (De Maio, Stiell, Wells & Spaite 2003, Ann Emerg Med
42(2):242-250, doi:10.1067/mem.2003.266; OPALS, Ontario, 9.273 PCR), usada
por Erkut, Ingolfsson & Erdogan 2008 (doi:10.1002/nav.20267):

    s(t) = 1 / (1 + exp(-(B0 + B1 t))),  B0 = -0,679, B1 = -0,262 por minuto

com t = minutos da chamada ate o desfibrilador. Confere com o artigo: 12,0% em
5 min, 4,6% em 9 min.

Tempo de resposta calibrado (a matriz do OSM e em fluxo livre e sem a
regulacao): t' = ATRASO + fator * t. ATRASO = 3 min e o tempo ate a saida nos
casos prioritarios e ALVO_GRAVE = 20 min a chegada media nos casos mais
graves, ambos da Prefeitura de SP (noticia de 21/12/2023). O fator e o unico
numero que faz a rede de hoje reproduzir esses 20 min (calibra_fator).
"""
import numpy as np

from fase2_sao_paulo.modelo import huff2sfca as H

B0, B1 = -0.679, -0.262          # De Maio et al. 2003
ATRASO = 3.0                     # min; regulacao + saida (Prefeitura, dez/2023)
ALVO_GRAVE = 20.0                # min; chegada media, casos mais graves (idem)
TAU_GUARDA = 15.0                # min de resposta; guardas de cobertura USB/USA
ALFA_CVAR = 0.10                 # os 10% da populacao com menor sobrevida
# limites das faixas (min de resposta) da aproximacao em degraus da curva,
# usada pela busca e pelo MILP; a avaliacao final usa a curva continua.
# A primeira faixa comeca no ATRASO: nenhuma resposta e mais rapida que ele, e
# comecar em 0 dava s(2) = 24% a chegadas em 3-4 min (s real ~18%).
BANDAS = tuple(np.arange(3.5, 14.01, 0.5)) + (15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, 25.0)
INICIO = ATRASO


def s(t):
    """Probabilidade de sobreviver a uma PCR com desfibrilacao em t minutos."""
    t = np.asarray(t, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-(B0 + B1 * t)))


def resposta(t, fator=1.0, atraso=0.0):
    """Tempo de resposta calibrado; par inalcancavel continua inalcancavel."""
    t = np.asarray(t)
    return np.where(t >= H.T_INALC, H.T_INALC,
                    atraso + fator * t).astype(np.float32)


def bruto(tau, fator=1.0, atraso=0.0):
    """Limite na matriz bruta equivalente a tau minutos de resposta."""
    return (np.asarray(tau, dtype=np.float64) - atraso) / fator


def calibra_fator(et_f0, et_f1, alvo=ALVO_GRAVE):
    """Fator que leva o tempo esperado do chamado grave da rede de hoje ao alvo.

    et_f0, et_f1: tempo esperado calibrado com fator 0 e 1 (mesmo atraso). O
    fator nao muda a ordem das unidades, logo nem as probabilidades de
    despacho, e E[t'] e linear nele: E(f) = et_f0 + f (et_f1 - et_f0). Os
    setores sem unidade alcancavel ficam em T_INALC nos dois casos e entram so
    na constante — dividir alvo - atraso por E[t] bruto erraria por isso.
    """
    return (alvo - et_f0) / (et_f1 - et_f0)


def degraus(bandas=BANDAS, inicio=INICIO):
    """Aproximacao em degraus: s~(t) = soma_b d_b 1[t <= tau_b].

    Em cada faixa (tau_{b-1}, tau_b] o degrau vale s no ponto medio da faixa
    (a primeira comeca em `inicio`, o menor tempo de resposta possivel);
    depois da ultima faixa, 0. Devolve (tau, d), com d_b = v_b - v_{b+1} > 0.
    """
    tau = np.asarray(bandas, dtype=np.float64)
    ini = np.concatenate(([inicio], tau[:-1]))
    v = s(0.5 * (ini + tau))
    d = v - np.concatenate((v[1:], [0.0]))
    return tau, d


def cvar_inferior(x, w, alfa=ALFA_CVAR):
    """Media de x nos alfa da populacao com os MENORES x (CVaR inferior).

    Diferente de huff2sfca.media_pior_decil, o setor que cruza o limite entra
    so com a fracao que cabe: e exatamente o que a linearizacao de
    Rockafellar-Uryasev do MILP calcula.
    """
    o = np.argsort(x)
    x = np.asarray(x, dtype=np.float64)[o]
    w = np.asarray(w, dtype=np.float64)[o] / np.sum(w)
    cw = np.cumsum(w)
    peso = np.clip(alfa - (cw - w), 0.0, w)
    return float(np.sum(peso * x) / alfa)


def avalia_vidas(t, pop, idx_usb, idx_usa, q_usb, q_usa, fator=1.0,
                 atraso=0.0, tau_guarda=TAU_GUARDA, k_desp=H.K_DESP,
                 detalhe=False):
    """Avalia um mapa de bases pela sobrevida a PCR e pelas guardas.

    t: (candidatos, setores) tempos BRUTOS do OSM. Devolve, por 1.000 PCR:
      vidas       sobreviventes esperados na cidade
      cvar10      sobreviventes esperados por 1.000 PCR nos 10% piores
    e as guardas (cobertura em tau_guarda min, em %): cob_grave (USA livre mais
    proxima, chamado grave) e cob_basico (USB livre mais proxima); tempos
    esperados calibrados et_grave e et_basico.
    """
    idx_usb = np.asarray(idx_usb, dtype=np.int64)
    idx_usa = np.asarray(idx_usa, dtype=np.int64)
    w = pop / pop.sum()

    # PCR: primeiro desfibrilador = unidade livre mais proxima de qualquer tipo
    todos = np.concatenate([idx_usb, idx_usa])
    loc, inv = np.unique(todos, return_inverse=True)
    q_un = np.concatenate([H._q_unidades(q_usb, idx_usb), H._q_unidades(q_usa, idx_usa)])
    tl = t[loc]
    P = H.despacho(tl, H._log_ocup(loc, inv, q_un), k_desp)
    S = np.einsum("ji,ji->i", P, s(resposta(tl, fator, atraso)).astype(np.float32))

    # guardas: as duas classes observadas de despacho
    out = {"vidas": float(1000 * np.sum(w * S)),
           "cvar10": float(1000 * cvar_inferior(S, pop))}
    for nome, idx, q in (("grave", idx_usa, q_usa), ("basico", idx_usb, q_usb)):
        lc, iv = np.unique(idx, return_inverse=True)
        tr = resposta(t[lc], fator, atraso)
        Pc = H.despacho(t[lc], H._log_ocup(lc, iv, H._q_unidades(q, idx)), k_desp)
        out[f"cob_{nome}"] = float(100 * np.sum(w * H.cobertura(tr, Pc, tau_guarda)))
        out[f"et_{nome}"] = float(np.sum(w * H.tempo_esperado(tr, Pc)))
    if detalhe:
        out["S"] = S
    return out


# ------------------------------------------------------------------- sanidade
def _teste():
    # a curva confere com o artigo
    assert abs(s(5) - 0.120) < 1e-3 and abs(s(9) - 0.046) < 1e-3, (s(5), s(9))
    assert np.all(np.diff(s(np.arange(0, 30))) < 0), "s(t) tem de cair com t"

    # degraus: soma_b d_b 1[t<=tau_b] = s no meio da faixa de t
    tau, d = degraus()
    for tt in (3.2, 4.6, 9.7, 24.9, 30.0):
        b = np.searchsorted(tau, tt)
        esp = 0.0 if b == len(tau) else s(0.5 * ((tau[b - 1] if b else INICIO) + tau[b]))
        assert abs(np.sum(d * (tt <= tau)) - esp) < 1e-12
    assert np.all(d > 0)

    # CVaR: igual populacao, x = 0..99 -> media dos 10 menores = 4,5
    x = np.arange(100.0)
    assert abs(cvar_inferior(x, np.ones(100)) - 4.5) < 1e-12
    # setor que cruza o limite entra so pela fracao
    assert abs(cvar_inferior(np.array([1.0, 3.0]), np.array([0.05, 0.95])) -
               (0.05 * 1 + 0.05 * 3) / 0.10) < 1e-12

    # calibracao: E[atraso + f t] bate o alvo exatamente
    rng = np.random.default_rng(0)
    m, n = 30, 400
    ps, dm = rng.random((m, 2)) * 20, rng.random((n, 2)) * 20
    t = np.sqrt(((ps[:, None, :] - dm[None, :, :]) ** 2).sum(-1)).astype(np.float32)
    pop = rng.integers(100, 2000, n).astype(float)
    usb, usa = rng.choice(m, 12), rng.choice(m, 3)
    r1 = avalia_vidas(t, pop, usb, usa, 0.3, 0.2)
    t[:, :3] = H.T_INALC                       # setores sem unidade alcancavel
    e0, e1 = (avalia_vidas(t, pop, usb, usa, 0.3, 0.2, fator=ff, atraso=ATRASO)["et_grave"]
              for ff in (0.0, 1.0))
    f = calibra_fator(e0, e1)
    r2 = avalia_vidas(t, pop, usb, usa, 0.3, 0.2, fator=f, atraso=ATRASO)
    assert abs(r2["et_grave"] - ALVO_GRAVE) < 1e-3, r2["et_grave"]
    # tempo maior -> menos vidas
    assert r2["vidas"] < r1["vidas"] and r2["cvar10"] <= r2["vidas"]

    # PCR = pool combinado: com q = 0, sobrevida = s(tempo ate a unidade mais
    # proxima de qualquer tipo)
    r0 = avalia_vidas(t, pop, usb, usa, 0.0, 0.0, detalhe=True)
    mais_prox = t[np.concatenate([usb, usa])].min(axis=0)
    assert np.allclose(r0["S"], s(mais_prox), atol=1e-6)

    # degraus = cobertura do despacho: soma_b d_b P(T <= tau_b) com P de
    # despacho() e, com k = todos os locais, 1 - prod q^n(tau) por setor
    loc, inv = np.unique(np.concatenate([usb, usa]), return_inverse=True)
    q_un = np.concatenate([np.full(len(usb), 0.3), np.full(len(usa), 0.2)])
    P = H.despacho(t[loc], H._log_ocup(loc, inv, q_un), k=len(loc))
    viaP = sum(dd * H.cobertura(t[loc], P, tt) for tt, dd in zip(tau, d))
    nB = np.array([(t[usb] <= tt).sum(axis=0) for tt in tau])     # (B, n)
    nA = np.array([(t[usa] <= tt).sum(axis=0) for tt in tau])
    fech = (d[:, None] * (1 - 0.3 ** nB * 0.2 ** nA)).sum(axis=0)
    # o despacho poe a massa de "todos ocupados" no mais proximo; e ~q^15
    assert np.allclose(viaP, fech, atol=1e-6), np.abs(viaP - fech).max()
    print(f"ok  s(5)={s(5):.3f} s(9)={s(9):.3f} | fator calibrado {f:.2f} | "
          f"vidas/1000 PCR {r1['vidas']:.1f} -> {r2['vidas']:.1f} (calibrado), "
          f"CVaR10 {r2['cvar10']:.1f} | degraus = 1 - prod q^n")


if __name__ == "__main__":
    _teste()
