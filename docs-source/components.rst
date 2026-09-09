Choose agents, models and loggers
=================================

NegoLog has three independently configurable component lists. An **agent**
chooses offers and decides whether to accept. An **opponent model** estimates
preferences from received offers. A **logger** records or evaluates what
happened. Start with the bundled quickstart and change one list at a time.

.. list-table:: Choose by the question you want to answer
   :header-rows: 1
   :widths: 32 68

   * - Question
     - Configuration to inspect
   * - How do strategies negotiate against one another?
     - ``agents``, domain role order and deadlines; include ``BidSpaceLogger``
       and ``TournamentSummaryLogger`` for outcome summaries.
   * - How accurately do models estimate an opponent's preferences?
     - ``estimators`` plus either ``EstimatorMetricLogger`` for trajectories
       or ``EstimatorOnlyFinalMetricLogger`` for terminal measurements.
   * - What did an agent offer and why did the session end?
     - Open the session workbook identified by ``FilePath`` in ``results.xlsx``.
       Add a specialized logger only when the extra measurement is needed.

Use the exact class names below in YAML. Built-in names resolve through
``agents/__init__.py``, ``nenv/OpponentModel/__init__.py`` and
``nenv/logger/__init__.py``. Custom classes use an importable path such as
``my_agents.MyAgent``. A component's display name in a workbook can differ
from its Python class name.

Adding a model to ``estimators`` makes it observe received offers; it does not
automatically change an agent's bidding policy. Some agents maintain their own
internal opponent models. Those internal models and the configured assessment
models have separate roles. The descriptions below summarize implemented
mechanisms, not a performance ranking or a guarantee of equivalence to the
original publication.

26 negotiating agents
---------------------

Time-based starting points
~~~~~~~~~~~~~~~~~~~~~~~~~~

These compact implementations make useful entry points for reading the agent
interface. Their different concession curves are easy to compare on the same
small domain.

.. list-table:: Time-based agents
   :header-rows: 1
   :widths: 28 72

   * - YAML class name
     - Implemented approach
   * - ``BoulwareAgent``
     - Maintains a higher target early and concedes later in the session.
   * - ``ConcederAgent``
     - Concedes more of its target utility earlier in the session.
   * - ``LinearAgent``
     - Uses a linear target-utility progression with time.

Further bundled strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~

The registry also exposes the following strategies. Their source files retain
individual authorship and publication references. Source-level adaptation notes
matter when reproducing an earlier study; consult the repository's
``MAINTENANCE.md`` before replacing an existing baseline.

.. list-table:: Further agents, alphabetically
   :header-rows: 1
   :widths: 30 70

   * - YAML class name
     - Implemented approach / useful distinction
   * - ``AgentBuyog``
     - Estimates the opponent's concession behavior and uses time-dependent
       acceptance thresholds.
   * - ``AgentGG``
     - Uses importance maps and time-dependent thresholds to select bids.
   * - ``AgentKN``
     - Combines bid search with opponent value frequencies and a time-dependent
       acceptance threshold.
   * - ``AhBuNeAgent``
     - Uses importance ordering and value constraints when modifying bids.
   * - ``Atlas3Agent``
     - Combines a concession lower bound, relative-utility search and
       opponent-history frequencies.
   * - ``Caduceus``
     - Combines suggestions from a portfolio of negotiating agents.
   * - ``Caduceus2015``
     - A separate strategy, also used inside Caduceus, that moves from high
       own-utility offers toward an estimated Nash-product target.
   * - ``CUHKAgent``
     - Uses adaptive concession and opponent-history information in bid
       selection. It is distinct from the two standalone CUHK estimators.
   * - ``HardHeaded``
     - Uses a concession limit and opponent estimates to choose among bids
       with similar own utility.
   * - ``HybridAgent``
     - Combines time-based and behavior-based concession.
   * - ``HybridAgentWithOppModel``
     - Extends the hybrid approach with its own opponent model for bid selection.
   * - ``IAMhaggler``
     - Uses observed concession history and its existing Gaussian-process
       regression to set time/utility targets.
   * - ``Kawaii``
     - Searches bids above a time-dependent threshold and accepts against
       that threshold.
   * - ``LuckyAgent2022``
     - Combines time-dependent bid and acceptance thresholds with an internal
       opponent model. Its workbook display name is ``LuckAgent2022``.
   * - ``MICROAgent``
     - Uses a reciprocal concession rule: concede when the opponent concedes.
   * - ``NiceTitForTat``
     - Responds to opponent concessions while targeting an estimated Nash
       outcome with an internal Bayesian model.
   * - ``ParsAgent``
     - Combines time-dependent, randomized and frequency-based bid selection.
   * - ``ParsCatAgent``
     - Samples bids around changing utility thresholds and uses received-offer
       history in its choice.
   * - ``PonPokoAgent``
     - Randomly chooses one of five time-dependent utility-bound patterns.
   * - ``RandomDance``
     - Randomizes the weighting of learned utility estimates when selecting bids.
   * - ``Rubick``
     - Uses randomized concession and issue-value frequencies to choose bids
       above a target utility.
   * - ``SAGAAgent``
     - Uses time-dependent targets and probabilistic acceptance. This port uses
       the supplied preference; its genetic-algorithm estimation calls are
       disabled in ``initiate``.
   * - ``YXAgent``
     - Uses utility thresholds and learned issue/value frequencies in its
       acceptance decision.

Nine opponent models
--------------------

Use these names in ``estimators``. :doc:`models` explains initialization,
deadline handling and the metric API.

.. list-table:: Registered estimators
   :header-rows: 1
   :widths: 40 60

   * - YAML class name
     - Estimation mechanism / relevant distinction
   * - ``ClassicFrequencyOpponentModel``
     - Increases value scores for repeated observations and issue scores when
       a value is retained between offers.
   * - ``WindowedFrequencyOpponentModel``
     - Compares observations through a 25-offer window.
   * - ``BayesianOpponentModel``
     - Maintains weight/evaluation hypotheses with a concession assumption
       scaled by the round deadline.
   * - ``ConflictBasedOpponentModel``
     - Uses offer comparisons, conflicts and preference ordering to estimate
       issue and value weights.
   * - ``CUHKOpponentModel``
     - Uses value frequencies with equal issue weights; counting continues
       beyond 100 distinct bids.
   * - ``CUHKFrequencyOpponentModel``
     - Adapts the public CUHK agent helper's counting rule: value-count updates
       stop when the 101st distinct bid is observed.
   * - ``StepwiseCOMBOpponentModel``
     - Updates weight/evaluation hypotheses from consecutive-offer utility
       differences.
   * - ``ExpectationCOMBOpponentModel``
     - Compares observed utility with a historical-mean estimate.
   * - ``RegressionCOMBOpponentModel``
     - Uses time/utility regression with a window scaled by the round deadline.

The two CUHK estimators have different update contracts; neither is an alias
for ``CUHKAgent``. Uniform initialization can give every bid the same estimated
utility before any learning. Rank correlations for a constant vector are
undefined (``NaN``), which should remain distinct from zero accuracy.

Choose the output you need
--------------------------

The core session and tournament workbooks are written even when ``loggers`` is
empty. Add loggers for a particular analysis. More loggers can require more bid
enumeration, disk output and computation; per-offer work also uses time in a
time-limited session.

.. list-table:: Outcome and behavior loggers
   :header-rows: 1
   :widths: 33 67

   * - YAML class name
     - Output / configuration note
   * - ``BidSpaceLogger``
     - Adds distances to Nash and Kalai points to the outcome. Include it with
       ``TournamentSummaryLogger``, ``FinalGraphsLogger`` or ``DomainGraphsLogger``,
       which consume these columns.
   * - ``TournamentSummaryLogger``
     - Writes ``summary.xlsx`` with per-agent outcomes. Separate sheets cover
       all sessions, accepted sessions and sessions without errors/timeouts.
   * - ``FinalGraphsLogger``
     - Creates tournament-level heatmaps across agents and domains in
       ``tournament_graphs/``.
   * - ``DomainGraphsLogger``
     - Creates per-domain agent-comparison heatmaps in ``domains/`` under
       the run's result directory.
   * - ``UtilityDistributionLogger``
     - Records offered-utility distributions and produces distribution plots.
       This logger writes PNG rather than interactive output when ``plotly``
       is selected.
   * - ``MoveAnalyzeLogger``
     - Classifies offer moves and summarizes sensitivity, awareness and move
       correlation for each side.

.. list-table:: Opponent-model assessment loggers
   :header-rows: 1
   :widths: 36 64

   * - YAML class name
     - Output / configuration note
   * - ``EstimatorOnlyFinalMetricLogger``
     - Measures terminal RMSE and rank correlations and writes the estimator
       summary. Choose this when you do not need per-round trajectories.
   * - ``EstimatorMetricLogger``
     - Measures every offer by default and adds metric trajectories, plots
       and summaries. A subclass can set a sampling interval; see :doc:`logging`.
   * - ``EstimatedUtilityLogger``
     - Records estimated utilities, product scores and social welfare using
       each configured model.
   * - ``EstimatedBidSpaceLogger``
     - Records distances in each model's estimated bid space.
   * - ``EstimatedParetoLogger``
     - Compares estimated and true Pareto frontiers through precision, recall
       and F1 measurements.
   * - ``EstimatedMoveLogger``
     - Assesses estimated move classifications and writes
       ``opponent model/estimator_move_performance.xlsx``. Include
       ``MoveAnalyzeLogger`` to supply the true move labels.

Configure at least one estimator for the model-assessment loggers. Use either
the final-only or the per-offer metric logger in a run; both write the same
terminal summary filename. Distinct model display names keep worksheet series
identifiable. Refer to :doc:`logging` for sampling, sparse rows and missing data,
and :doc:`runs` for run records and reproducibility.
