# Como instalar e rodar

## 1. Instalar o uv (uma vez por máquina)

| sistema | comando |
|---|---|
| Windows | `winget install astral-sh.uv` |
| macOS / Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

Feche e reabra o terminal depois.

## 2. Instalar tudo

Na raiz do repositório:

```bash
uv sync
```

Isso baixa o Python 3.12 (não precisa ter Python instalado antes) e instala
todas as dependências do projeto, fase 1 e fase 2 juntas. Um comando só, todo
mundo com as mesmas versões.

## 3. Rodar

O projeto é dividido em dois pacotes Python, `fase1_nacional` e
`fase2_sao_paulo` (ver [README.md](README.md) para o que cada um é). Todo
script roda **a partir da raiz do repositório** com `python -m`:

```bash
uv run python -m fase2_sao_paulo.modelo.huff2sfca
uv run python -m fase2_sao_paulo.experimentos.roda
uv run python -m fase1_nacional.experimentos.tabelas
```

Sempre `uv run python -m fase.subpasta.arquivo` (sem `.py` no final) — não
precisa ativar nada nem `cd` para dentro da pasta.

## 4. Buscar os dados (só na primeira vez)

`fase1_nacional/_raw/`, `fase2_sao_paulo/_raw/` e `dados/fase2/sp_tempos.npy`
não vêm no clone (são grandes e reconstruíveis). Sem eles, os scripts de
`experimentos/` não rodam:

```bash
uv run python -m fase2_sao_paulo.coleta.pull_dados    # única etapa que precisa de rede
uv run python -m fase2_sao_paulo.experimentos.monta
```

A fase 1 tem o equivalente em `fase1_nacional/coleta/pull_*.py` (também
precisam de rede; ver [fase1_nacional/README.md](fase1_nacional/README.md)).

## 5. Adicionar uma dependência nova

```bash
uv add nome-do-pacote
```

Isso atualiza `uv.lock` — **comite o `uv.lock` junto**, é ele que mantém todo
mundo com as mesmas versões.

## O deck (.pptx)

Os geradores do deck (`fase2_sao_paulo/docs/deck_gera.js`,
`fase2_sao_paulo/docs/deck_didatico.js`) rodam em Node, não em Python —
precisa instalar o Node.js uma vez por máquina:

| sistema | comando |
|---|---|
| Windows | `winget install OpenJS.NodeJS.LTS` |
| macOS | `brew install node` |
| Linux | `nvm install --lts` ([nvm](https://github.com/nvm-sh/nvm)) |

Feche e reabra o terminal depois. Confira com `node --version` (precisa de
Node 18+).

```bash
npm install              # instala o pptxgenjs em node_modules/ (uma vez)
npm run deck              # gera fase2_sao_paulo/docs/apresentacao_usb_usa_sp.pptx
npm run deck:didatico      # gera fase2_sao_paulo/docs/apresentacao_didatica_samu.pptx
```

## Problemas comuns

- **`uv` não é reconhecido** → feche e reabra o terminal.
- **No Windows, `python` abre a Microsoft Store** → ignore, use sempre
  `uv run python`.
- **`ModuleNotFoundError: No module named 'fase2_sao_paulo'`** → rode o
  comando a partir da **raiz do repositório**, com `-m` e sem `.py` no final
  (`python -m fase2_sao_paulo.experimentos.roda`, não
  `python fase2_sao_paulo/experimentos/roda.py`).
