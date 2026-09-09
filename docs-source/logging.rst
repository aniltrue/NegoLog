Logging and measurement cost
============================

Add a logger
------------

Subclass ``nenv.logger.AbstractLogger`` and override only the callbacks needed
for your analysis. Tournament configuration constructs each logger with
``log_dir``. If you override ``__init__``, call ``super().__init__(log_dir)``;
the base constructor calls ``initiate()`` once. Reset state for each session in
``before_session_start(session)`` when it must not carry over to the next pair.

Row callbacks return a nested mapping such as
``{"MyAnalysis": {"OfferCount": count}}``: the outer key selects a worksheet,
and the inner mapping supplies its column values. Return ``{}`` when there is
no measurement. Choose distinct sheet/column names; a reused column name can
replace another logger's value in the merged row.

.. list-table:: Callback outputs
   :header-rows: 1
   :widths: 38 62

   * - Callback
     - What to return / where it is used
   * - ``before_session_start(session)``
     - A list of additional session worksheet names, or ``[]``.
   * - ``on_offer(agent, offer, time, session)``
     - A row mapping merged into the current session workbook row.
   * - ``on_accept(agent, offer, time, session)``
     - A row mapping merged into the final outcome returned to the tournament.
   * - ``on_fail(time, session)``
     - A row mapping for the terminal outcome without agreement, including
       error/timeout paths. Use ``on_session_end`` to inspect the recorded
       outcome when distinguishing those cases.
   * - ``on_session_end(final_row, session)``
     - A row mapping added to the completed outcome in the tournament workbook.
   * - ``on_tournament_end(tournament_logs, agent_names, domain_names, estimator_names)``
     - No row return is consumed; write the required summaries or figures.

Terminal metric callback results belong to the tournament outcome; do not
assume they also populate the saved session workbook's terminal row. Use
``self.get_path(filename)`` for output under the configured result directory,
and ``self.get_session_path(row)`` when reopening a recorded session, including
repeated sessions or a copied results folder.

To try a logger:

1. Start with the working sampled-logger example in :doc:`tutorials` and select
   its full Python path in ``loggers``.
2. Confirm the expected sheet and column names in a small run before adding
   more callbacks. Keep worksheet names within Excel's 31-character limit.
3. Check the cases your measurement needs: agreement, failure, no usable
   observations, and undefined numerical values. Document required companion
   loggers; :doc:`components` lists built-in dependencies.

Default observations
--------------------

``EstimatorMetricLogger`` measures every offer by default. The
``EstimatorOnlyFinalMetricLogger`` measures the terminal state. Logger callbacks
assess models; they do not replace the models' received-offer updates.

.. code-block:: python

   from nenv.logger import EstimatorMetricLogger

   class SampledMetrics(EstimatorMetricLogger):
       def __init__(self, log_dir):
           super().__init__(log_dir, sample_every=5)

Put the subclass in an importable module and select its full path in a YAML
configuration. Class-based configuration passes ``log_dir``; it does not pass
arbitrary constructor keywords. An interval of five measures both sides in
rounds 0, 5, 10, and so on, plus the terminal state. Models still update on every
received offer. ``include_round=True`` adds explicit ``Round``/``Action`` keys
without reducing the measurement frequency.

Workbook contracts
------------------

Default Excel serialization retains dense padding. Explicit
``ExcelLog.save(path, sparse_sheets={"MyMetrics"})`` omits only empty dictionaries
in the selected sheets and leaves the in-memory rows unchanged. Loading a
compacted workbook does not recreate padding. Use keyed readers for compacted
metrics; other consumers may still rely on dense row alignment.

The estimator history reader uses ``Round`` and ``Action`` when available and
can also read legacy dense data. A compressed legacy sheet without those keys
cannot reliably be assigned to rounds. For sampled reprocessing, start from a
clean copy without prior values in the estimator sheets; old and newly sampled
metrics cannot be silently combined.

``SessionLogs`` postprocessing updates the receiving side's estimators, as a
live session does. Current JSON and legacy Python dictionary bid representations
are read without rewriting quoted value names. Keep the original tournament
outcome row when reprocessing: the offer workbook alone cannot reconstruct an
agent error or timeout, so missing terminal fields use defaults while recorded
outcome fields are retained. Use copies when preserving earlier measurements.

Keep undefined rank correlations as ``NaN``. Do not replace them with zero or
blend corrected metric columns with earlier results without recording the code
version. Per-offer measurement cost may affect time-limited negotiations.

API
---

.. autoclass:: nenv.logger.EstimatorMetricLogger
   :members: get_estimator_results

.. autoclass:: nenv.logger.EstimatorOnlyFinalMetricLogger

.. autoclass:: nenv.logger.AbstractLogger
   :members: initiate, before_session_start, on_offer, on_accept, on_fail, on_session_end, on_tournament_end, get_path, get_session_path

.. autoclass:: nenv.utils.ExcelLog
   :members: save, load
