# Migration and compatibility

Use this guide when moving an existing experiment or extension to the current
checkout. For a first run, start with the [README](README.md); for available
classes, use the [component catalog](docs-source/components.rst).

## Migration quick reference

| If your project does this | What to change or check | Details |
| --- | --- | --- |
| Instantiates `EstimatedPreference(reference)` | Choose `UniformEstimatedPreference(reference)` or `CBOMEstimatedPreference(reference)`. Custom subclasses implement `initialize_weights`. | [Preference API](#preference-api-migration) |
| Assumes an inverse initial estimate | Base models now default to uniform weights. Select an explicit supported initialization and record it. | [Preference API](#preference-api-migration) |
| Constructs a custom opponent model or embeds one in an agent | Support the deadline handoff before observations. Use a positive integer round limit; the default horizon is 1000. | [Preference API](#preference-api-migration) |
| Compares earlier agent/model results with new runs | Treat the revisions as different implementations. Several concession, initialization and update policies changed. | [Models](#opponent-models), [agents](#existing-agents) |
| Unpacks `calculate_error(...)` | Keep the same three values: RMSE, Spearman and Kendall. Treat undefined correlations as missing values. | [Assessment corrections](#assessment-corrections) |
| Wants Pearson, MAPE or faster additive evaluation | Request named statistics separately; enable `vectorized=True` explicitly when appropriate. | [Additional statistics](#additional-named-statistics), [batch evaluation](#optional-additive-batch-evaluation) |
| Selects a CUHK estimator | Choose between the two counting contracts explicitly; neither class is the full CUHK agent. | [CUHK adapters](#public-cuhk-frequency-adapter) |
| Samples metrics or reprocesses workbooks | Preserve round/action keys and choose compatible readers; default Excel output remains dense. | [Sampling and round keys](#optional-sampling-and-round-keys) |
| Generates domains or reruns a tournament | Keep input profiles and previous output separately. Successful runs replace their result directory; infeasible domain constraints now raise an error. | [Configuration, domains and lifecycle](#configuration-domains-and-run-lifecycle) |
| Uses checked-in `docs/` HTML as the current API | Read or build `docs-source/` for this checkout. | [Current documentation](#current-documentation) |

Before a comparison, save the earlier revision, configuration, profiles and
results. Run a small round-limited example with the new revision, inspect its
outcomes and expected columns, then record the new revision with subsequent
results. A successful smoke test checks integration; it does not establish
equivalence to an earlier experiment.

## Opponent model and agent updates

This update changes model initialization and several built-in agents' behavior,
as well as correcting evaluation and logging errors. It is not a drop-in
reproduction of results obtained with earlier commits. Record the code revision,
model configuration and seed when comparing experiments. Removing assessment-time
RNG consumption can also change subsequent stochastic choices with the same seed.

## Preference API migration

`EstimatedPreference` is now an abstract base. Instantiate
`UniformEstimatedPreference(reference)` or `CBOMEstimatedPreference(reference)`
instead. Custom subclasses must implement `initialize_weights(reference)`.
AgentBuyog and SAGA use the concrete uniform class.

The default base model initialization is `mode="uniform"`: issue weights are
`1 / number_of_issues`; equal value weights are max-normalized to 1. Consequently
all bids initially have estimated utility 1. `mode="cbom"` selects the inverse
own-preference initialization. These are different modeling assumptions, and
choosing `cbom` does not restore every behavior of an earlier model version.

Model construction with one reference argument remains supported. The base
class also exposes `set_deadline(deadline_round)`; `SessionManager` calls it
before constructing the agents. It also sets the agents' optional
`deadline_round` attribute before `initiate()`, so the embedded models in
NiceTitForTat and HybridWithOppModel receive the same horizon. Round-based and
mixed sessions use the actual round limit. Standalone models and time-only
sessions default to 1000 rounds.
The limit must be a positive integer; no environment variable is required.
Custom models that override this method should accept `None` for the default.

## Opponent models

| Component | Resulting behavior |
| --- | --- |
| ConflictBasedOpponentModel | Revised comparison map, conflict handling, belief ordering and issue-weight calculation. This is an algorithm implementation update, not a claim that every changed line fixes a demonstrated failure. |
| CUHKOpponentModel | Adds a standalone frequency estimator with uniform issue weights. |
| Stepwise / Expectation / Regression COMB | Adds three estimators using weight/evaluation hypotheses: Stepwise uses consecutive-offer utility differences, Expectation compares with the historical mean, and Regression uses time/utility regression. Regression's compact window follows the configured round limit, with a minimum of one observation. |
| BayesianOpponentModel | Uses a deadline-scaled concession decrement, `0.9 / deadline_round`, with a positive numerical floor when updates exhaust the expected utility. |
| WindowedFrequencyOpponentModel | Changes the observation window from 48 to 25. This changes the model's responsiveness. |

The synthetic checks cover finite normalized estimates, selected update paths,
repeated bids, small horizons and integration. They do not establish equality
with the original Java agents or published performance rankings.

## Existing agents

| Agent | Resulting behavior |
| --- | --- |
| Rubick | Clears candidates separately for each issue; uses mean frequency and a two-party history gate. The candidate reset prevents values from unrelated issues from being selected. |
| CUHK | Revises concession when the discount factor equals one; samples with replacement; removes the extra wall-clock adjustment. |
| HardHeaded | Updates paired bid-history representations and the associated access, bid-selector assignment placement, tolerance and random selection behavior. |
| Hybrid / HybridWithOppModel | Changes concession control points and restores the domain-size-dependent curve in the opponent-model variant. |
| NiceTitForTat | Changes the acceptance guard and refreshes the estimated Nash target on each relevant call. |
| PonPoko | Selects from five patterns rather than six. This is a policy choice, not a proven out-of-range exception fix. |
| IAMhaggler | Initializes the discount factor per instance and stops installing a process-wide convergence-warning filter. Its existing Gaussian-process strategy is otherwise retained. |
| AgentBuyog / SAGA | Uses concrete uniform preferences after the abstract-base migration. |

The agent registry retains all 26 existing exported agents. Pure formatting and
annotation differences in Atlas3 and Conceder are omitted.

## Assessment corrections

- Spearman and Kendall compare the true and estimated utilities of the **same
  bids**. Tied utilities retain tied ranks; a constant vector or a single bid
  yields NaN for rank correlation. Measurement no longer consumes the global
  random-number generator. `calculate_error` still returns exactly
  `(rmse, spearman, kendall)` and accepts the existing metric flags.
- Per-round observations stay in their respective estimator series, rather
  than all accumulating under the first estimator's name.
- The median-round plots receive the truncated means without changing the
  caller's observations. The existing exclusive cutoff convention is retained.
- Estimated Pareto precision is `TP / (TP + FP)` and recall is
  `TP / (TP + FN)`. Empty or disjoint frontiers return zero scores.
- Pareto and estimated bid-space summaries filter missing values only in their
  own columns. Undefined rank correlations in a shared sheet no longer erase
  valid frontier scores or turn valid distances into a misleading zero.

Undefined ranks may propagate NaN through existing aggregate functions. Do not
replace them silently with zero or combine corrected metric columns with older
results without identifying their code versions.

## Optional additive batch evaluation

```python
rmse, spearman, kendall = model.calculate_error(reference, vectorized=True)
```

The default scalar path is unchanged. The fast path handles the standard
additive utility implementation using ordinary double-precision weights and
standard bids with a common issue iteration order. Custom utility functions,
custom iteration, other preference subclasses, different bid issue orders and
other numeric types fall back to normal scalar calls. The helper checks the
original method identities, including overrides installed before it is loaded.

No utility values, bid encodings or preference data are persistently cached.
Each call reflects current weights, bid contents, stored true utilities and bid
order. The original assessment convention uses `reference.bids[i].utility` for
true utilities. The fast path does not regenerate those values or change the
reference preference's own bid cache. Speed depends on domain and input type;
small/custom workloads can fall back or see little benefit.

## Additional named statistics

```python
extra = model.calculate_additional_metrics(reference, pearson=True, mape=True)
# {'Pearson': ..., 'MAPE': ...}
```

Only requested keys are returned; the default call returns `{}`. This is a
separate method and does not add logger columns or alter the existing tuple.
Pearson is NaN for constant vectors or fewer than two bids. MAPE is a percentage:
`100 * mean(abs(true - estimated) / abs(true))`. If any true utility equals zero,
the default returns NaN. Set `zero_utility="raise"` for an explicit `ValueError`;
zero-valued observations are never silently dropped. Empty input yields NaN.
This method also accepts `vectorized=True`.

## Public CUHK frequency adapter

`nenv.OpponentModel.CUHKFrequencyOpponentModel` exposes a preference estimate
based on the counting rule in the existing public
`agents/CUHKAgent/OpponentBidHistory.py` helper. Repeated offers count while
history contains at most 100 distinct bids; the 101st distinct bid stops further
value-count updates, while distinct history and bid counts continue growing.
This preserves the public helper's gate rather than defining a new window.

The adapter explicitly chooses equal issue weights and per-issue maximum
normalization of value counts. Initially all values score 1; after observations,
unseen values score 0. These normalization choices do not promise the same
ordering as CUHKAgent's raw-frequency bid selection. It does not change CUHKAgent
or claim to reproduce that agent's full policy. Display name: `CUHK Frequency Model`.

The separately exposed `CUHKOpponentModel` continues updating counts after
100 distinct offers. The two adapters have different update contracts; choose
them explicitly rather than treating them as interchangeable names.

## Optional sampling and round keys

```python
logger = EstimatorMetricLogger(log_dir, sample_every=5)
```

The default (`sample_every=1`, `include_round=False`) measures every offer and
keeps the original columns. An interval N measures offers from both sides in
rounds 0, N, 2N, ...; it does not skip opponent-model updates. Terminal accept/fail
callbacks still measure the final state. Sampling adds explicit `Round` and
`Action` keys. Use `include_round=True` to add these keys without sampling.
The interval must be a positive integer. Configure an instance through the
Python API, or define a logger subclass with these options for class-based
tournament configuration.

New keyed records and legacy dense records can be read by the estimator-series
extractor. Unmeasured padding rows are skipped. A compressed legacy sheet without
round/action keys cannot be reconstructed safely. For existing session-log
reprocessing, use a clean copy with no prior estimator metric values; keyed
sampling cannot silently combine newly measured and old dense observations.

`ExcelLog.save(path, sparse_sheets={"MyMetrics"})` can omit empty `{}` rows only
from explicitly selected sheets. Default serialization remains dense and
in-memory rows are unchanged. Compaction does not restore padding on load;
readers other than the keyed estimator reader may still require dense alignment.
No automatic compaction is enabled.

## Validation

### Configuration, domains and run lifecycle

- CLI and web configuration share validation for fields and concrete component
  types. Time limits must be positive finite numbers; round limits must be
  positive integers. Single-agent schedules require self-negotiation. The
  historical fallback from a nonpositive integer repeat count to one is retained.
- Before replacing output, tournament setup verifies the selected catalog rows
  by domain name and loads both profiles. Source/input directories, ancestor
  directories, files and symlink output targets are rejected.
- Web previews leave stored profiles and the catalog unchanged. Save/create
  operations replace one catalog entry by its domain identifier; deletion removes
  the corresponding entries. Saved normalized profiles match the utilities used
  for the reported domain statistics; older manual profiles could retain values
  above one while their statistics used normalized utilities. Domain folders and
  catalog workbooks are each replaced atomically in separate steps. Ordinary
  catalog write or rename failures restore the prior folder, including removal
  failures. Process interruption between steps is not a single atomic operation.
- Both generators accept keyword-only `output_dir`. Staged generation preserves
  an existing domain when generation fails. Random generation validates and
  copies ranges, retains the requested constraints, and raises after
  `max_attempts=1000` unsuccessful candidates by default. Attempts are bounded;
  large-domain enumeration remains potentially expensive. Infeasible constraints
  raise `ValueError` rather than silently widening the requested ranges. Bounded
  issue-weight normalization allocates integer hundredths instead of retrying
  for floating-point equality, so old seeded domain trajectories may change.
- Undefined normalized balance scores use JSON `null`. Genius export uses
  issue weights and bid/utility pairs from the same generated preference.
- The web process permits one active tournament because RNG and plot settings
  are shared. Unexpected tournament-level errors close the monitor and retain a
  nonempty error message; cancellation is retained even before the run starts.
  Completed session outcomes remain distinct from tournament-level failures.

### Current documentation

The checked-in HTML under `docs/` is a historical snapshot. It does not document
all model classes or the current abstract preference and metric APIs. The
[current Sphinx sources](docs-source/README.md) build from this checkout's public
`nenv` classes into a separate output directory. Documentation dependencies are
separate from runtime requirements. The documentation workflow creates a review
artifact and does not deploy the site.

### Constant and single-issue preferences

- Bayesian normalized-utility bounds are invalidated after a new observation,
  so later queries use the current hypothesis distribution. Finite tied
  predictions still return zero, without marking the model crashed or blocking
  future updates.
- Caduceus2015's utility-space normalization uses equal weights when an issue or
  value-weight total is zero. Its existing sum-normalization convention remains;
  positive-total formulas and `init_zero()` behavior are unchanged.
- RandomDance handles the case where every bid has utility one with a finite
  self-model that values all offers equally at one. This adds no random draws
  and leaves the nonconstant-domain formula unchanged.

### Runtime and portability corrections

- Caduceus2015's utility space uses the concrete inverse initializer; the
  abstract-base migration no longer prevents it or the Caduceus portfolio
  from responding to an offer.
- SAGA clamps the early acceptance ratio below its target to zero before
  exponentiation. This avoids NaN or greater-than-one probabilities while
  retaining the existing random draw and above-target formula.
- IAMhaggler uses its existing opening curve until an observed time slot has
  closed, instead of fitting a regression to empty history.
- RandomDance copies a candidate before changing its issue values; it no
  longer corrupts the preference's cached bids during initialization.
- Bid-to-bid and bid-to-dictionary equality compare the complete content.
  Content hashes ignore issue insertion order, so equal bids share dictionary
  and set entries. Do not mutate a bid's content while it is a dictionary key.
- Callback exceptions reach the session's Error result, including failures in
  initialization. Deliberately cancelled Python callbacks retain TimedOut
  status. Thread cancellation still depends on Python tracing; it is not a
  process-isolation guarantee for blocking native code.
- Repeated sessions keep distinct workbooks, including when a domain name
  resembles a repetition suffix. Result FilePath values identify each file;
  built-in readers also resolve these files after moving the results folder.
- List order is preserved for configured classes. Set inputs are sorted by
  module/class name before scheduling; duplicate entries are removed.
- A tournament with no measured offers can finish its error summaries without
  generating fictitious zero-valued curves. Empty round statistics remain NaN.
- Web agent discovery handles both path separators and excludes abstract
  classes. Bundled UI requests use the page's origin, including custom ports;
  polling a newly registered tournament safely reports Pending.

Use Python 3.10 with the repository's `requirements.txt` and `pytest`:

```sh
python -m pytest -q tests
```

Tests use small synthetic preferences. They check local behavior and API
integration; they are not a tournament benchmark or evidence of a performance
improvement. Historical experiment outputs are not rewritten by these changes.

The existing Classic Frequency model name exceeds Excel's 31-character sheet
title limit; some Excel applications may reject that existing sheet name.
Legacy dependencies can emit deprecation warnings, and IAMhaggler's Gaussian
process can emit convergence warnings on small histories. Finite-output checks
do not establish convergence or negotiation-performance improvements.
