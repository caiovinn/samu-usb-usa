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

```bash
uv run python sp/huff2sfca.py
uv run python sp/roda.py
uv run python tabelas.py
```

Sempre `uv run python arquivo.py` — não precisa ativar nada.

## 4. Buscar os dados (só na primeira vez)

`sp/_raw/` e `dados/sp_tempos.npy` não vêm no clone (são grandes e
reconstruíveis). Sem eles, `roda.py`, `compara.py` e `figuras.py` não rodam:

```bash
uv run python sp/pull_dados.py    # única etapa que precisa de rede
uv run python sp/monta.py
```

## 5. Adicionar uma dependência nova

```bash
uv add nome-do-pacote
```

Isso atualiza `uv.lock` — **comite o `uv.lock` junto**, é ele que mantém todo
mundo com as mesmas versões.

## O deck (.pptx)

```bash
npm install
npm run deck
```

## Problemas comuns

- **`uv` não é reconhecido** → feche e reabra o terminal.
- **No Windows, `python` abre a Microsoft Store** → ignore, use sempre
  `uv run python`.
