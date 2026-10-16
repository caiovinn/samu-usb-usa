"""Simulacao de eventos discretos com a PCR como condicao tracadora.

Mesmo laco de fase2_sao_paulo/experimentos/simula.py (que fica intocado):
chamados Poisson nas taxas do SIA, em setores sorteados pela populacao;
grave -> USA livre mais proxima; basico -> USB livre mais proxima, senao USA;
todas ocupadas -> espera a primeira elegivel. Duas mudancas:

  1. tempos de resposta calibrados (atraso + fator * tempo do OSM), como no
     modelo da fase 3;
  2. PCR tracadora: no instante de cada chamado, ANTES de despacha-lo, mede-se
     quando chegaria o primeiro desfibrilador a uma PCR naquele setor — a USB
     livre mais proxima ou a USA livre mais proxima, o que chegar antes (se
     nenhuma estiver livre, a primeira a liberar). Nao ocupa ninguem: a PCR ja
     esta dentro dos volumes observados, e a pergunta e so "quanto tempo ate
     o desfibrilador, dado o estado real da frota naquele momento".

Aqui as ocupacoes sao correlacionadas de verdade (picos ocupam vizinhas
juntas), que e a hipotese que o modelo analitico simplifica.
"""
import numpy as np

from fase3_vidas.modelo import sobrevida as SV

DIAS, AQUEC = 365, 14
T_IDA = 6.0          # min brutos; ordem de grandeza do deslocamento (como na fase 2)
TAU = SV.TAU_GUARDA


def simula(T, pop, x, n_usb, taxa_usa, taxa_usb, s_min, semente, fator=1.0,
           atraso=0.0, dias=DIAS, aquec=AQUEC):
    """Uma rodada. T: (locais, setores) bruto; x: local de cada unidade (USB
    primeiro). Devolve (metricas, soma_s por setor, contagem por setor)."""
    rng = np.random.default_rng(semente)
    n = len(x)
    usb, usa = np.arange(n_usb), np.arange(n_usb, n)
    tu = SV.resposta(T[x], fator, atraso).astype(np.float64)   # (unidades, setores)
    ord_usb = np.argsort(tu[usb], axis=0).T
    ord_usa = np.argsort(tu[usa], axis=0).T + n_usb
    ord_tod = np.argsort(tu, axis=0).T
    horas = 24.0 * (dias + aquec)
    lam = taxa_usa + taxa_usb
    k = rng.poisson(lam * horas)
    chegada = np.sort(rng.uniform(0, horas * 60, k))
    grave = rng.random(k) < taxa_usa / lam
    setor = rng.choice(len(pop), size=k, p=pop / pop.sum())
    ida_media = atraso + fator * T_IDA
    resto = rng.gamma(2.0, max(s_min - ida_media, 1.0) / 2.0, k)

    livre_em = np.zeros(n)
    ocupado = np.zeros(n)
    t0 = aquec * 24 * 60
    resp = np.empty(k); espera = np.zeros(k, bool); t_pcr = np.empty(k)
    for c in range(k):
        agora, i = chegada[c], setor[c]
        # PCR tracadora: primeiro desfibrilador, com a frota como esta agora
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
        # o chamado em si, pela regra observada
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
        fim = inicio + ida + resto[c]
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
        "vidas": float(1000 * sv[med].mean()),
        "t_pcr": float(t_pcr[med].mean()),
        "et_grave": float(resp[g].mean()), "et_basico": float(resp[b].mean()),
        "cob_grave": float(100 * (resp[g] <= TAU).mean()),
        "cob_basico": float(100 * (resp[b] <= TAU).mean()),
        "q_usb": float(ocupado[usb].sum() / (dur * len(usb))),
        "q_usa": float(ocupado[usa].sum() / (dur * len(usa))),
        "frac_fila": float(espera[med].mean()),
        "n_chamados": int(med.sum()),
    }, soma, cnt


def _teste():
    """Com frota enorme e carga minima ninguem fica ocupado: a PCR tracadora
    chega pela unidade mais proxima e a sobrevida simulada = analitica (q=0)."""
    rng = np.random.default_rng(0)
    m, n = 25, 60
    ps, dm = rng.random((m, 2)) * 10, rng.random((n, 2)) * 10
    T = np.sqrt(((ps[:, None, :] - dm[None, :, :]) ** 2).sum(-1)).astype(np.float32)
    pop = rng.integers(100, 2000, n).astype(float)
    x = np.arange(m)                       # 20 USB + 5 USA, uma por local
    r, soma, cnt = simula(T, pop, x, 20, 0.4, 1.6, 30.0, 1, fator=1.5,
                          atraso=2.0, dias=60, aquec=1)
    an = SV.avalia_vidas(T, pop, x[:20], x[20:], r["q_usb"], r["q_usa"],
                         fator=1.5, atraso=2.0)
    assert r["q_usb"] < 0.08 and r["n_chamados"] > 2000
    assert abs(r["vidas"] - an["vidas"]) < 0.03 * an["vidas"], (r["vidas"], an["vidas"])
    print(f"ok  simulacao sem carga: vidas {r['vidas']:.1f} x analitico {an['vidas']:.1f} "
          f"({r['n_chamados']} chamados)")


if __name__ == "__main__":
    _teste()
