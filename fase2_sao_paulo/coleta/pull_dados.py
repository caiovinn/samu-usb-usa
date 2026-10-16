"""Coleta dos dados brutos da fase 2 (São Paulo capital).

RODE ESTE ARQUIVO NA SUA MÁQUINA (Windows), não no sandbox: ftp.ibge.gov.br,
apidadosabertos.saude.gov.br e o OpenStreetMap estão fora da lista de egresso
dos ambientes do Claude.

    python -m venv .venv-eda
    .venv-eda\\Scripts\\activate
    pip install "numpy>=2" pandas pyarrow requests osmnx
    python -m fase2_sao_paulo.coleta.pull_dados

Tudo cai em fase2_sao_paulo/_raw/. Cada etapa é idempotente: arquivo que já
existe é pulado.
"""
import io
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

from fase2_sao_paulo.caminhos import RAW

RAW.mkdir(parents=True, exist_ok=True)

MUN6, MUN7 = 355030, 3550308
UA = {"User-Agent": "eda-usb-usa/0.2 (pesquisa academica MAI5003)"}


def log(*a):
    print(*a, flush=True)


def baixa(url, destino, timeout=600):
    """Download com barra simples. Devolve True se o arquivo existe ao fim."""
    destino = Path(destino)
    if destino.exists() and destino.stat().st_size > 0:
        log(f"  ja existe: {destino.name} ({destino.stat().st_size/1e6:.1f} MB)")
        return True
    tmp = destino.with_suffix(destino.suffix + ".part")
    log(f"  baixando {url}")
    with requests.get(url, stream=True, timeout=timeout, headers=UA) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        feito = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                feito += len(chunk)
                if total:
                    print(f"\r    {feito/1e6:7.1f}/{total/1e6:.1f} MB", end="")
        print()
    tmp.rename(destino)
    log(f"  ok: {destino.name} ({destino.stat().st_size/1e6:.1f} MB)")
    return True


# --------------------------------------------------------------------- setores
RAIZ_SETORES = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
                "Agregados_por_Setores_Censitarios/")
UFS_OUTRAS = {"AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
              "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","TO"}


def lista(url):
    """Nomes de arquivos/pastas num indice HTML do FTP do IBGE."""
    r = requests.get(url, timeout=120, headers=UA)
    r.raise_for_status()
    nomes = re.findall(r'href="([^"?][^"]*)"', r.text)
    return [n for n in nomes if not n.startswith(("/", "http", "?", ".."))]


def caminha(url, prof=0, max_prof=4, visto=None):
    """Percorre o indice do FTP e devolve [(url_arquivo, tamanho_desconhecido)]."""
    visto = visto if visto is not None else set()
    if url in visto or prof > max_prof:
        return []
    visto.add(url)
    try:
        nomes = lista(url)
    except Exception as e:
        log(f"    ! nao listou {url}: {e}")
        return []
    out = []
    for n in nomes:
        alvo = url + n
        if n.endswith("/"):
            base = n.strip("/").upper()
            # nao desce em pastas de outras UFs
            if base in UFS_OUTRAS:
                continue
            out += caminha(alvo, prof + 1, max_prof, visto)
        else:
            out.append(alvo)
    return out


API_MALHA = ("https://servicodados.ibge.gov.br/api/v3/malhas/municipios/3550308"
             "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=setor")
RAIZ_MALHAS = ("https://ftp.ibge.gov.br/Organizacao_do_Territorio/Malhas_Territoriais/"
               "Malhas_de_Setores_Censitarios__Divisoes_Intramunicipais/")


def _arvore(raiz, cache):
    """Lista (com cache em disco) os arquivos de uma subarvore do FTP."""
    if cache.exists():
        urls = cache.read_text(encoding="utf-8").split()
        log(f"  arvore em cache: {len(urls)} arquivos ({cache.name})")
        return urls
    log(f"  mapeando {raiz} (1-2 min)...")
    urls = caminha(raiz)
    cache.write_text("\n".join(urls), encoding="utf-8")
    log(f"  {len(urls)} arquivos -> {cache.name}")
    return urls


def _escolhe(urls, *regras):
    for rx in regras:
        cand = [u for u in urls if re.search(rx, u, re.I)]
        if cand:
            return sorted(cand, key=len)[0]
    return None


def etapa_setores():
    """Malha dos setores de SP + populacao residente.

    O IBGE so publica a malha com atributos para o Brasil inteiro (o .gpkg
    nacional passa de 2 GB). Entao: primeiro tenta a API de malhas, que devolve
    so o municipio pedido; se ela nao aceitar intrarregiao=setor, procura uma
    malha por UF em Malhas_Territoriais; so em ultimo caso baixa o arquivo BR.
    """
    log("\n[1/3] setores censitarios (IBGE, Censo 2022)")
    geo = RAW / "setores_sp.geojson"

    # -- 1. API de malhas, so o municipio de Sao Paulo
    if not geo.exists():
        log("  tentando a API de malhas do IBGE...")
        try:
            r = requests.get(API_MALHA, timeout=300, headers=UA)
            if r.ok and r.text.lstrip().startswith("{"):
                d = r.json()
                n = len(d.get("features", []))
                if n > 1000:
                    geo.write_text(r.text, encoding="utf-8")
                    log(f"  ok: {n} setores -> {geo.name} "
                        f"({geo.stat().st_size/1e6:.1f} MB)")
                else:
                    log(f"  a API devolveu so {n} feicoes; nao e malha de setor")
            else:
                log(f"  API recusou (HTTP {r.status_code})")
        except Exception as e:
            log(f"  API falhou: {e}")

    # -- 2. malha por UF em Malhas_Territoriais
    if not geo.exists() and not (RAW / "setores_malha_sp.zip").exists():
        urls = _arvore(RAIZ_MALHAS, RAW / "_ftp_tree_malhas.txt")
        alvo = _escolhe(urls,
                        r"2022.*/SP[_/].*\.zip$",
                        r"2022.*SP_setores.*\.zip$",
                        r"/SP_.*setores.*(2022|CD2022).*\.zip$",
                        r"/SP[_.].*\.zip$")
        if alvo:
            log(f"  malha por UF: {alvo}")
            baixa(alvo, RAW / "setores_malha_sp.zip")
        else:
            log("  !! nenhuma malha de SP encontrada; caindo para o arquivo BR")
            urls_ag = _arvore(RAIZ_SETORES, RAW / "_ftp_tree.txt")
            br = _escolhe(urls_ag, r"malha_com_atributos/setores/shp/BR/.*\.zip$",
                          r"malha_com_atributos/setores/gpkg/BR/.*\.gpkg$")
            if br:
                log(f"  ATENCAO: arquivo do Brasil inteiro, pode passar de 1 GB")
                baixa(br, RAW / ("setores_malha_sp.zip" if br.endswith(".zip")
                                 else "setores_malha_br.gpkg"))

    # -- 3. populacao: agregados basicos por setor (Brasil, csv zipado)
    urls_ag = _arvore(RAIZ_SETORES, RAW / "_ftp_tree.txt")
    basico = _escolhe(urls_ag,
                      r"Agregados_por_Setor_csv/.*basico.*\.zip$",
                      r"Agregados_por_setores_basico_BR.*\.zip$")
    log(f"  basico -> {basico}")
    if basico:
        baixa(basico, RAW / "setores_basico.zip")
    else:
        log("  !! nao achei os agregados basicos. Mande _ftp_tree.txt ao Claude.")


# ------------------------------------------------------------------------ cnes
API = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
# candidatos plausiveis para sediar uma unidade movel
TIPOS = {1: "posto de saude", 2: "centro de saude/UBS", 4: "policlinica",
         5: "hospital geral", 7: "hospital especializado",
         15: "unidade mista", 20: "pronto socorro geral",
         21: "pronto socorro especializado", 36: "clinica/ambulatorio",
         42: "unidade movel", 73: "pronto atendimento/UPA"}


def pull_tipo(tipo):
    rows, off = [], 0
    while True:
        for tent in range(4):
            try:
                r = requests.get(API, timeout=90, headers=UA,
                                 params={"codigo_municipio": MUN6,
                                         "codigo_tipo_unidade": tipo,
                                         "limit": 20, "offset": off})
                r.raise_for_status()
                break
            except Exception:
                if tent == 3:
                    raise
                time.sleep(2 ** tent)
        lote = r.json().get("estabelecimentos", [])
        if not lote:
            break
        rows += lote
        off += len(lote)
        time.sleep(0.12)
    return pd.DataFrame(rows)


def etapa_cnes():
    log("\n[2/3] estabelecimentos CNES do municipio de Sao Paulo")
    destino = RAW / "cnes_sp.parquet"
    if destino.exists():
        log(f"  ja existe: {destino.name}")
        return
    partes = []
    for tipo, nome in TIPOS.items():
        p = RAW / f"cnes_sp_tipo{tipo:02d}.parquet"
        if p.exists():
            partes.append(pd.read_parquet(p))
            log(f"  tipo {tipo:02d} {nome:<28} (cache)")
            continue
        df = pull_tipo(tipo)
        df.to_parquet(p)
        partes.append(df)
        log(f"  tipo {tipo:02d} {nome:<28} {len(df):5d} estabelecimentos")
    todo = pd.concat(partes, ignore_index=True).drop_duplicates("codigo_cnes")
    todo.to_parquet(destino)
    log(f"  {len(todo)} estabelecimentos -> {destino.name}")


# ------------------------------------------------------------------------- osm
def etapa_osm():
    log("\n[3/3] rede viaria do OpenStreetMap")
    n_out, e_out = RAW / "osm_nos.parquet", RAW / "osm_arestas.parquet"
    if n_out.exists() and e_out.exists():
        log("  ja existe: osm_nos.parquet / osm_arestas.parquet")
        return
    try:
        import osmnx as ox
    except ImportError:
        log("  !! osmnx nao instalado. pip install osmnx")
        return
    log("  baixando o grafo (5-15 min, ~200 mil nos)...")
    G = ox.graph_from_place("São Paulo, São Paulo, Brazil", network_type="drive")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    nos, arestas = ox.graph_to_gdfs(G)
    (pd.DataFrame({"osmid": nos.index, "x": nos.x.values, "y": nos.y.values})
       .to_parquet(n_out))
    a = arestas.reset_index()[["u", "v", "length", "travel_time", "highway"]]
    a["highway"] = a.highway.astype(str)
    a.to_parquet(e_out)
    log(f"  {len(nos)} nos / {len(a)} arestas -> _raw/")


if __name__ == "__main__":
    etapas = sys.argv[1:] or ["setores", "cnes", "osm"]
    if "setores" in etapas:
        etapa_setores()
    if "cnes" in etapas:
        etapa_cnes()
    if "osm" in etapas:
        etapa_osm()
    log("\nFIM. Avise o Claude: ele le fase2_sao_paulo/_raw/ direto da pasta.")
