import pysus, pandas as pd
from pathlib import Path

UFS = ['RO','AC','AM','RR','PA','AP','TO','MA','PI','CE','RN','PB','PE','AL',
       'SE','BA','MG','ES','RJ','SP','PR','SC','RS','MS','MT','GO','DF']
ANO, MES = 2024, 12

for grupo in ('SR', 'ST'):
    out = Path(f'cnes_{grupo.lower()}'); out.mkdir(exist_ok=True)
    for uf in UFS:
        p = out / f'{uf}.parquet'
        if p.exists():
            continue
        try:
            df = pysus.cnes(state=uf, year=ANO, month=MES, group=grupo,
                            as_dataframe=True)
            if 'TP_UNID' in df.columns:
                df = df[pd.to_numeric(df.TP_UNID, errors='coerce') == 42]
            df.to_parquet(p)
            print(f'{grupo} {uf}: {len(df)}', flush=True)
        except Exception as e:
            print(f'{grupo} {uf} FALHOU: {type(e).__name__}: {e}', flush=True)
print('FIM')
