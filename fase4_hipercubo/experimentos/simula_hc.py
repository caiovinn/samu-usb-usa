"""Simulacao da fase 3 com opcao de servico exponencial (hipotese do hipercubo).

Copia de fase3_vidas/experimentos/simula_vidas.simula (que fica intocada) com UMA
mudanca controlada por `servico`:
  "gamma"  igual a fase 3: ocupacao = ida + resto, resto ~ Gamma(2), media s_min.
  "exp"    ocupacao total ~ Exponencial(media s_min), independente do local (o
           servico do hipercubo de Larson).
Serve para medir quanto da diferenca modelo-simulacao vem da hipotese de servico.
Com servico="gamma" reproduz simula_vidas.simula (conferido em _teste).
"""
import numpy as np

from fase3_vidas.modelo import sobrevida as SV
from fase3_vidas.experimentos import simula_vidas as SI


def simula(T, pop, x, n_usb, taxa_usa, taxa_usb, s_min, semente, fator=1.0, atraso=0.0,
           dias=SI.DIAS, aquec=SI.AQUEC, servico="gamma"):
    if servico == "gamma":
        return SI.simula(T, pop, x, n_usb, taxa_usa, taxa_usb, s_min, semente, fator, atraso, dias, aquec)
    assert servico == "exp"
    rng = np.random.default_rng(semente)
    n = len(x)
    usb, usa = np.arange(n_usb), np.arange(n_usb, n)
    tu = SV.resposta(T[x], fator, atraso).astype(np.float64)
    ord_usb = np.argsort(tu[usb], axis=0).T
    ord_usa = np.argsort(tu[usa], axis=0).T + n_usb
    ord_tod = np.argsort(tu, axis=0).T
    horas = 24.0 * (dias + aquec)
    lam = taxa_usa + taxa_usb
    k = rng.poisson(lam * horas)
    chegada = np.sort(rng.uniform(0, horas * 60, k))
    grave = rng.random(k) < taxa_usa / lam
    setor = rng.choice(len(pop), size=k, p=pop / pop.sum())
    dur_total = rng.exponential(s_min, k)           # ocupacao total (ida inclusa)

    livre_em = np.zeros(n)
    ocupado = np.zeros(n)
    t0 = aquec * 24 * 60
    resp = np.empty(k); espera = np.zeros(k, bool); t_pcr = np.empty(k)
    for c in range(k):
        agora, i = chegada[c], setor[c]
        cand = []
        for lst in (ord_usb[i], ord_usa[i]):
            ok = livre_em[lst] <= agora
            if ok.any():
                cand.append(tu[lst[np.argmax(ok)], i])
        if cand:
            t_pcr[c] = min(cand)
        else:
            o = ord_tod[i]
            t_pcr[c] = np.min(livre_em[o] - agora + tu[o, i])
        listas = (ord_usa[i],) if grave[c] else (ord_usb[i], ord_usa[i])
        u = -1
        for lst in listas:
            ok = livre_em[lst] <= agora
            if ok.any():
                u = lst[np.argmax(ok)]
                break
        inicio = agora
        if u < 0:
            eleg = np.concatenate(listas)
            u = eleg[np.argmin(livre_em[eleg])]
            inicio = livre_em[u]
            espera[c] = True
        ida = tu[u, i]
        resp[c] = inicio - agora + ida
        fim = inicio + max(dur_total[c], ida)        # nao termina antes de chegar
        if fim > t0:
            ocupado[u] += fim - max(inicio, t0)
        livre_em[u] = fim
    med = chegada >= t0
    dur = dias * 24 * 60
    g, b = med & grave, med & ~grave
    sv = SV.s(t_pcr)
    soma = np.bincount(setor[med], weights=sv[med], minlength=len(pop))
    cnt = np.bincount(setor[med], minlength=len(pop))
    return {
        "vidas": float(1000 * sv[med].mean()), "t_pcr": float(t_pcr[med].mean()),
        "et_grave": float(resp[g].mean()), "et_basico": float(resp[b].mean()),
        "cob_grave": float(100 * (resp[g] <= SI.TAU).mean()),
        "cob_basico": float(100 * (resp[b] <= SI.TAU).mean()),
        "q_usb": float(ocupado[usb].sum() / (dur * len(usb))),
        "q_usa": float(ocupado[usa].sum() / (dur * len(usa))),
        "frac_fila": float(espera[med].mean()), "n_chamados": int(med.sum()),
    }, soma, cnt


def _teste():
    rng = np.random.default_rng(0)
    m, n = 25, 60
    ps, dm = rng.random((m, 2)) * 10, rng.random((n, 2)) * 10
    T = np.sqrt(((ps[:, None, :] - dm[None, :, :]) ** 2).sum(-1)).astype(np.float32)
    pop = rng.integers(100, 2000, n).astype(float)
    x = np.arange(m)
    a = simula(T, pop, x, 20, 0.4, 1.6, 30.0, 1, 1.5, 2.0, dias=20, aquec=1, servico="gamma")[0]
    b = SI.simula(T, pop, x, 20, 0.4, 1.6, 30.0, 1, 1.5, 2.0, dias=20, aquec=1)[0]
    assert a == b, "servico='gamma' tem de reproduzir a fase 3"
    e = simula(T, pop, x, 20, 0.4, 1.6, 30.0, 1, 1.5, 2.0, dias=60, aquec=1, servico="exp")[0]
    # ocupacao media ~ carga oferecida (carga baixa, sem fila): taxa*s/n_unidades
    print(f"simula_hc: gamma = fase 3; exp: q_usb {e['q_usb']:.3f}, q_usa {e['q_usa']:.3f}, fila {e['frac_fila']:.4f}")


if __name__ == "__main__":
    _teste()
