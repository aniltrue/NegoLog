# NegoLog V2 release notes

## 2.1.0 — 2026-09-09

- Add `CBOMAgent` and `CBOMJavaAgent`, connecting the maintained CBOM opponent
  model to the published offering/acceptance strategy in Python and native Java.
- Bundle the public CBOM core, Java source, citation and SHA-256 manifest so
  either checkout runs independently. Java is optional and built before use.
- Add explicit `EndNegotiation` support for no-agreement decisions, including
  session logging and replay. Existing no-agreement result categories remain.
- Handle zero-offer endings in movement analysis and terminal rows in metric
  histories; preserve the raw domain identifier when generating domain graphs.
- Add Python-only and mixed-language tournament configurations, standalone demos,
  an integration diagram and a guide covering setup, outputs and method citation.
- Extend regression tests and CI to exercise actual Java sessions as well as
  the existing Python framework.

This adds two language implementations of one strategy; it is not a performance
ranking. The method's documented implementation choices and large-domain
candidate-search limitations remain applicable. See [the CBOM guide](docs-source/cbom.rst).

## 2.0.0 — 2026-09-09

NegoLog V2 continues the original NegoLog negotiation framework with updated
opponent models and agents, corrected assessment and logging, more reliable
domain and tournament workflows, and new usage guides. This distribution is
maintained by Mehmet Onur Keskin. The original authorship, GPLv3 license and
[IJCAI 2024 paper citation](CITATION.bib) are preserved.

### Models, agents and compatibility

- Add the CUHK estimators and Stepwise, Expectation and Regression COMB variants;
  update CBOM, Bayesian and Windowed implementations.
- Introduce concrete uniform and CBOM estimated preferences under an abstract
  `EstimatedPreference` base, and pass round deadlines to supported models.
- Correct existing-agent failures and update selected initialization, concession
  and learning behavior. The catalog retains the 26 existing agent exports.

These include API and policy changes. Keep the old code and configuration when
reproducing earlier experiments; read the
[migration checklist](MAINTENANCE.md#migration-quick-reference) before upgrading.
Successful tests do not establish equivalence to an original paper or a ranking
of negotiation strategies.

### Assessment, records and runtime

- Correct utility/rank pairing, estimated bid-space distances, Pareto metrics,
  model-series isolation and undefined-measurement handling.
- Preserve the three-value `calculate_error` API; provide separate optional
  Pearson/MAPE statistics and opt-in additive batch evaluation.
- Support keyed sampling and explicit sparse Excel output; preserve repeated
  session files, callback results and moved-output resolution.
- Validate CLI and Web configurations and selected domains before replacing
  output; improve cancellation and error reporting.
- Keep previews separate from saved profiles, synchronize domain catalogs,
  stage writes with rollback, and bound random-generation attempts.
- Restrict the local Web interface to loopback/same-origin requests while
  retaining trusted Python plugins and local HTTP clients.

### Learning and citation

- Add a two-session quickstart, tested configuration and extension tutorials,
  a component catalog, troubleshooting, migration and contribution guides.
- Provide an accessible workflow diagram, a real interface screenshot and
  responsive, searchable Sphinx documentation.
- Add `CITATION.cff` and BibTeX so research using V2 can cite the published
  framework and separately record the software version.

### Validation and known limits

The inherited framework revision passed 421 tests on Python 3.10 across Linux,
Windows and macOS. Documentation examples completed 14 local sessions. This
release keeps that runtime and test code unchanged; its workflows also run on
the V2 repository's `main` branch.

Use Python 3.10 with the existing dependency constraints. A configured
`result_dir` is replaced when a run starts. Large bid spaces and per-offer
assessment can be expensive; seeded runs are not guaranteed to be identical
across every agent or machine. Undefined correlations, legacy long worksheet
names, blocking native-code cancellation and process interruption between
domain/catalog replacements remain described in [MAINTENANCE.md](MAINTENANCE.md).

### Provenance and reproducibility

The code descends from [aniltrue/NegoLog](https://github.com/aniltrue/NegoLog),
including the maintenance revision at
[`85dae16`](https://github.com/aniltrue/NegoLog/commit/85dae1683fceafe5085ca24e888ed235201eb8bf).
Its Git history and component references are retained. The corresponding
changes are proposed in [upstream PR #2](https://github.com/aniltrue/NegoLog/pull/2);
this distribution does not imply that the upstream project has merged or
released that proposal.

For the fixed 2.0.0 source revision, use the `v2.0.0` tag. Record its full commit
alongside the YAML, domain profiles, environment and outputs:

```sh
git checkout v2.0.0
git rev-parse HEAD
```

The framework remains a clone-and-run project: module imports stay under
`nenv`. This release does not change the package name or require a package-index
installation.
