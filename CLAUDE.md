# Working guidelines

Guidelines for AI assistants working in this repository.
Keep this file short: edit or delete rules, don't just append.

## Boundaries

**Always**
- Read the relevant code and docs before proposing changes; reuse what exists.
- Run the project's tests or self-checks after changing code; report failures verbatim.
- Keep published results reproducible: new behaviour goes behind an option, the
  old default stays, and a known reference number is re-checked after the change.

**Ask first**
- Commits, pushes, PRs. Never commit before the user has reviewed the changes.
- Installing software, changing global config, deleting or overwriting data/results.
- Long or expensive runs (more than ~15 min): state the design and the cost, and
  ask at the one decision that would change what the run produces.
- Anything that changes a project's conclusions or framing: objective functions,
  metrics, the main claim.

**Never**
- Invent numbers, citations, DOIs, authors or results. If unverified, say so.
- Modify raw data. Derived data goes to separate, regenerable files.
- Change a definition (formula, metric, parameter) in one place only. Fix every
  place that uses it (code, docs, slides) or flag the inconsistency.
- Touch files with uncommitted changes you didn't make; mention them instead.

## Scientific rigor
- Separate what is measured, estimated and assumed. Give assumptions as
  low / central / high ranges, not single values.
- Prefer parameters with a physical meaning that can be estimated from data.
  Arbitrary parameters get a sensitivity analysis.
- Validate models against something independent: a simulation, an exact solution
  on a small instance, known limiting cases. Encode invariants and limits as asserts.
- Compare against a strong classical baseline before claiming an improvement.
- Stochastic methods: run several seeds and report ranges, not a single run.
- Sanity-check data before using it: totals against an external source, outliers,
  units. Record every anomaly and how it was handled.
- Report inconvenient findings as prominently as convenient ones; don't oversell.
- One source of truth for numbers: documents and slides read result files;
  numbers are never typed by hand.

## Literature and sources
- Verify every reference: the DOI resolves and title, authors and year match
  (Crossref or OpenAlex).
- Claims come only from text actually read (abstract or full text). Say so when
  only a short summary was available.
- When web information is used, list the sources with links.

## Computation
- Heavy work runs locally in the background, logging to files. Scripts print a
  short summary and write small JSON outputs; read those, not raw data or full logs.
- Long pipelines are restartable (skip finished steps, checkpoints) and parallel
  where independent, with one BLAS thread per worker process.
- Smoke-test with a tiny budget before launching a long run.
- Don't poll; wait for the completion notification.
- Measure the bottleneck before optimizing.

## Code
- Match the surrounding style: naming, comment language and density, idioms.
- Small, focused changes; backward-compatible defaults.
- Keep paths centralized; no hard-coded absolute paths in project code.
- On Windows, set UTF-8 explicitly when writing files or printing non-ASCII text.

## Communication
- Lead with the answer, then the evidence. Flag uncertainty and what is unverified.
- If the user's intuition is right or wrong, say so directly, with the reason.
- Before a long job: what it does, how long, what decision is pending. After:
  results, caveats, and what is not done.
- Don't expand scope silently; offer follow-ups instead.
- Deliverables match their audience and the project's language.
- Always convey ideas clearly. Don't try to summarize complex contexts in a few words, use as many words as necessary, but don't extend the text just to make it longer, nor use difficult words unnecessarily.

## Documents and figures
- Render and look at every page, slide and figure before handing it over:
  overlaps, overflow, phone width, light and dark themes.
- Charts: never a dual y-axis; consistent colours per entity; data from result files.
- Always transmit the idea 
