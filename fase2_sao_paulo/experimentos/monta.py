"""Monta a base da fase 2: setores, candidatos e matriz de tempo pela rede OSM.

Le fase2_sao_paulo/_raw/ (produzido por pull_dados.py na maquina do usuario) e grava em
dados/:

    sp_setores.parquet     cod_setor, pop, lat, lon, no_osm
    sp_candidatos.parquet  id, codigo_cnes, nome, tipo, lat, lon, no_osm,
                           base_atual, n_usb, n_usa
    sp_tempos.npy          (n_setores, n_candidatos) float32, minutos

Roda na VM Linux da maquina (device_bash) ou no venv do Windows. Nao acessa a
rede. geopandas so e preciso para ler a malha; scipy e opcional (acelera o
Dijkstra, com fallback em heapq puro).
"""
import heapq
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from fase2_sao_paulo.caminhos import DADOS, DADOS_FASE1, RAW

MUN7 = 3550308
INF_MIN = 999.0          # tempo atribuido a par inalcancavel
LIM_SNAP_M = 1000.0      # distancia maxima aceitavel ate a malha viaria


def log(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------- setores
RX_COD = r"^cd_?setor$|^codarea$|^cd_geocodi$"
RX_POP = r"^v0001$|^moradores$|^pop(ulacao)?$"


def _col(cols, rx):
    for c in cols:
        if re.fullmatch(rx, str(c), re.I):
            return c
    return None


def _centroide_anel(anel):
    """Centroide e area assinada de um anel pelo teorema do shoelace."""
    a = np.asarray(anel, dtype=float)
    x, y = a[:, 0], a[:, 1]
    if x[0] != x[-1] or y[0] != y[-1]:          # fecha o anel
        x, y = np.append(x, x[0]), np.append(y, y[0])
    cr = x[:-1] * y[1:] - x[1:] * y[:-1]
    area = cr.sum() / 2.0
    if abs(area) < 1e-15:                        # degenerado: usa a media
        return float(x[:-1].mean()), float(y[:-1].mean()), 0.0
    cx = ((x[:-1] + x[1:]) * cr).sum() / (6.0 * area)
    cy = ((y[:-1] + y[1:]) * cr).sum() / (6.0 * area)
    return cx, cy, area


def _rings_wkb(buf):
    """Aneis de um Polygon/MultiPolygon em WKB. Sem shapely."""
    m = memoryview(buf)
    pos = [0]

    def u32():
        v = np.frombuffer(m, dtype=ordem + "u4", count=1, offset=pos[0])[0]
        pos[0] += 4
        return int(v)

    ordem = "<" if m[0] == 1 else ">"
    pos[0] = 1
    tipo = u32() % 1000                      # ignora as variantes Z/M
    if tipo == 6:                            # MultiPolygon
        n = u32()
        saida = []
        for _ in range(n):
            sub = bytes(m[pos[0]:])
            aneis, consumido = _rings_um_poligono(sub)
            saida.append(aneis)
            pos[0] += consumido
        return saida
    if tipo == 3:                            # Polygon
        aneis, _ = _rings_um_poligono(bytes(m))
        return [aneis]
    return []


def _rings_um_poligono(buf):
    """Aneis de um unico Polygon e quantos bytes ele ocupou."""
    m = memoryview(buf)
    ordem = "<" if m[0] == 1 else ">"
    off = 5                                   # byte order + tipo
    n_aneis = int(np.frombuffer(m, dtype=ordem + "u4", count=1, offset=off)[0])
    off += 4
    aneis = []
    for _ in range(n_aneis):
        n_pt = int(np.frombuffer(m, dtype=ordem + "u4", count=1, offset=off)[0])
        off += 4
        pts = np.frombuffer(m, dtype=ordem + "f8", count=2 * n_pt, offset=off)
        off += 16 * n_pt
        aneis.append(pts.reshape(n_pt, 2))
    return aneis, off


def _centroide_wkb(buf):
    """Centroide area-ponderado a partir do WKB, com buracos negativos."""
    sx = sy = sa = 0.0
    for aneis in _rings_wkb(buf):
        for k, anel in enumerate(aneis):
            cx, cy, a = _centroide_anel(anel)
            if k > 0:
                a = -abs(a)
            sx += cx * a
            sy += cy * a
            sa += a
    if abs(sa) < 1e-15:
        return None
    return sx / sa, sy / sa, abs(sa)


def _centroide(geom):
    """Centroide de Polygon/MultiPolygon do GeoJSON, ponderado pela area.

    Buracos entram com area negativa, como manda a orientacao do GeoJSON.
    """
    if geom is None:
        return None
    poligonos = (geom["coordinates"] if geom["type"] == "MultiPolygon"
                 else [geom["coordinates"]])
    sx = sy = sa = 0.0
    for pol in poligonos:
        for k, anel in enumerate(pol):
            cx, cy, a = _centroide_anel(anel)
            if k > 0:
                a = -abs(a)                      # buraco
            sx += cx * a
            sy += cy * a
            sa += a
    if abs(sa) < 1e-15:
        return None
    return sx / sa, sy / sa, abs(sa)


def carrega_setores():
    """Centroide e populacao de cada setor censitario de SP capital."""
    cache, geo = RAW / "setores_sp.parquet", RAW / "setores_sp.geojson"
    z = RAW / "setores_malha_sp.zip"
    if cache.exists():
        out = pd.read_parquet(cache)
        log(f"  recorte de SP em cache: {len(out)} setores ({cache.name})")
    elif z.exists() and zipfile.ZipFile(z).namelist()[0].endswith(
            (".cpg", ".dbf", ".prj", ".shp", ".shx")) and _tem_shp(z):
        out = _setores_do_shp(z, cache)
    elif geo.exists():
        out = _setores_do_geojson(geo)
    elif z.exists():
        out = _setores_da_malha(z)
    else:
        sys.exit(f"falta {geo.name} ou {z.name} — rode pull_dados.py setores")

    if "pop" not in out:
        out["pop"] = _pop_do_basico(out.cod_setor)
    out = out[out["pop"] > 0].reset_index(drop=True)
    log(f"  {len(out)} setores habitados, {out['pop'].sum():,.0f} habitantes")
    return out


def _tem_shp(z):
    return any(n.lower().endswith(".shp") for n in zipfile.ZipFile(z).namelist())


def _setores_do_shp(z, cache):
    """Recorta SP capital do shapefile nacional do IBGE.

    O arquivo tem 468 mil setores e 2,3 GB descompactado, entao o filtro vai
    para o OGR (`where`) e o centroide sai do WKB direto — sem geopandas e sem
    carregar o Brasil inteiro na memoria.
    """
    try:
        from pyogrio.raw import read
    except ImportError:
        sys.exit("recortar o shapefile nacional precisa de pyogrio: "
                 "pip install pyogrio")
    nome = next(n for n in zipfile.ZipFile(z).namelist() if n.lower().endswith(".shp"))
    caminho = f"/vsizip/{z}/{nome}"
    log(f"  recortando {nome} (468 mil setores) para o municipio {MUN7}...")
    meta, _, geom, campos = read(
        caminho, where=f"CD_MUN = '{MUN7}'",
        columns=["CD_SETOR", "CD_MUN", "AREA_KM2", "v0001"])
    col = {n: campos[i] for i, n in enumerate(meta["fields"])}
    log(f"  {len(geom)} setores em SP capital")

    cen = [_centroide_wkb(g) if g is not None else None for g in geom]
    ok = np.array([c is not None for c in cen])
    out = pd.DataFrame({
        "cod_setor": pd.Series(col["CD_SETOR"]).astype(str).str.zfill(15)[ok].values,
        "lat": np.array([c[1] for c in cen if c], dtype=float),
        "lon": np.array([c[0] for c in cen if c], dtype=float),
        "area_km2": pd.to_numeric(pd.Series(col["AREA_KM2"])[ok], errors="coerce").values,
        "pop": pd.to_numeric(pd.Series(col["v0001"])[ok], errors="coerce").fillna(0).values,
    })
    if (~ok).any():
        log(f"  {(~ok).sum()} setores sem geometria utilizavel, descartados")
    out.to_parquet(cache)
    log(f"  recorte salvo em {cache.name} (as proximas rodadas leem daqui)")
    return out


def _setores_do_geojson(geo):
    """Caminho preferido: GeoJSON so de SP, lido sem geopandas."""
    import json
    d = json.loads(geo.read_text(encoding="utf-8"))
    linhas = []
    for f in d["features"]:
        c = _centroide(f.get("geometry"))
        if c is None:
            continue
        props = f.get("properties", {})
        cod = props.get(_col(props.keys(), RX_COD) or "codarea")
        linhas.append((str(cod).zfill(15), c[1], c[0], c[2]))
    out = pd.DataFrame(linhas, columns=["cod_setor", "lat", "lon", "area_gr2"])
    out = out[out.cod_setor.str.startswith(str(MUN7))].reset_index(drop=True)
    # grau^2 -> km^2 no paralelo de SP
    k = 111.32 ** 2 * np.cos(np.radians(out.lat.mean()))
    out["area_km2"] = out.area_gr2 * k
    log(f"  {len(out)} setores em SP capital (GeoJSON, centroide por shoelace)")
    return out.drop(columns="area_gr2")


def _setores_da_malha(z):
    """Fallback: shapefile/gpkg do IBGE. Este caminho precisa de geopandas."""
    try:
        import geopandas as gpd
    except ImportError:
        sys.exit("ler a malha .zip/.gpkg precisa de geopandas: pip install geopandas")
    with zipfile.ZipFile(z) as zf:
        nomes = [n for n in zf.namelist() if n.lower().endswith((".gpkg", ".shp"))]
    if not nomes:
        sys.exit(f"{z.name} sem .gpkg nem .shp")
    log(f"  malha: {nomes[0]}")
    g = gpd.read_file(f"zip://{z}!{nomes[0]}")
    col_cod = _col(g.columns, RX_COD)
    g[col_cod] = g[col_cod].astype(str).str.zfill(15)
    g = g[g[col_cod].str.startswith(str(MUN7))].copy()
    log(f"  {len(g)} setores em SP capital")
    gm = g.to_crs(31983)
    cen = gm.geometry.centroid.to_crs(4326)
    out = pd.DataFrame({"cod_setor": g[col_cod].values, "lat": cen.y.values,
                        "lon": cen.x.values, "area_km2": gm.area.values / 1e6})
    col_pop = _col(g.columns, RX_POP)
    if col_pop:
        out["pop"] = pd.to_numeric(g[col_pop], errors="coerce").fillna(0).values
        log(f"  populacao veio da propria malha (coluna {col_pop})")
    return out


def _pop_do_basico(cods):
    """Populacao residente do arquivo de agregados basicos do Censo 2022."""
    z = RAW / "setores_basico.zip"
    if not z.exists():
        sys.exit(f"a malha nao traz populacao e falta {z}")
    with zipfile.ZipFile(z) as zf:
        alvo = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not alvo:
            sys.exit(f"{z.name} sem csv: {zf.namelist()[:10]}")
        log(f"  basico: {alvo[0]}")
        with zf.open(alvo[0]) as fh:
            df = pd.read_csv(fh, sep=";", dtype=str, low_memory=False,
                             encoding="latin-1")
    col_cod, col_pop = _col(df.columns, RX_COD), _col(df.columns, RX_POP)
    if not (col_cod and col_pop):
        sys.exit(f"colunas nao reconhecidas no basico: {list(df.columns)[:15]}")
    df[col_cod] = df[col_cod].astype(str).str.replace(r"\D", "", regex=True).str.zfill(15)
    m = dict(zip(df[col_cod], pd.to_numeric(df[col_pop], errors="coerce")))
    achou = pd.Series(cods).map(m)
    log(f"  populacao do basico: {achou.notna().sum()}/{len(cods)} setores casaram")
    return achou.fillna(0).values


# ------------------------------------------------------------------ candidatos
TIPOS_BASE = {1, 2, 4, 5, 7, 15, 20, 21, 36, 42, 73}


def carrega_candidatos():
    """Bases SAMU atuais + equipamentos publicos de saude, sem duplicata."""
    p = RAW / "cnes_sp.parquet"
    if not p.exists():
        sys.exit(f"falta {p} — rode pull_dados.py cnes na sua maquina")
    df = pd.read_parquet(p)
    df["ativo"] = df.codigo_motivo_desabilitacao_estabelecimento.isna()
    nj = df.descricao_natureza_juridica_estabelecimento.astype(str).str[:1]
    df["publico"] = nj.isin(["1", "3"])
    df["lat"] = pd.to_numeric(df.latitude_estabelecimento_decimo_grau, errors="coerce")
    df["lon"] = pd.to_numeric(df.longitude_estabelecimento_decimo_grau, errors="coerce")

    ok = (df.ativo & df.publico
          & df.codigo_tipo_unidade.astype(float).isin(TIPOS_BASE)
          & df.lat.between(-24.1, -23.3) & df.lon.between(-46.9, -46.3))
    c = df[ok].copy()
    log(f"  {len(c)} estabelecimentos publicos ativos com coordenada plausivel")

    # dedupe por coordenada (~11 m): varias unidades dividem o mesmo endereco
    c["chave"] = (c.lat.round(4).astype(str) + "," + c.lon.round(4).astype(str))
    c = (c.sort_values("codigo_tipo_unidade")
           .drop_duplicates("chave").reset_index(drop=True))

    # frota atual por local, a partir da base nacional ja existente
    frota = pd.read_parquet(DADOS_FASE1 / "frota.parquet")
    f = frota[(frota.cod_mun == MUN7) & frota.ativo
              & frota.setor.isin(["publico", "sem_fins_lucrativos"])
              & frota.modalidade.isin(["USB", "USA"])].copy()
    f["chave"] = (f.lat.round(4).astype(str) + "," + f.lon.round(4).astype(str))
    piv = (f.pivot_table(index="chave", columns="modalidade", values="codigo_cnes",
                         aggfunc="count").fillna(0).astype(int))
    for m in ("USB", "USA"):
        if m not in piv:
            piv[m] = 0

    # base atual cuja coordenada nao bateu com nenhum candidato: entra como candidato
    faltando = piv.index.difference(c.chave)
    if len(faltando):
        extra = (f[f.chave.isin(faltando)].drop_duplicates("chave")
                 [["codigo_cnes", "nome_fantasia", "lat", "lon", "chave"]])
        extra["codigo_tipo_unidade"] = 42
        c = pd.concat([c, extra], ignore_index=True)
        log(f"  + {len(extra)} bases SAMU sem equipamento correspondente")

    c = c.merge(piv, left_on="chave", right_index=True, how="left")
    c[["USB", "USA"]] = c[["USB", "USA"]].fillna(0).astype(int)

    out = pd.DataFrame({
        "id": np.arange(len(c)),
        "codigo_cnes": c.codigo_cnes.values,
        "nome": c.nome_fantasia.values,
        "tipo": pd.to_numeric(c.codigo_tipo_unidade, errors="coerce").astype(int).values,
        "lat": c.lat.values, "lon": c.lon.values,
        "n_usb": c.USB.values, "n_usa": c.USA.values,
    })
    out["base_atual"] = (out.n_usb + out.n_usa) > 0
    log(f"  {len(out)} candidatos, dos quais {out.base_atual.sum()} sao base hoje "
        f"({out.n_usb.sum()} USB + {out.n_usa.sum()} USA)")
    return out


# ----------------------------------------------------------------------- grafo
def carrega_grafo():
    n = pd.read_parquet(RAW / "osm_nos.parquet")
    e = pd.read_parquet(RAW / "osm_arestas.parquet")
    idx = pd.Series(np.arange(len(n)), index=n.osmid.values)
    u = idx.reindex(e.u.values).values
    v = idx.reindex(e.v.values).values
    ok = ~(pd.isna(u) | pd.isna(v))
    u, v = u[ok].astype(np.int64), v[ok].astype(np.int64)
    w = (e.travel_time.values[ok] / 60.0).astype(np.float64)   # minutos
    ruim = ~np.isfinite(w) | (w <= 0)
    if ruim.any():   # aresta sem velocidade: 30 km/h
        w[ruim] = e.length.values[ok][ruim] / 1000.0 / 30.0 * 60.0

    # o grafo do OSM e multigrafo: arestas paralelas viram uma so, com o menor
    # tempo. Sem isso a matriz esparsa do scipy SOMA as paralelas.
    a = pd.DataFrame({"u": u, "v": v, "w": w}).groupby(["u", "v"], sort=False,
                                                       as_index=False).w.min()
    log(f"  grafo: {len(n)} nos, {len(u)} arestas ({len(a)} apos fundir paralelas)")
    return n.x.values, n.y.values, a.u.values, a.v.values, a.w.values, len(n)


def no_mais_proximo(px, py, nx, ny, celula=0.005):
    """Indice do no OSM mais proximo de cada ponto. Grade espacial, sem scipy.

    Achar um candidato no anel r nao basta: a distancia e escalada por cos(lat),
    entao o vizinho mais proximo pode estar dois aneis adiante. Por isso a busca
    continua por mais dois aneis depois do primeiro acerto.
    """
    ix = np.floor(nx / celula).astype(np.int64)
    iy = np.floor(ny / celula).astype(np.int64)
    balde = {}
    for k, (a, b) in enumerate(zip(ix, iy)):
        balde.setdefault((a, b), []).append(k)

    cosl = np.cos(np.radians(float(np.mean(ny))))
    out = np.empty(len(px), dtype=np.int64)
    for i, (x, y) in enumerate(zip(px, py)):
        a0, b0 = int(np.floor(x / celula)), int(np.floor(y / celula))
        cand, r, ate = [], 0, -1
        while r <= 60:
            for a in range(a0 - r, a0 + r + 1):
                for b in range(b0 - r, b0 + r + 1):
                    if r == 0 or max(abs(a - a0), abs(b - b0)) == r:
                        cand += balde.get((a, b), [])
            if cand and ate < 0:
                ate = r + 2
            if 0 <= ate <= r:
                break
            r += 1
        if not cand:
            out[i] = -1
            continue
        c = np.fromiter(cand, dtype=np.int64)
        d = ((nx[c] - x) * cosl) ** 2 + (ny[c] - y) ** 2
        out[i] = c[np.argmin(d)]
    return out


def dist_ao_no(lon, lat, nx, ny, no):
    """Metros entre cada ponto e o no em que ele foi encaixado."""
    cosl = np.cos(np.radians(float(np.mean(lat))))
    return np.sqrt(((nx[no] - lon) * cosl) ** 2 + (ny[no] - lat) ** 2) * 111320.0


def _csr(u, v, w, n):
    ordem = np.argsort(u, kind="stable")
    u, v, w = u[ordem], v[ordem], w[ordem]
    inicio = np.zeros(n + 1, dtype=np.int64)
    np.add.at(inicio, u + 1, 1)
    return np.cumsum(inicio), v, w


def matriz_tempos(fontes, alvos, u, v, w, n_nos, corte=60.0, bloco=64):
    """(len(alvos), len(fontes)) minutos. Dijkstra a partir de cada candidato."""
    try:
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import dijkstra
        A = csr_matrix((w, (u, v)), shape=(n_nos, n_nos))
        saida = np.empty((len(alvos), len(fontes)), dtype=np.float32)
        for i in range(0, len(fontes), bloco):
            f = fontes[i:i + bloco]
            d = dijkstra(A, directed=True, indices=f, limit=corte)
            saida[:, i:i + bloco] = d[:, alvos].T.astype(np.float32)
            print(f"\r    {min(i+bloco, len(fontes))}/{len(fontes)} fontes", end="")
        print()
    except ImportError:
        log("    scipy ausente; Dijkstra em python puro (mais lento)")
        ini, viz, peso = _csr(u, v, w, n_nos)
        saida = np.empty((len(alvos), len(fontes)), dtype=np.float32)
        for k, s in enumerate(fontes):
            dist = np.full(n_nos, np.inf)
            dist[s] = 0.0
            fila = [(0.0, int(s))]
            while fila:
                d, x = heapq.heappop(fila)
                if d > dist[x] or d > corte:
                    continue
                for p in range(ini[x], ini[x + 1]):
                    y, nd = viz[p], d + peso[p]
                    if nd < dist[y]:
                        dist[y] = nd
                        heapq.heappush(fila, (nd, int(y)))
            dist[dist > corte] = np.inf     # mesmo criterio do `limit` do scipy
            saida[:, k] = dist[alvos]
            print(f"\r    {k+1}/{len(fontes)} fontes", end="")
        print()
    saida[~np.isfinite(saida)] = INF_MIN
    return saida


# ------------------------------------------------------------------------ main
def main():
    log("[1/4] setores censitarios")
    st = carrega_setores()
    log("[2/4] candidatos")
    cd = carrega_candidatos()
    log("[3/4] rede viaria")
    nx_, ny_, u, v, w, n_nos = carrega_grafo()
    st["no_osm"] = no_mais_proximo(st.lon.values, st.lat.values, nx_, ny_)
    cd["no_osm"] = no_mais_proximo(cd.lon.values, cd.lat.values, nx_, ny_)
    st = st[st.no_osm >= 0].reset_index(drop=True)
    cd = cd[cd.no_osm >= 0].reset_index(drop=True)
    st["d_no_m"] = dist_ao_no(st.lon.values, st.lat.values, nx_, ny_, st.no_osm.values)
    cd["d_no_m"] = dist_ao_no(cd.lon.values, cd.lat.values, nx_, ny_, cd.no_osm.values)

    # Um lote de registros do CNES tem coordenada de fabrica fora da cidade
    # (varios equipamentos no mesmo ponto, a ~17 km da malha). Longe demais da
    # rua, o ponto nao representa nada: sai do conjunto de candidatos.
    longe = cd.d_no_m > LIM_SNAP_M
    if longe.any():
        log(f"  descartando {longe.sum()} candidatos a mais de "
            f"{LIM_SNAP_M:.0f} m da malha (coordenada suspeita no CNES)")
        if cd.loc[longe, "base_atual"].any():
            nb = int(cd.loc[longe, "base_atual"].sum())
            log(f"  !! ATENCAO: {nb} deles sao base SAMU hoje — confira antes de seguir")
        cd = cd[~longe].reset_index(drop=True)
    fora = st.d_no_m > LIM_SNAP_M
    if fora.any():
        log(f"  {fora.sum()} setores a mais de {LIM_SNAP_M:.0f} m da malha "
            f"({100*st.loc[fora,'pop'].sum()/st['pop'].sum():.2f}% da populacao)")
    cd["id"] = np.arange(len(cd))
    log("[4/4] matriz de tempo")
    T = matriz_tempos(cd.no_osm.values, st.no_osm.values, u, v, w, n_nos)

    DADOS.mkdir(exist_ok=True)
    st.to_parquet(DADOS / "sp_setores.parquet")
    cd.to_parquet(DADOS / "sp_candidatos.parquet")
    np.save(DADOS / "sp_tempos.npy", T)
    fin = T[T < INF_MIN]
    log(f"\nsp_setores {st.shape} | sp_candidatos {cd.shape} | tempos {T.shape}")
    log(f"tempo mediano {np.median(fin):.1f} min | "
        f"pares inalcancaveis {100*(T>=INF_MIN).mean():.2f}%")
    log(f"tempo ate o candidato mais proximo: mediana "
        f"{np.median(T.min(axis=1)):.1f} min, p90 {np.percentile(T.min(axis=1),90):.1f} min")


if __name__ == "__main__":
    main()
