# How the SAMU relocation model works

A guide with the exact formula used in the code, a worked numeric example you can check by hand, and a link to where the technique comes from. No result in this document is invented:
every number is either in `CONTEXTO_PROJETO.md`, computed directly from the
code in `sp/`, or a fresh toy example built to match the real formulas.

## Table of contents

1. [The problem in one paragraph](#1-the-problem-in-one-paragraph)
2. [The execution pipeline](#2-the-execution-pipeline)
3. [The data](#3-the-data)
4. [Model 1 — Huff: how demand actually splits between stations](#4-model-1--huff-how-demand-actually-splits-between-stations)
5. [Model 2 — 2SFCA: turning choice probabilities into an accessibility score](#5-model-2--2sfca-turning-choice-probabilities-into-an-accessibility-score)
6. [The hierarchy: two ambulance types, two demand pools](#6-the-hierarchy-two-ambulance-types-two-demand-pools)
7. [The two objectives: expected time and Gini](#7-the-two-objectives-expected-time-and-gini)
8. [Why coverage numbers came out one specific way](#8-why-coverage-numbers-came-out-one-specific-way)
9. [The cost of relocating: an assignment problem](#9-the-cost-of-relocating-an-assignment-problem)
10. [Optimizer 1 — NSGA-II: searching two objectives at once](#10-optimizer-1--nsga-ii-searching-two-objectives-at-once)
11. [Optimizer 2 — p-median: the classical baseline](#11-optimizer-2--p-median-the-classical-baseline)
12. [Reading the results](#12-reading-the-results)
13. [Every parameter, in one table](#13-every-parameter-in-one-table)
14. [What's arbitrated, not estimated](#14-whats-arbitrated-not-estimated)
15. [Glossary](#15-glossary)
16. [Sources](#16-sources)

---

## 1. The problem in one paragraph

SAMU (Brazil's mobile emergency service) runs two kinds of ambulance: **USB**
(basic support — a driver and a nurse technician) and **USA** (advanced
support — adds a physician and a defibrillator, for the calls that need one).
A phase-1 national analysis (root of this repo) found that ambulance
*placement* — not the total count — is the problem: 40.6 million people have
a USB within 20 minutes and **zero** USA in that radius, and the fleet is far
more unequally spread for USA (Gini 0.67) than for USB (Gini 0.54, defined in
[§7](#7-the-two-objectives-expected-time-and-gini)). Phase 2, everything in
`sp/`, takes one city — São Paulo, 123 ambulances across 92 sites today — and
asks: *given the same 123 ambulances, where should they sit to respond faster
and more fairly?*

The one modeling decision that drives the whole project: instead of assuming
"every call goes to the nearest ambulance" (what almost all facility-location
literature assumes), it models *which* ambulance actually answers as a
**probability**, using the Huff model. Sections 4–5 are why that matters.

---

## 2. The execution pipeline

```
sp/pull_dados.py   ── network: census tracts, CNES facility registry, OSM road graph
        │             (only step that needs internet — writes to sp/_raw/, gitignored)
        ▼
sp/monta.py         ── builds the three files everything else reads:
        │               sp_setores.parquet     (26,889 census tracts: pop, location)
        │               sp_candidatos.parquet  (1,107 candidate sites: current fleet)
        │               sp_tempos.npy          (1,107 × 26,889 travel-time matrix, minutes)
        ▼
sp/roda.py          ── for each λ (change-cost price): runs NSGA-II, saves the
        │               Pareto front + its "knee" point to dados/sp_pareto_lam*.parquet
        ▼
sp/compara.py        sp/figuras.py        sp/deck_gera.js
   compares Huff        renders                builds the
   vs. the classic       figs/sp_*.png           .pptx deck
   p-median baseline
```

Every module in `sp/` also runs its own correctness test standalone
(`uv run python sp/huff2sfca.py`, etc. — see `SETUP.md`). That matters here
because several of the numbers below come straight from those tests.

---

## 3. The data

- **Demand** = 26,889 census tracts (`sp_setores.parquet`), each with a
  population count and a location. Demand is *residential population*, not
  call volume — see [§14](#14-whats-arbitrated-not-estimated).
- **Supply** = 1,107 candidate sites (`sp_candidatos.parquet`): every active,
  public health facility in São Paulo (UBS, UPA, hospitals, SAMU's own
  bases) that a unit could plausibly be assigned to. 92 of them currently
  host at least one ambulance.
- **Distance** = a 1,107 × 26,889 matrix of **travel time in minutes**
  (`sp_tempos.npy`), computed by Dijkstra's shortest path over the real
  OpenStreetMap road network for São Paulo — not straight-line distance. This
  is what makes the "20 minutes" in every metric below a real driving time,
  not a circle on a map.

---

## 4. Model 1 — Huff: how demand actually splits between stations

### The assumption everyone else makes, and why it's wrong here

The standard facility-location model (used by `p-median`, [§11](#11-optimizer-2--p-median-the-classical-baseline))
assumes every unit of demand goes to whichever facility is **closest**, full
stop — a hard, deterministic assignment. That's fine for something like
"which supermarket do I drive to," but for an ambulance dispatch it ignores a
basic operational fact: the nearest unit might already be on another call.
Someone still gets dispatched — from a station further away — with some
probability. The **Huff model** replaces "always nearest" with "probably
nearest, but sometimes not," and that's the entire point of using it here.

### The formula

For a census tract $i$ and a candidate site $j$, the probability that $i$'s
call gets answered by $j$ is:

$$
P(j \mid i) = \frac{S_j^{\alpha} \cdot f(t_{ij})}{\sum_{j'} S_{j'}^{\alpha} \cdot f(t_{ij'})}
$$

where $S_j$ is how many ambulances sit at site $j$ (its "attractiveness" —
capacity), $t_{ij}$ is the travel time in minutes, and $f$ is a distance-decay
function. This is a straight [Huff model](https://en.wikipedia.org/wiki/Huff_model)
(retail-location literature, 1960s) — the same structure a data scientist
knows as a **weighted softmax**: an un-normalized attractiveness score per
option, normalized to sum to 1 across all options available to $i$.

The code ([`sp/huff2sfca.py:33-36`](sp/huff2sfca.py#L33)) uses a **Gaussian**
decay instead of the power-law decay in Huff's original retail model:

$$
f(t) = \begin{cases} \exp\!\left(-\dfrac{t^2}{2\beta^2}\right) & t \le D_0 \\ 0 & t > D_0 \end{cases}
$$

If you've used an RBF kernel (in an SVM, in Gaussian processes, in kernel
density estimation) this is exactly that kernel, applied to travel time
instead of feature distance: $\beta$ sets how quickly the weight collapses
with distance (like an RBF kernel's bandwidth $\gamma = 1/(2\beta^2)$), and
$D_0$ is a hard cutoff — beyond it, a site contributes nothing, on the
reasoning that a unit 30+ minutes away is never really "in the running" for a
given call.

$\alpha$ (default 1.0) makes attractiveness scale linearly with capacity: a
site with 2 ambulances is twice as attractive as one with 1. $\alpha > 1$
would make bigger sites *disproportionately* more attractive (an
economies-of-scale effect, the kind that matters for shopping malls in Huff's
original use case). It's currently inert here because 86 of the 92 occupied
sites in São Paulo host just 1–2 ambulances — see [§14](#14-whats-arbitrated-not-estimated).

### Worked example

Two candidate sites, A and B, one ambulance each ($S_A = S_B = 1$). One
tract, travel times $t_{iA} = 5$ min, $t_{iB} = 10$ min. Using the project's
default $\beta = 4.5$:

$$f(5) = \exp\!\left(-\frac{25}{2 \cdot 4.5^2}\right) = \exp(-0.617) = 0.540$$
$$f(10) = \exp\!\left(-\frac{100}{2 \cdot 4.5^2}\right) = \exp(-2.469) = 0.085$$

$$P(A \mid i) = \frac{0.540}{0.540 + 0.085} = 0.864 \qquad P(B \mid i) = \frac{0.085}{0.540+0.085} = 0.136$$

So the closer station answers about 86% of the time, the farther one 14% —
not the 100/0 split a nearest-facility rule would give. This spread is
exactly what a queueing system with real ambulances looks like: sometimes the
closest one is busy.

### Orphans

If a tract has *no* site within $D_0=30$ min (rare, but possible at the edges
of the coverage area), the sum in the denominator is 0 and the formula breaks
down. The code catches this and force-assigns that tract to its single
nearest site with probability 1
([`sp/huff2sfca.py:61-67`](sp/huff2sfca.py#L61-L67)) — the Huff model quietly
falls back to the classic rule exactly where it has to.

---

## 5. Model 2 — 2SFCA: turning choice probabilities into an accessibility score

Knowing *who answers whom* isn't the same as knowing *how well-served* each
tract is — a tract might be answered mostly by a station that is itself
overloaded by everyone else. **2SFCA** (Two-Step Floating Catchment Area,
[Luo & Wang 2003](https://doi.org/10.1068/b29120)) fixes that by running the
Huff probabilities through capacity twice: once to measure how loaded each
site is, once to measure how much of that (now-scarce) capacity actually
reaches each tract.

### Step 1 — how loaded is each site?

Every tract sends some expected demand to site $j$ — its population times the
probability it goes to $j$. Summed over all tracts, that's the **pressure**
on $j$:

$$\text{pressure}_j = \sum_i P(j \mid i) \cdot \text{pop}_i$$

Site $j$'s **supply ratio** is then how many ambulances it has per unit of
pressure:

$$R_j = \frac{S_j}{\text{pressure}_j}$$

A site fielding a lot of expected demand relative to its capacity gets a low
$R_j$ — it's stretched thin.

### Step 2 — how much of that reaches each tract?

A tract's accessibility is the demand-weighted average of the ratios of every
site it might be sent to:

$$A_i = \sum_j P(j \mid i) \cdot R_j$$

$A_i$ has units of "ambulances per resident" — small numbers, but directly
comparable across tracts.

### Worked example (continuing §4, now with a second tract)

Two sites (A, B, one unit each), two tracts. Tract 1: pop 1,000,
$t_{1A}=5,\ t_{1B}=10$ (same as before: $P(A\mid1)=0.864,\ P(B\mid1)=0.136$).
Tract 2: pop 2,000, $t_{2A}=15,\ t_{2B}=5$, which by the same formula gives
$P(A\mid2)=0.007,\ P(B\mid2)=0.993$.

**Step 1 — pressure:**
$$\text{pressure}_A = 0.864{\times}1000 + 0.007{\times}2000 = 878.7$$
$$\text{pressure}_B = 0.136{\times}1000 + 0.993{\times}2000 = 2121.1$$

(Notice $878.7 + 2121.1 = 3000$ — the total population. The Huff
probabilities *partition* demand; nothing is created or lost.)

$$R_A = \frac{1}{878.7} = 0.001138 \qquad R_B = \frac{1}{2121.1} = 0.000471$$

**Step 2 — accessibility:**
$$A_1 = 0.864{\times}0.001138 + 0.136{\times}0.000471 = 0.001048$$
$$A_2 = 0.007{\times}0.001138 + 0.993{\times}0.000471 = 0.000476$$

Tract 1 gets about **2.2× the ambulances-per-resident** of tract 2, even
though both tracts are 1,107 sites away from the same two-station system —
purely a function of who else is competing for the same stations.

### The conservation identity — and why it matters for picking objectives

Check: $1000 \times 0.001048 + 2000 \times 0.000476 = 1.048 + 0.952 = 2.000$
— exactly the total capacity ($S_A + S_B = 2$). **This is not a coincidence
of the toy numbers; it's a mathematical identity of 2SFCA**: population-weighted
accessibility always sums to total capacity, no matter how the ambulances are
placed. The code checks it explicitly
([`sp/huff2sfca.py:169`](sp/huff2sfca.py#L169), `np.isclose((A * pop * THETA).sum(), n_usa)`).

The practical consequence: **"maximize total accessibility" is a useless
objective** — it's a constant, unaffected by placement. That's why the
project optimizes *time* and *inequality (Gini)* instead of accessibility
itself — see [§7](#7-the-two-objectives-expected-time-and-gini).

---

## 6. The hierarchy: two ambulance types, two demand pools

USA is scarce and clinically necessary for severe calls; USB can't substitute
for it. The model splits every tract's population into two virtual pools
before running Huff+2SFCA on each:

- **Advanced pool** = $\theta \cdot \text{pop}_i$ — only USA sites are
  candidates.
- **Basic pool** = $(1-\theta) \cdot \text{pop}_i$ — both USB and USA sites
  are candidates (a USA can answer a basic call if it's free).

$\theta = 0.10$: one call in ten is assumed to need advanced support. This
runs Huff+2SFCA **twice** with different candidate sets and different demand
weights ([`sp/huff2sfca.py:109-151`](sp/huff2sfca.py#L109-L151)), producing
two separate accessibility surfaces, $A^{av}$ and $A^{ba}$.

---

## 7. The two objectives: expected time and Gini

### Objective 1 — expected response time

For each tract, $E[T_i] = \sum_j P(j\mid i) \cdot t_{ij}$ — literally the
expected value of a discrete random variable: "time to whichever unit
responds," under the Huff distribution. (§4's worked example already computed
this per-station; summing $P \times t$ over all $j$ gives the tract's single
expected value: $0.864{\times}5 + 0.136{\times}10 = 5.68$ min for tract 1.)

The reported project-wide number combines both pools by the law of total
expectation:

$$E[T] = \theta \cdot \overline{E[T^{av}]} + (1-\theta) \cdot \overline{E[T^{ba}]}$$

where each bar is a population-weighted average across all 26,889 tracts.
This is `f_tempo` in the code and in every results table.

### Objective 2 — the Gini coefficient of advanced accessibility

**Gini in one sentence, if you've never used it:** it's a single number
between 0 (everyone has exactly the same amount of something) and 1 (one
person/place has all of it, everyone else has none). It's the standard
economics measure of income inequality — [Wikipedia](https://en.wikipedia.org/wiki/Gini_coefficient) —
applied here to *ambulance accessibility per resident* instead of income.

**Where it comes from — the Lorenz curve.** Sort tracts from
worst-served to best-served, and plot cumulative share of accessibility
against cumulative share of population. If accessibility were perfectly
equal, that plot would be the diagonal line (the bottom 20% of the
population would hold exactly 20% of accessibility, etc.). Real data sags
below the diagonal — the "worst 20% of tracts" hold less than 20% of the
accessibility. **The Gini coefficient is twice the area between the diagonal
and that sagging curve.**

$$
G = 1 - \sum_{k} (cw_{k+1} - cw_k)(cx_{k+1} + cx_k)
$$

where $cw_k$ is cumulative population share and $cx_k$ is cumulative
accessibility share, both starting at $(0,0)$ — that's a trapezoidal-rule
estimate of the area under the Lorenz curve, doubled and subtracted from 1
([`sp/huff2sfca.py:92-115`](sp/huff2sfca.py#L92-L115)).

**Worked example, continuing §5:** tract 2 is worse-served (accessibility
0.000476) than tract 1 (0.001048), so it sorts first.

| | cum. pop share ($cw$) | cum. access. share ($cx$) |
|---|---|---|
| origin | 0 | 0 |
| after tract 2 (pop 2000) | 0.667 | 0.476 |
| after tract 1 (pop 1000) | 1.000 | 1.000 |

$$G = 1 - \big[(0.667{-}0)(0.476{+}0) + (1{-}0.667)(1{+}0.476)\big] = 1 - 0.809 = 0.191$$

(Run against the actual code: $G = 0.1905$ — the two-decimal hand calculation
above rounds to the same figure.)

A Gini of ~0.19 for a two-tract toy system with a 2.2:1 accessibility ratio.
For comparison, São Paulo's *actual* USA accessibility Gini today is
**0.224** — a real, city-wide, 26,889-tract version of the same calculation,
on the same scale.

> **A bug that lived here, now fixed:** the trapezoid sum above must start
> from the origin $(0,0)$. The code originally omitted that first segment, so
> a *perfectly equal* distribution (which should score exactly 0) instead
> scored a small positive number whose size depended on which tract the
> sorting happened to place first — undefined tie-breaking, not a real
> effect. It was caught by the module's own self-test failing after a numpy
> upgrade. The bias was of order $1/n^2$ — about $10^{-9}$ on 26,889 tracts
> — so **no published Gini number in this project changes**; it only ever
> affected the degenerate all-equal test case. Fixed in
> [`sp/huff2sfca.py`](sp/huff2sfca.py), logged in `CONTEXTO_PROJETO.md` §10.

### Why *this* Gini, specifically

The code reports Gini of **advanced** accessibility ($A^{av}$) only, not
basic ($A^{ba}$, still computed and reported as `gini_basico`, just not
optimized). That follows directly from the phase-1 finding that motivated
this whole project: the *advanced* fleet is the unequally distributed one
(national Gini 0.67 vs. 0.54 for basic) and the one with the 40.6-million-person
gap. Optimizing basic-support equity too would dilute the objective toward a
problem that's comparatively already solved.

### Why two objectives, and not one

Section 5 showed accessibility is conserved — you can't optimize it, only
redistribute it, so "maximize accessibility" is degenerate. The flip side:
Gini alone is trivially minimized by parking every ambulance at one point —
that makes accessibility *identical* everywhere (Gini → 0) at the cost of
enormous response times everywhere except that one point (the project's own
test confirms this: `sp/huff2sfca.py`'s `_teste()` checks that concentrating
the fleet worsens `f_tempo` while driving `f_gini` to ~0). Time and Gini each
have a trivial, useless optimum on their own; only optimizing *both together*
— which is what [§10](#10-optimizer-1--nsga-ii-searching-two-objectives-at-once)'s
Pareto front does — produces a meaningful trade-off.

---

## 8. Why coverage numbers came out one specific way

You'll see a number like "98.24% of the population has USA coverage within
20 minutes." Two different things could be meant by that, and the project
currently reports one of them (a second, complementary definition is planned
— see `CONTEXTO_PROJETO.md` §7.0):

- **Huff-expected coverage** (what's reported today,
  [`sp/huff2sfca.py:147`](sp/huff2sfca.py#L147)): the share of population
  whose *expected* time $E[T_i]$ (§7) is ≤ 20 min. This asks "on average,
  accounting for the chance the nearest unit is busy, is this tract well
  served?"
- **Nearest-unit coverage** ([`sp/compara.py:33`](sp/compara.py#L33), used
  only in the classical-baseline comparison): the share whose *closest*
  unit is ≤ 20 min. This is the definition used in the classic
  location-coverage literature (e.g. the Maximum Covering Location Problem).

At 20 minutes the two nearly agree in São Paulo, because the city is dense
enough that the nearest unit dominates the Huff distribution almost
everywhere. They diverge sharply at shorter thresholds (5–10 min), which is
exactly why a τ-sweep at those thresholds is on the project's near-term
to-do list.

---

## 9. The cost of relocating: an assignment problem

Moving 12 ambulances isn't free, and "12 units moved" doesn't say whether
each one drove around the corner or across the city. The project prices
relocation in **kilometers of actual displacement**, computed as an
**optimal assignment problem**: match each old position to a new position
such that the *total* distance moved is minimized.

This is the [assignment problem](https://en.wikipedia.org/wiki/Assignment_problem)
— exactly the bipartite matching problem you'd recognize from optimal
transport — solved exactly by the
[**Hungarian algorithm**](https://en.wikipedia.org/wiki/Hungarian_algorithm)
(`scipy.optimize.linear_sum_assignment`,
[`sp/mudanca.py:60-72`](sp/mudanca.py#L60-L72)). Ambulances of the same
modality are interchangeable, so it doesn't matter *which* USB ends up
where — only the total kilometers moved to realize the new configuration.
Before matching, any units that are already at the same site in both the old
and new configuration are canceled out (a multiset intersection), which
guarantees the identical configuration costs exactly 0 km and prevents the
optimizer from being "charged" for two units at the same site trading places
with each other on paper.

A naive greedy version (repeatedly pick the closest unmatched pair) was
tried and measured against the optimal one: it costs 9% more on average,
*always* on the worse side of optimal (never better, as guaranteed by the
theory) — [`sp/mudanca.py:111-154`](sp/mudanca.py#L111-L154)'s self-test
checks this explicitly across problem sizes. The Hungarian solve turned out
cheap enough (0.27 ms per call on a 100×100 problem) to just use directly
inside the optimizer's inner loop rather than settle for the approximation.

### Turning kilometers into the same units as minutes

The optimizer needs to trade off *response time* against *change cost* on
one scale. $\lambda$ (lambda) is the exchange rate: minutes of penalty per
km moved, per unit:

$$f_{\text{obj}} = E[T] + \lambda \cdot \frac{\text{km}_{\text{total}}}{p}$$

where $p=123$ is fleet size. At $\lambda=0$, relocation is free (a full
redesign); at $\lambda=1$, every km moved "costs" as much as a full minute of
extra response time spread across the fleet, which in practice freezes the
network almost in place. The project sweeps $\lambda \in \{0, 0.01, 0.03, 0.1,
0.3, 1\}$ and reports, for each, what response-time and Gini improvement that
price of change buys — the headline result (12 units, 39 km, 62% of the Gini
gain) comes from reading that curve, not from a single run.

---

## 10. Optimizer 1 — NSGA-II: searching two objectives at once

### Why not just run "minimize E[T] + minimize Gini" as one number?

Because there's no single correct exchange rate between minutes of response
time and points of Gini — that's a value judgment, not a technical one. The
standard approach when two objectives genuinely trade off is
**multi-objective optimization**: instead of one best answer, produce the
whole **Pareto front** — every configuration where you cannot improve one
objective without worsening the other — and let a human pick a point on it.
[**NSGA-II**](https://doi.org/10.1109/4235.996017) (Deb et al., 2002) is the
standard genetic algorithm for exactly this, and it's what
[`sp/otimiza.py`](sp/otimiza.py) implements from scratch (~150 lines, no
external solver dependency).

### The encoding

A candidate solution is a vector of length $p=123$ (107 USB slots + 16 USA
slots), where each entry is the ID of the candidate site hosting that unit.
Repeats are allowed (multiple ambulances, same site) — this is how "capacity
per site" gets represented without a separate variable.

### The core mechanics (standard NSGA-II, briefly)

- **Non-dominated sorting** ([`fronteiras()`](sp/otimiza.py#L19)): solutions
  are grouped into fronts — front 0 is every solution not beaten on *both*
  objectives simultaneously by any other solution, front 1 is the next-best
  layer, and so on.
- **Crowding distance** ([`aglomeracao()`](sp/otimiza.py#L43)): within a
  front, measures how close a solution's neighbors are in objective space.
  Boundary solutions (extreme time, extreme Gini) always get infinite
  distance and are kept; this is the mechanism that spreads the final front
  across the trade-off instead of collapsing to one region of it.
- **Selection**: binary tournament by (front rank, then crowding distance) —
  better front wins; on a tie, less-crowded wins (preserves diversity).
- **Variation**: uniform crossover (each gene independently comes from
  parent A or B) plus mutation. Mutation has a domain-specific twist: 70% of
  mutated genes jump to one of the site's 12 geographic nearest neighbors
  (a *local* move), 30% jump anywhere valid (a *long* move) —
  [`sp/otimiza.py:129-137`](sp/otimiza.py#L129-L137). This biases search
  toward small, plausible relocations, which is also what the $\lambda$
  penalty in §9 is pushing toward.
- **Survival**: parents + offspring merged (μ+λ elitism), re-sorted into
  fronts, and the population is filled front-by-front; the front that would
  overflow the population size is trimmed by crowding distance, not
  randomly.

### The knee point

The Pareto front has dozens of points; the project needs to report *one*
recommended configuration per $\lambda$. It picks the **knee**: normalize
both objectives to [0,1] by their observed range in this run, then take the
point closest to the ideal corner (0,0) — [`joelho()`](sp/otimiza.py#L58-L68).
This is the same idea behind
[compromise programming / TOPSIS](https://en.wikipedia.org/wiki/TOPSIS):
pick the point nearest the (unreachable) best-of-both-worlds. A comment in
the code (and `CONTEXTO_PROJETO.md` §10) records that this project once had
*two* different knee definitions live at once, and they disagreed — the map
figure showed 16 arrows for a configuration the summary table said had 12
relocations. There is now exactly one function, imported everywhere a knee
is needed.

### Two things that measurably mattered

1. **Seeding.** The initial population isn't random — it includes the
   *current* fleet configuration and the p-median solution (§11), plus small
   mutations of each. Without this, NSGA-II actually lost to the classical
   p-median heuristic on the time objective (6.77 vs. 6.70 min); with it,
   6.64 min — better than both starting points.
2. **The row-major travel-time matrix.** Not a modeling choice, but worth
   knowing: the time matrix is stored candidates-in-rows because the
   optimizer only ever needs a handful of rows (the occupied sites) per
   evaluation, and row-slicing a contiguous array is ~13× faster than
   column-slicing the same data (2.6 ms vs. 34 ms) — this is what makes
   thousands of generations tractable at all.

### Runtime mechanics (not math, but load-bearing)

Each $\lambda$ run has a wall-clock budget (`ORCAMENTO = 420` s); if it runs
out mid-search, the whole population state is checkpointed to a `.npz` file
and the run resumes from there next time it's invoked, rather than
restarting — necessary because this ran inside sandboxed shells with their
own per-call time limits.

---

## 11. Optimizer 2 — p-median: the classical baseline

The [**p-median problem**](https://en.wikipedia.org/wiki/P-median_problem)
(ReVelle & Swain, 1970) is *the* textbook facility-location model: choose $p$
sites to minimize the population-weighted average distance to each person's
**nearest** open facility. It's what almost every real-world facility
placement is planned against, and it's the model this project argues is
missing something (§4). It matters here as the honest baseline: if Huff+2SFCA
can't beat it, the added complexity isn't earning its keep.

It's NP-hard, so [`sp/pmedian.py`](sp/pmedian.py) solves it heuristically in
two stages:

1. **Greedy construction**: add sites one at a time, always picking whichever
   candidate most reduces the total weighted distance so far — vectorized to
   evaluate all 1,107 candidates against the full tract set simultaneously
   per step.
2. **Vertex substitution** ([Teitz & Bart, 1968](https://doi.org/10.1287/opre.16.5.955),
   a local-search interchange heuristic): repeatedly try swapping each
   currently-selected site for every *unselected* one; keep any swap that
   improves the total cost; repeat until a full pass makes no improvement.

Checked against true optimal on a small brute-force-solvable instance ($p=3$):
the heuristic lands **1.15% above the exact optimum** — close enough to trust
on the full 123-site problem, where exact solving isn't feasible.

---

## 12. Reading the results

All from `CONTEXTO_PROJETO.md`, computed by the pipeline above on the current
São Paulo fleet (107 USB + 16 USA, 92 sites):

| configuration | $E[T]$ (min) | Gini (USA) | relocated | km moved |
|---|---|---|---|---|
| today | 7.435 | 0.224 | — | — |
| free redesign ($\lambda{=}0$) | 6.640 | 0.031 | 115 | 385 |
| **recommended ($\lambda{=}0.1$)** | 6.669 | **0.025** | **12*** | **39*** |
| frozen ($\lambda{=}1$) | 7.297 | 0.085 | 12 | 39 |
| classical p-median | 6.696 | 0.079 | — | 373 |

*(the $\lambda{=}0.1$ row's own moved/km figures are in the same table as
$\lambda{=}1$ in the source — both land near "12 units, 39 km" per
`CONTEXTO_PROJETO.md` §5; see that file for the exact per-λ breakdown.)*

**The one-sentence finding:** Huff's probabilistic demand model barely
changes the time objective versus planning with the classical nearest-unit
rule (+0.4%) — the p-median baseline is robust to that assumption. What it
*does* reveal, because p-median has no notion of capacity at all, is
inequality: **3.1× lower Gini, for less relocation.** The paper's claim is
about equity, not speed — and the p-median comparison in §11 is precisely
what makes that claim defensible rather than asserted.

---

## 13. Every parameter, in one table

| parameter | value | what it controls | where |
|---|---|---|---|
| $\beta$ | 4.5 min | Gaussian decay width in Huff — governs how many "effective" nearby units a tract draws from (~2.2 at this value) | `huff2sfca.BETA` |
| $\alpha$ | 1.0 | how superlinearly capacity drives attractiveness in Huff | `huff2sfca.ALFA` |
| $D_0$ | 30 min | hard cutoff — sites beyond this contribute zero weight | `huff2sfca.D0` |
| $\theta$ | 0.10 | fraction of calls assumed to need USA | `huff2sfca.THETA` |
| $\lambda$ | swept: 0, 0.01, 0.03, 0.1, 0.3, 1 | minutes of penalty per km of relocation, per unit | `roda.LAMBDAS` |
| population size | 80 | NSGA-II candidates per generation | `roda.N_POP` |
| generations | 150 | NSGA-II iterations | `roda.N_GER` |
| max per site | 10 | capacity constraint during search | `roda.CAP_MAX` |
| neighbor count | 12 | candidates considered "local" for mutation | `roda.K_VIZ` |
| time budget | 420 s | per-$\lambda$ wall-clock budget before checkpoint | `roda.ORCAMENTO` |

---

## 14. What's arbitrated, not estimated

Two parameters are the honest weak points, both already logged in
`CONTEXTO_PROJETO.md` §6, worth understanding *why* they're weak rather than
just that they are:

- **$\beta$ is chosen, not fit to data.** There's no dataset of "which
  ambulance actually responded to which call" to estimate a real distance-decay
  curve from — so 4.5 min was picked by *reasoning* about dispatch behavior
  (it produces ~2.2 effective nearby units per tract, matching an intuition
  of "the closest one, or the next one if that's busy") rather than by
  fitting a likelihood to observed choices. A parameter sweep
  ($\beta \in \{1.5, 4.5, 8.5, 12\}$) shows it moves $E[T]$ and Gini in
  *opposite* directions — meaning the paper's conclusions are conditioned on
  this choice, not independent of it. Published methodology exists for
  calibrating exactly this kind of decay against real dispatch data (see
  [§16](#16-sources), the Handan City GP2SFCA study) — the gap here is data,
  not method.
- **$\alpha$ is inert, so it's untested by the current fleet.** Going from
  $\alpha{=}1$ to $\alpha{=}2$ moves $E[T]$ by 0.02 minutes — negligible,
  because 86 of 92 occupied sites host only 1–2 units today, so the
  exponent has almost nothing to act on. It would start to matter if the
  optimizer ever concentrated many units at one site.
- **$\theta = 0.10$** (the severity mix) is also asserted rather than
  measured from São Paulo's actual call log.
- **Demand = resident population**, not call volume — no age profile, no
  time-of-day variation, no incidence data. A stated next step is replacing
  this with a Bayesian incidence model (`CONTEXTO_PROJETO.md` §7.2).

---

## 15. Glossary

| term | plain meaning |
|---|---|
| USB / USA | Basic / Advanced ambulance support — only USA carries a physician and defibrillator |
| Huff model | probability that a customer/call goes to option $j$, proportional to attractiveness over distance-decay |
| 2SFCA | accessibility index that accounts for how many *other* people are competing for the same facility |
| Gini coefficient | 0–1 inequality measure; 0 = everyone equal, 1 = one place has everything |
| Lorenz curve | the cumulative-share plot the Gini coefficient is the area-deficit of |
| Pareto front | the set of solutions where improving one objective necessarily worsens another |
| NSGA-II | the genetic algorithm used to search that front for two objectives at once |
| knee point | the front point closest to the (unreachable) best-of-both-objectives corner |
| p-median | classical facility-location model: minimize average distance to the *nearest* open facility |
| Hungarian algorithm | exact solver for "match these to those at minimum total cost" |
| $\lambda$ | the price, in minutes, of moving one ambulance one kilometer |
| $\beta$ | how fast Huff's preference for a site decays with travel time |
| $\theta$ | fraction of demand assumed to require advanced support |

---

## 16. Sources

- Huff, D.L. (1964). *Defining and Estimating a Trading Area*. Journal of
  Marketing. Overview: [Wikipedia — Huff model](https://en.wikipedia.org/wiki/Huff_model)
- Luo, W., & Wang, F. (2003). *Measures of spatial accessibility to health
  care in a GIS environment*. Environment and Planning B, 30(6).
  [doi:10.1068/b29120](https://doi.org/10.1068/b29120) — the original 2SFCA paper.
- Luo, W., & Qi, Y. (2009). *An enhanced two-step floating catchment area
  (E2SFCA) method for measuring spatial accessibility to primary care
  physicians*. Health & Place, 15(4). — the distance-decay-weighted variant
  this project's `acessibilidade()` follows.
- Gini coefficient / Lorenz curve: [Wikipedia](https://en.wikipedia.org/wiki/Gini_coefficient)
- Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). *A fast and
  elitist multiobjective genetic algorithm: NSGA-II*. IEEE Transactions on
  Evolutionary Computation, 6(2).
  [doi:10.1109/4235.996017](https://doi.org/10.1109/4235.996017)
- Knee-point selection in Pareto fronts: Branke, J. et al. (2004). *Finding
  Knees in Multi-objective Optimization*. PPSN VIII. Background on the
  general idea: [Wikipedia — TOPSIS](https://en.wikipedia.org/wiki/TOPSIS)
- ReVelle, C.S., & Swain, R.W. (1970). *Central facilities location*.
  Geographical Analysis, 2(1). — the original p-median formulation.
  Overview: [Wikipedia — p-median problem](https://en.wikipedia.org/wiki/P-median_problem)
- Teitz, M.B., & Bart, P. (1968). *Heuristic methods for estimating the
  generalized vertex median of a weighted graph*. Operations Research, 16(5).
  [doi:10.1287/opre.16.5.955](https://doi.org/10.1287/opre.16.5.955)
- Assignment problem / Hungarian algorithm:
  [Wikipedia](https://en.wikipedia.org/wiki/Hungarian_algorithm); Kuhn, H.W.
  (1955). *The Hungarian method for the assignment problem*. Naval Research
  Logistics Quarterly, 2(1–2).
- Haversine formula (used for the relocation-distance matrix, `mudanca.py`):
  [Wikipedia](https://en.wikipedia.org/wiki/Haversine_formula)
- Dijkstra's algorithm (used for the real road-network travel-time matrix,
  `monta.py`): [Wikipedia](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- OSMnx (the OpenStreetMap road-network toolkit `pull_dados.py` uses):
  [osmnx.readthedocs.io](https://osmnx.readthedocs.io/)
- A recent (2025) real-world validation of Gaussian-decay 2SFCA specifically
  for **prehospital EMS**, including a calibration protocol against observed
  station choice — directly relevant to the $\beta$ gap in §14: *Spatial
  analysis of prehospital emergency medical services accessibility: a
  comparative evaluation of the GAUSS-probability two-step floating
  catchment area model in Handan City*, Frontiers in Public Health (2025).
  [PMC11986854](https://pmc.ncbi.nlm.nih.gov/articles/PMC11986854/)
- The bi-objective Huff+2SFCA framework this project's technique 2 is built
  on (fresh-produce distribution centers, not healthcare — see
  `CONTEXTO_PROJETO.md` §2): *Balancing efficiency and accessibility in
  location–allocation study for multi-mode fresh produce front distribution
  centre*, Engineering Optimization (2025).
  [doi:10.1080/0305215X.2025.2583216](https://www.tandfonline.com/doi/full/10.1080/0305215X.2025.2583216)
