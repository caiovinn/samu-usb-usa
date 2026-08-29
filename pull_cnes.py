import requests, time, sys, pandas as pd
from pathlib import Path

U = 'https://apidadosabertos.saude.gov.br/cnes/estabelecimentos'
UFS = [11,12,13,14,15,16,17,21,22,23,24,25,26,27,28,29,31,32,33,35,
       41,42,43,50,51,52,53]
OUT = Path('cnes42')
OUT.mkdir(exist_ok=True)

def pull(uf):
    rows, off = [], 0
    while True:
        for tent in range(4):
            try:
                r = requests.get(U, params={'codigo_uf': uf,
                                            'codigo_tipo_unidade': 42,
                                            'limit': 20, 'offset': off},
                                 timeout=90)
                r.raise_for_status()
                break
            except Exception as e:
                if tent == 3:
                    raise
                time.sleep(2 ** tent)
        batch = r.json().get('estabelecimentos', [])
        if not batch:
            break
        rows += batch
        off += len(batch)          # a API devolve no máximo 20, ignore o `limit`
        time.sleep(0.15)
    return pd.DataFrame(rows)

for uf in UFS:
    p = OUT / f'uf{uf}.parquet'
    if p.exists():
        continue
    df = pull(uf)
    df.to_parquet(p)
    print(f'UF {uf}: {len(df)} estabelecimentos tipo 42', flush=True)
print('FIM')
