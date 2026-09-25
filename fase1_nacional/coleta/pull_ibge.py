import requests, pandas as pd

from fase1_nacional.caminhos import DADOS

V = '93|6318|614'
url = (f'https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022'
       f'/variaveis/{V}?localidades=N6[all]')
dados = requests.get(url, timeout=300).json()

def limpa(v):
    return None if v in ('-', '...', 'X', '..', None) else float(v)

frames = []
for var in dados:
    linhas = [{'cod_mun': int(s['localidade']['id']),
               'municipio': s['localidade']['nome'],
               f"v{var['id']}": limpa(list(s['serie'].values())[0])}
              for s in var['resultados'][0]['series']]
    frames.append(pd.DataFrame(linhas).set_index(['cod_mun', 'municipio']))

mun = pd.concat(frames, axis=1).reset_index().rename(columns={
    'v93': 'populacao', 'v6318': 'area_km2', 'v614': 'densidade'})

loc = requests.get('https://servicodados.ibge.gov.br/api/v1/localidades/municipios',
                   timeout=300).json()
def uf_de(m):
    # alguns municipios novos vem sem microrregiao; cai para a regiao imediata
    try:
        return m['microrregiao']['mesorregiao']['UF']
    except (TypeError, KeyError):
        return m['regiao-imediata']['regiao-intermediaria']['UF']

meta = pd.DataFrame([{
    'cod_mun': m['id'],
    'uf_sigla': uf_de(m)['sigla'],
    'uf_nome':  uf_de(m)['nome'],
    'regiao':   uf_de(m)['regiao']['nome'],
} for m in loc])

mun = mun.merge(meta, on='cod_mun', how='left')
mun['cod_mun6'] = mun.cod_mun // 10
mun.to_parquet(DADOS / 'municipios_ibge.parquet')
print(mun.shape, f"{mun.populacao.sum()/1e6:.1f} mi hab")
print(mun.head())
