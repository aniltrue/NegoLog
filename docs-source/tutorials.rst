Configure and extend NegoLog
============================

Start with :doc:`getting-started`. These examples run from the repository root
in the same Python 3.10 environment and use only bundled negotiation components.

.. contents:: On this page
   :local:
   :depth: 2

Create your own configuration
-----------------------------

Save this complete file as ``tournament_configurations/my_tournament.yaml``:

.. code-block:: yaml

   deadline_time: null
   deadline_round: 20
   agents:
     - BoulwareAgent
     - ConcederAgent
   domains: ["0"]
   loggers:
     - BidSpaceLogger
     - TournamentSummaryLogger
     - EstimatorOnlyFinalMetricLogger
   estimators:
     - BayesianOpponentModel
   self_negotiation: false
   repeat: 2
   result_dir: results/my-tournament
   seed: 1234
   shuffle: false
   drawing_format: matplotlib-PNG

Run it with:

.. code-block:: console

   python run.py tournament_configurations/my_tournament.yaml

There are four sessions: two ordered agent pairs, each repeated twice. With
``n`` distinct agents, ``d`` domains, and ``r`` repeats, a tournament without
self-negotiation has ``n * (n - 1) * d * r`` sessions. Enabling self-negotiation
changes the count to ``n * n * d * r``. This makes it possible to estimate the
workload before adding agents or domains.

Make one change at a time
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Goal
     - Configuration change
   * - Retain a previous run
     - Choose a new ``result_dir`` before running again. Output directories are
       replaced at the start of a tournament.
   * - Try another strategy
     - Add an exact agent class name from :doc:`components` to ``agents``.
       Display names such as ``Conceder`` are not class names.
   * - Include another domain
     - Add its quoted identifier to ``domains``. ``"0"`` refers to
       ``domains/domain0/`` and its row in ``domains/domains.xlsx``.
   * - Assess another model
     - Add its exact model class name to ``estimators``. Models observe received
       offers; the agent's strategy decides whether to use estimates.
   * - Omit model assessment
     - Set ``estimators: []`` and remove the estimator logger. Keep
       ``BidSpaceLogger`` with ``TournamentSummaryLogger`` for agent summaries.
   * - Measure the entire learning trajectory
     - Replace ``EstimatorOnlyFinalMetricLogger`` with
       ``EstimatorMetricLogger``. Per-offer evaluation is more expensive.
   * - Use a wall-clock deadline
     - Set, for example, ``deadline_time: 30`` and ``deadline_round: null``.
       A mixed deadline stops when either limit is reached.
   * - Export vector plots
     - Set ``drawing_format: matplotlib-SVG``. Supported choices also include
       ``matplotlib-PNG`` and ``plotly``.

Use positive integer round limits and at least one positive deadline. A
single-agent configuration needs ``self_negotiation: true``. Built-in component
names resolve through their registries; the CLI and web interface also accept
full Python import paths. Configuration files must be YAML mappings, and
unrecognized fields are rejected.

Add your first agent module
---------------------------

First confirm the extension mechanism with an existing strategy. Save this as
``my_agent.py`` in the repository root:

.. code-block:: python

   from agents.conceder.Conceder import ConcederAgent


   class MyConceder(ConcederAgent):
       """Use the existing Conceder policy under a distinct display name."""

       @property
       def name(self):
           return "MyConceder"

In ``my_tournament.yaml``, replace ``ConcederAgent`` with
``my_agent.MyConceder`` and change ``result_dir`` to
``results/my-conceder``. Run the same CLI command again. The results should now
name ``MyConceder`` and keep all four session workbooks.

This subclass intentionally inherits the existing bidding and acceptance policy.
You have verified import, scheduling, and logging before introducing your own
strategy logic. You do not need to edit the built-in registry.

When developing a strategy from ``nenv.AbstractAgent``, implement its ``name``
property and ``initiate(opponent_name)``, ``receive_offer(bid, t)``, and
``act(t)`` methods. Initialize session state in ``initiate`` and return an
``Offer`` or ``self.accept_action`` from ``act``; check ``self.can_accept()``
before acceptance. ``t`` is normalized negotiation time, not seconds.

The framework's ``receive_bid`` method updates the configured estimators before
calling your ``receive_offer`` hook. Do not update those estimators a second
time. Use distinct display names so analyses can distinguish components. Full
import paths execute Python code, so load components you trust. Refer to
:doc:`api` for the interfaces and the bundled Conceder source for the complete
inherited policy.

Sample model metrics without skipping learning
----------------------------------------------

Save this as ``my_loggers.py`` in the repository root:

.. code-block:: python

   from nenv.logger import EstimatorMetricLogger


   class SampledMetrics(EstimatorMetricLogger):
       """Measure every fifth round and at the end of the session."""

       def __init__(self, log_dir):
           super().__init__(log_dir, sample_every=5)

Replace the estimator logger in ``my_tournament.yaml`` with
``my_loggers.SampledMetrics``. Retain at least one estimator and set a fresh
``result_dir``, such as ``results/sampled-metrics``. Then run the CLI again.

Model sheets in the session workbooks now include explicit ``Round`` and
``Action`` columns for sampled offers from both sides in rounds 0, 5, 10, and
so on. Final-state measurements are written to the model sheets in
``results.xlsx`` and summarized in ``opponent model/estimator_summary.xlsx``;
do not infer that final assessment was skipped from an empty terminal row in
the session workbook. The models still receive every incoming offer. Some
sheet rows are empty because dense workbook alignment is retained. Class-based
YAML loading supplies only ``log_dir`` to a logger constructor; the subclass
is how you set sampling options.

Do not include both the default and sampled estimator logger in the same run:
they write the same metric sheets. Use the final-only logger when only final
accuracy matters. Sampling and logged round keys are described in :doc:`logging`.

Evaluate a model directly in Python
-----------------------------------

Save this as ``inspect_model.py`` in the repository root and run
``python inspect_model.py``:

.. code-block:: python

   from nenv import Preference
   from nenv.OpponentModel import BayesianOpponentModel

   own = Preference("domains/domain0/profileA.json")
   truth = Preference("domains/domain0/profileB.json")
   model = BayesianOpponentModel(own, deadline_round=20)

   # Illustrative observation, chosen from a bundled profile for this example.
   model.update(truth.bids[0], t=0.0)
   rmse, spearman, kendall = model.calculate_error(truth)
   print({"RMSE": rmse, "Spearman": spearman, "KendallTau": kendall})
   print(model.calculate_additional_metrics(truth, pearson=True, mape=True))

Only the evaluation code receives ``truth`` here. A negotiating agent receives
its own profile and the opponent's offers, not the opponent's private utility
profile. This one-observation illustration is not a realistic offer dataset or
a performance comparison.

``calculate_error`` returns three values in the shown order. Optional Pearson
and percentage MAPE are named results from a separate API. A constant utility
vector has undefined rank correlation; MAPE with zero true utilities is also
undefined by default. Preserve these ``NaN`` values. See :doc:`models` for
initialization, deadline handling, and the optional additive batch path.

Prepare a reproducible study
----------------------------

Before scaling up, check session counts and outcomes on a small domain. Bid-space
size is the product of the numbers of values per issue; enumeration and model
evaluation can become expensive even with a short deadline.

Keep the following beside the output you retain:

* The Git commit, uncommitted changes if any, and the exact configuration file.
* Both domain profiles and catalog metadata used in the experiment.
* Python and dependency versions, seed, deadlines, repetitions, role order,
  and logger selection.
* The complete outcomes, including failures and undefined measurements.

For example, after the run, from the repository root:

.. code-block:: console

   git rev-parse HEAD
   git status --short
   python --version
   python -m pip freeze

The seed controls the framework's Python and NumPy random streams. Some agents
manage additional randomness, and wall-clock timing can alter outcomes; a seed
alone does not guarantee identical results across machines or revisions.
Report strategy outcomes and estimation accuracy separately, and cite NegoLog
using the :download:`repository citation instructions <../README.md>`.
