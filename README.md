# SAMU — realocação de frota USB/USA (MAI5003)

Projeto de estatística/otimização sobre a frota móvel de urgência do SAMU,
separando **Unidade de Suporte Básico (USB)** de **Unidade de Suporte
Avançado (USA)**. Duas fases, cada uma no seu próprio pacote:

| pasta | escopo | leia primeiro |
|---|---|---|
| [`fase1_nacional/`](fase1_nacional/README.md) | EDA da frota em todo o Brasil | [fase1_nacional/README.md](fase1_nacional/README.md) |
| [`fase2_sao_paulo/`](fase2_sao_paulo/README.md) | Huff + 2SFCA bi-objetivo, restrito ao município de São Paulo | [fase2_sao_paulo/README.md](fase2_sao_paulo/README.md) |

Dentro de cada fase, o código é separado por responsabilidade:
`coleta/` baixa dados brutos da internet, `modelo/` tem as funções
reutilizáveis (sem ler/escrever arquivo), `experimentos/` roda o pipeline e
grava em `dados/`/`figs/`, e `docs/` gera os relatórios e apresentações
finais a partir desses resultados.

## Documentos do projeto

- **[CONTEXTO_PROJETO.md](CONTEXTO_PROJETO.md)** — handoff completo: decisões
  de escopo, achados, armadilhas já corrigidas, próximos passos.
- **[SETUP.md](SETUP.md)** — como instalar e rodar em qualquer máquina do
  grupo (uv + Node, um comando cada).
- **[fase2_sao_paulo/docs/MODEL_GUIDE.md](fase2_sao_paulo/docs/MODEL_GUIDE.md)**
  — o modelo da fase 2 explicado em detalhe, em inglês.
- **[fase2_sao_paulo/docs/matematica_usb_usa.html](fase2_sao_paulo/docs/matematica_usb_usa.html)**
  — a matemática completa (Huff, 2SFCA, Gini, NSGA-II, p-median), em português.

## Ambiente

**Ver [SETUP.md](SETUP.md)** — é a única lista de dependências do projeto.
Resumo: `uv sync` na raiz instala tudo (Python 3.12 incluso); Node.js só é
necessário para gerar os decks `.pptx`.
