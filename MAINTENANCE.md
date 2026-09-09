# Opponent model and agent updates

This update changes model initialization and several built-in agents' behavior,
as well as correcting evaluation and logging errors. It is not a drop-in
reproduction of results obtained with earlier commits. Record the code revision,
model configuration and seed when comparing experiments.

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

## Optional sparse workbook output

`ExcelLog.save(path, sparse_sheets={"CustomMetrics"})` omits empty `{}` padding
rows only from selected sheets. The default remains dense, and in-memory rows
are unchanged. Compacted sheets need explicit keys and a compatible reader;
the built-in estimator readers still depend on dense row alignment. Loading a
compacted sheet does not reconstruct padding. No sampling schedule or automatic
compaction is enabled.

## Validation

Use Python 3.10 with the repository's `requirements.txt` and `pytest`:

```sh
python -m pytest -q tests
```

Tests use small synthetic preferences. They check local behavior and API
integration; they are not a tournament benchmark or evidence of a performance
improvement. Historical experiment outputs are not rewritten by these changes.

Two existing limitations are observable in these tests: SAGA can produce a NaN
acceptance probability for a very low-utility offer (the exercised case still
returns a valid counteroffer), and the existing Classic Frequency model name
exceeds Excel's 31-character sheet-title limit. Neither behavior is introduced
by this update; some Excel applications may reject that existing sheet name.
