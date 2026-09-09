Logging and measurement cost
============================

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
   :members: get_session_path

.. autoclass:: nenv.utils.ExcelLog
   :members: save, load
