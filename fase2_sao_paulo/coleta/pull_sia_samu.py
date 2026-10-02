"""Producao do SAMU 192 no SIA/SUS (DATASUS) — base para estimar a ocupacao q.

RODE NA SUA MAQUINA (o FTP do DATASUS esta fora do egresso dos sandboxes):

    uv run python -m fase2_sao_paulo.coleta.pull_sia_samu            # 2401..2607
    uv run python -m fase2_sao_paulo.coleta.pull_sia_samu 2501 2512  # outra janela

O SIA de SP vem em PASP{aamm}{a,b,c,d}.dbc, 60-160 MB cada, ~360 MB por mes.
Nada disso e guardado: cada arquivo e baixado, descomprimido para .dbf,
filtrado e apagado. Fica so o parquet minusculo com as linhas do subgrupo
03.01.03 (SAMU 192: regulacao, USB, USA, motolancia, ...) do estado de SP.

O filtro nao usa dbfread (python puro, minutos por arquivo): o DBF e um bloco
de registros de largura fixa, entao o arquivo inteiro vira uma matriz uint8
(n_registros, largura) por memmap e o filtro e uma comparacao de bytes
vetorizada — segundos por arquivo. So as linhas que passam sao decodificadas.

Idempotente: arquivo cujo parquet ja existe em _raw/sia/ e pulado.
"""
import re
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from ftplib import FTP

import numpy as np
import pandas as pd

from fase2_sao_paulo.caminhos import DADOS, RAW

HOST = "ftp.datasus.gov.br"
PASTA = "/dissemin/publicos/SIASUS/200801_/Dados"
SAIDA = RAW / "sia"
PREFIXO_SAMU = b"0301030"        # subgrupo 03.01.03 da tabela SIGTAP
N_WORKERS = 4                    # gentil com o FTP; o gargalo e a rede


def log(*a):
    print(*a, flush=True)


def lista_arquivos(ini, fim):
    """PASP{aamm}{parte}.dbc com ini <= aamm <= fim (aamm como int)."""
    ftp = FTP(HOST, timeout=120)
    ftp.login()
    nomes = ftp.nlst(PASTA)
    ftp.quit()
    rx = re.compile(r"PASP(\d{4})([a-z]?)\.dbc$", re.I)
    out = []
    for n in nomes:
        m = rx.search(n)
        if m and ini <= int(m.group(1)) <= fim:
            out.append(n.rsplit("/", 1)[-1])
    return sorted(out)


def le_dbf_filtrado(caminho):
    """Linhas do DBF cujo PA_PROC_ID comeca com PREFIXO_SAMU, como DataFrame."""
    with open(caminho, "rb") as f:
        cab = f.read(32)
        n_reg = int.from_bytes(cab[4:8], "little")
        tam_cab = int.from_bytes(cab[8:10], "little")
        tam_reg = int.from_bytes(cab[10:12], "little")
        campos, pos = [], 1                     # byte 0 do registro: flag de apagado
        while True:
            d = f.read(32)
            if not d or d[0] == 0x0D:
                break
            nome = d[:11].split(b"\x00")[0].decode("ascii")
            tam = d[16]
            campos.append((nome, pos, tam))
            pos += tam
    if n_reg == 0:
        return pd.DataFrame(columns=[c[0] for c in campos])
    R = np.memmap(caminho, dtype=np.uint8, mode="r", offset=tam_cab,
                  shape=(n_reg, tam_reg))
    _, p0, _ = next(c for c in campos if c[0] == "PA_PROC_ID")
    alvo = np.frombuffer(PREFIXO_SAMU, dtype=np.uint8)
    ok = np.ones(n_reg, dtype=bool)
    for k, b in enumerate(alvo):                 # coluna a coluna: sem copiar R
        ok &= R[:, p0 + k] == b
    ok &= R[:, 0] != ord("*")                    # registro apagado
    sel = np.asarray(R[np.nonzero(ok)[0]])
    del R
    dados = {nome: [bytes(l[p:p + t]).decode("latin-1").strip() for l in sel]
             for nome, p, t in campos}
    return pd.DataFrame(dados)


def processa(nome):
    """Baixa, descomprime, filtra e apaga. Devolve (nome, n_linhas, segundos)."""
    import pyreaddbc
    destino = SAIDA / (nome.rsplit(".", 1)[0] + ".parquet")
    if destino.exists():
        return nome, -1, 0.0
    t0 = time.time()
    dbc, dbf = SAIDA / nome, SAIDA / (nome[:-4] + ".dbf")
    for tentativa in range(4):
        try:
            urllib.request.urlretrieve(f"ftp://{HOST}{PASTA}/{nome}", dbc)
            break
        except Exception as e:                   # FTP do DATASUS cai as vezes
            if tentativa == 3:
                raise
            time.sleep(30 * (tentativa + 1))
    pyreaddbc.dbc2dbf(str(dbc), str(dbf))
    dbc.unlink()
    df = le_dbf_filtrado(dbf)
    dbf.unlink()
    df["arquivo"] = nome
    df.to_parquet(destino)
    return nome, len(df), time.time() - t0


def junta():
    """Concatena os parciais em dados/fase2/sp_samu_producao.parquet."""
    partes = sorted(SAIDA.glob("PASP*.parquet"))
    df = pd.concat([pd.read_parquet(p) for p in partes], ignore_index=True)
    arq = DADOS / "sp_samu_producao.parquet"
    df.to_parquet(arq)
    return df, arq


def main(ini=2401, fim=2607):
    SAIDA.mkdir(parents=True, exist_ok=True)
    nomes = lista_arquivos(ini, fim)
    falta = [n for n in nomes
             if not (SAIDA / (n.rsplit(".", 1)[0] + ".parquet")).exists()]
    log(f"{len(nomes)} arquivos PASP em {ini}..{fim}; faltam {len(falta)}")
    erros = []
    with ProcessPoolExecutor(N_WORKERS) as ex:
        fut = {ex.submit(processa, n): n for n in falta}
        for i, f in enumerate(as_completed(fut), 1):
            try:
                nome, n, s = f.result()
                log(f"  [{i}/{len(falta)}] {nome}: {n} linhas SAMU ({s:.0f} s)")
            except Exception as e:
                erros.append(fut[f])
                log(f"  [{i}/{len(falta)}] {fut[f]}: ERRO {e!r}")
    df, arq = junta()
    log(f"\n{len(df)} linhas -> {arq}")
    if erros:
        log(f"!! {len(erros)} arquivos falharam (rode de novo para retomar): {erros}")


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    main(*a) if a else main()
