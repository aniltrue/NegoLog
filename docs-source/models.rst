Opponent models and assessment
==============================

Implement an opponent model
---------------------------

Use this checklist for a custom estimator, then follow :doc:`tutorials` for the
import-path configuration and direct-assessment example:

1. Subclass ``nenv.OpponentModel.AbstractOpponentModel``. Keep construction from
   one reference preference supported; tournament setup calls
   ``YourModel(reference)``. If you override the constructor, call
   ``super().__init__(reference)`` to initialize its estimated preference and
   default round horizon.
2. Implement a ``name`` property returning a distinct display name, and
   ``update(bid, t)`` to process a received offer. ``t`` is normalized negotiation
   time. Update the estimated weights as required by your algorithm; ``update``
   returns nothing. The base ``preference`` property already exposes the
   estimated profile, so a separate property implementation is unnecessary.
3. Keep ``set_deadline(deadline_round)`` callable before observations. If you
   override it, accept ``None`` for the default horizon and preserve positive
   integer validation. Initialize any state that the override needs before
   calling the base constructor, which also calls ``set_deadline``.
4. Put the model in an importable module and select, for example,
   ``my_models.MyModel`` in ``estimators``. Begin on a small bundled domain;
   inspect utilities before updates, after an offer, and after a repeated offer.
   Keep the opponent's true profile in assessment code, outside the learning
   update.

``ClassicFrequencyOpponentModel`` is a compact existing implementation to read
alongside the API below. :doc:`components` describes the other built-in choices.
Document the assumptions behind initialization and updates when contributing
a new model; a successful run alone does not establish estimation quality.

Preference initialization
-------------------------

``EstimatedPreference`` is abstract. Instantiate
``UniformEstimatedPreference(reference)`` for equal issue/value weights or
``CBOMEstimatedPreference(reference)`` for inverse own-preference weights.
Custom subclasses implement ``initialize_weights(reference)``. Uniform issue
weights sum to one; equal value weights are max-normalized to one, so an
unobserved uniform preference gives every bid utility one.

The base model defaults to ``mode="uniform"``. Choosing ``mode="cbom"`` changes
that initialization assumption; it does not restore every behavior of older
versions. Existing agent and model policy changes are listed in the repository's
``MAINTENANCE.md``.

Deadlines and observation
-------------------------

Construct standalone models with a reference preference. The base class exposes
``set_deadline(deadline_round)``; session setup calls it before observations.
Round-limited and mixed sessions use the actual positive integer round limit.
Time-only sessions and standalone models use 1000 when no round limit is supplied.
No environment variable is required.

An agent's configured estimators receive every incoming offer. Adding a model to
the tournament's ``estimators`` list does not automatically make the strategy
use that estimate to choose bids.

Metrics
-------

.. code-block:: python

   from nenv import Preference
   from nenv.OpponentModel import BayesianOpponentModel

   own = Preference("domains/domain0/profileA.json")
   truth = Preference("domains/domain0/profileB.json")
   model = BayesianOpponentModel(own, deadline_round=20)
   model.update(truth.bids[0], t=0.0)
   rmse, spearman, kendall = model.calculate_error(truth)
   extra = model.calculate_additional_metrics(truth, pearson=True, mape=True)

The existing ``calculate_error`` tuple has exactly three values. Rank
correlations compare utilities of the same bids and retain ties. A constant
vector has undefined rank correlation (``NaN``). Pearson and percentage MAPE
are optional named statistics; zero true utilities produce ``NaN`` MAPE by
default, or a ``ValueError`` with ``zero_utility="raise"``.

``vectorized=True`` requests the optional additive batch path. Customized
utility/iteration implementations fall back to scalar evaluation. No persistent
utility or bid encoding cache is created.

Built-in choices
----------------

The nine registered models are Classic Frequency, Windowed Frequency, Bayesian,
Conflict Based, CUHK, the CUHK frequency adapter, and Stepwise/Expectation/
Regression COMB. Their exact Python class names appear in the API below.
Windowed Frequency uses a 25-offer window. The three COMB variants respectively
compare consecutive offers, historical mean utility, and time/utility regression.

``CUHKOpponentModel`` continues counting beyond 100 distinct bids.
``CUHKFrequencyOpponentModel`` follows the existing CUHK agent helper: the 101st
distinct bid stops further value-count updates. Both expose equal issue weights;
neither is the full CUHKAgent policy or an alias for the other model.

Bayesian normalized-utility queries use the current hypothesis distribution.
Finite tied predictions return zero without disabling later learning. This is
different from the undefined rank correlation of a constant utility vector.

API
---

.. autoclass:: nenv.OpponentModel.AbstractOpponentModel
   :members: name, update, preference, initialize_preference, set_deadline, calculate_error, calculate_additional_metrics

.. autoclass:: nenv.OpponentModel.EstimatedPreference
   :members: initialize_weights, normalize

.. autoclass:: nenv.OpponentModel.UniformEstimatedPreference

.. autoclass:: nenv.OpponentModel.CBOMEstimatedPreference

.. autoclass:: nenv.OpponentModel.ClassicFrequencyOpponentModel

.. autoclass:: nenv.OpponentModel.WindowedFrequencyOpponentModel

.. autoclass:: nenv.OpponentModel.BayesianOpponentModel
   :members: getNormalizedUtility

.. autoclass:: nenv.OpponentModel.ConflictBasedOpponentModel

.. autoclass:: nenv.OpponentModel.CUHKOpponentModel

.. autoclass:: nenv.OpponentModel.CUHKFrequencyOpponentModel

.. autoclass:: nenv.OpponentModel.StepwiseCOMBOpponentModel

.. autoclass:: nenv.OpponentModel.ExpectationCOMBOpponentModel

.. autoclass:: nenv.OpponentModel.RegressionCOMBOpponentModel
