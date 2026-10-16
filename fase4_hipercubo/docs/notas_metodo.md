# Fase 4 — notas de método (hipercubo de Larson)

## O que foi lido e o que não foi

- **Lido por inteiro (texto e exemplo):** Larson, R. C. (1975), *Approximating the Performance of
  Urban Emergency Service Systems*, Operations Research 23(5):845–868,
  doi:10.1287/opre.23.5.845 (PDF fornecido pelo usuário; páginas 846–864 lidas,
  seções 1–6; as tabelas de resultados adicionais das últimas páginas não foram lidas).
- **Metadados conferidos (Crossref/OpenAlex), texto NÃO lido:** Larson (1974), Computers & Operations
  Research 1(1):67–95, doi:10.1016/0305-0548(74)90076-8; Jarvis (1985), Management Science,
  doi:10.1287/mnsc.31.2.235; Batta, Dolan & Krishnamurthy (1989), Transportation Science,
  doi:10.1287/trsc.23.4.277; Budge, Ingolfsson & Erkut (2009), Operations Research 57:251–255,
  doi:10.1287/opre.1080.0591.
- Consequência: **a extensão de Budge et al. (serviço específico por local, várias unidades por
  local) não está implementada como no artigo.** O que fazemos com `mu` por unidade e várias
  unidades por local é nosso e está marcado como tal.

## Modelo exato (Larson 1974/1975)

Região em átomos (aqui, zonas de 1 km) que geram chamados Poisson, N unidades, serviço
exponencial. Estado = quais unidades estão ocupadas (2^N). Despacho de preferência fixa por
átomo: a unidade livre mais bem colocada na lista atende. Equações de equilíbrio resolvidas por
`scipy.sparse` em `modelo/hipercubo_exato.py` (sistema de perda; até ~20 unidades).

**Teste independente (publicado):** o exemplo de 3 unidades do artigo (pp. 861–864; λ = 1,2,
sistema de perda, ocupações exatas do hipercubo 0,3548 / 0,3650 / 0,3724) é reproduzido pelo
nosso solver exato (tolerância 1e-4) e pela aproximação (0,351 / 0,367 / 0,374 do artigo; erro máx.
reproduzido < 1,5e-3). Os valores Q'(3; 0,4; 1) = 0,862 e Q'(3; 0,4; 2) = 0,887 também.

## Aproximação (seções 2–3 do artigo)

Para a unidade que é a (j+1)-ésima da lista e j anteriores ocupadas:

    P{B1...Bj F(j+1)} ≈ Q(N, ρ, j) · ρ_n1 ... ρ_nj · (1 − ρ_n(j+1))                (eq. 4, 20, 22)

`Q` corrige a independência: Q = 1 é a ocupação independente (a das fases 2b e 3). Para o sistema
de perda M/M/N/0 vale `Q'` (eqs. 14–16), com ρ = λ/(Nμ) global e P_N' = Erlang B(N, a).
Ponto fixo nas ocupações (eq. 21 com λ_D = 0): 1 − ρ_i = [1 + Σ_k Σ_{j∈G_i^k} λ_j Q'(N,ρ,k−1) Π ρ ... ]^−1,
com normalização de Larson (passo 2: Σρ_i = N·r, r = ρ(1 − P_N')). Implementado em
`hipercubo_aprox.aprox_larson75` (instâncias pequenas) e `hc_real.ocupacoes` (SP, 123 unidades).

**Generalizações nossas (não são do artigo):** μ por unidade (ρ_i = R_i/(μ_i+R_i)); listas
parciais (grave só com USA; basico USB depois USA); fator `local` (`fator_q`), deduzido por nós
via Erlang sobre o conjunto elegível. Ambos testados contra o hipercubo exato (`valida_exato.py`).

## Hipóteses e onde a simulação as viola

| Hipótese do hipercubo | Simulação (fase 3) |
|---|---|
| serviço exponencial, média 1/μ por classe, independente do local | Gamma(2), mesma média (inclui o deslocamento) |
| sistema de perda (sem fila) | fila implícita; ocorre em ~0% dos chamados (v5) |
| taxa por átomo = total × população | idem (não há taxa por zona nos dados) |
| ordem de preferência fixa por átomo (ordem do tempo) | idem |
| PCR traçadora é um observador (não gera carga) | idem; no hipercubo, observador PASTA |

Truncagem: listas com as 12 USB e 16 USA mais próximas (a massa restante, ~ρ^12, vai para a
última da lista; é o oposto da fase 3, que a manda para a mais próxima).

## Extensão: serviço dependente do deslocamento (nossa)

Na simulação da fase 3 o tempo ocupado = deslocamento real + resto Gamma, então unidades que
atendem mais longe ficam mais ocupadas (ocupação simulada das USA 0,22–0,24 contra 0,21 no
hipercubo de μ fixo). Opção `servico_ida=True` em `hc_real.avalia`: μ_u = 60 / (s_min + ida média
de u − ida nominal), iterado no ponto fixo, sem a normalização de Larson. Padrão desligado.
Inspirada na ideia de serviço por local de Budge et al. (2009), **artigo não lido**; a formulação é
nossa. Efeito (39 casos): erro médio da cobertura grave 0,87 → 0,13 pp e do tempo grave 0,53 →
0,27 min; vidas 0,29 → 0,24, com viés +0,24. A busca local NÃO usa esta opção.

## Onde estão os resultados

`docs/relatorio_hipercubo.html` (gerado por `docs/relatorio_gera.py` a partir de `dados/fase4/*.json`).
