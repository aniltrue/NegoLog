"""Synthetic preference and offer histories for the opponent-model API."""
import json
import math

import numpy as np
import pytest

from nenv import Preference
from nenv.OpponentModel import (
    AbstractOpponentModel,
    BayesianOpponentModel,
    CBOMEstimatedPreference,
    ClassicFrequencyOpponentModel,
    ConflictBasedOpponentModel,
    CUHKOpponentModel,
    EstimatedPreference,
    ExpectationCOMBOpponentModel,
    RegressionCOMBOpponentModel,
    StepwiseCOMBOpponentModel,
    UniformEstimatedPreference,
    WindowedFrequencyOpponentModel,
)


MODELS = (
    ClassicFrequencyOpponentModel, WindowedFrequencyOpponentModel,
    BayesianOpponentModel, ConflictBasedOpponentModel, CUHKOpponentModel,
    StepwiseCOMBOpponentModel, ExpectationCOMBOpponentModel,
    RegressionCOMBOpponentModel,
)
DEADLINE_MODELS = (
    BayesianOpponentModel, WindowedFrequencyOpponentModel,
    StepwiseCOMBOpponentModel, ExpectationCOMBOpponentModel,
    RegressionCOMBOpponentModel,
)


@pytest.fixture
def profile_factory(tmp_path):
    def make(issues=None, weights=None):
        path = tmp_path / "profile.json"
        path.write_text(json.dumps({
            "reservationValue": 0,
            "issueWeights": weights or {"color": .7, "size": .3},
            "issues": issues or {
                "color": {"red": 1., "blue": .2},
                "size": {"small": .2, "medium": .6, "large": 1.},
            },
        }))
        return Preference(str(path))
    return make


def weights_of(preference):
    return ([preference[issue] for issue in preference.issues] +
            [preference[issue, value]
             for issue in preference.issues for value in issue.values])


def assert_normalized(preference, bids):
    assert all(math.isfinite(weight) and weight >= 0 for weight in weights_of(preference))
    assert sum(preference[issue] for issue in preference.issues) == pytest.approx(1.)
    for issue in preference.issues:
        assert max(preference[issue, value] for value in issue.values) == pytest.approx(1.)
    for bid in bids:
        utility = preference.get_utility(bid)
        assert math.isfinite(utility) and 0 <= utility <= 1. + 1e-12


class ConfigurableModel(AbstractOpponentModel):
    @property
    def name(self):
        return "Configurable model"

    def update(self, bid, t):
        pass


def test_preference_initializers_are_explicit_and_do_not_mutate_reference(profile_factory):
    reference = profile_factory()
    original_weights = reference.issue_weights
    original_values = reference.value_weights
    with pytest.raises(TypeError):
        # Instantiation must fail: this is the abstract API's negative test.
        EstimatedPreference(reference)  # pylint: disable=abstract-class-instantiated
    uniform = UniformEstimatedPreference(reference)
    inverse = CBOMEstimatedPreference(reference)
    assert weights_of(uniform) == pytest.approx([.5, .5, 1., 1., 1., 1., 1.])
    assert weights_of(inverse) == pytest.approx([.3, .7, 0., 1., 1., .5, 0.])
    assert isinstance(ConfigurableModel(reference).preference, UniformEstimatedPreference)
    assert isinstance(ConfigurableModel(reference, mode="cbom").preference, CBOMEstimatedPreference)
    assert reference.issue_weights == original_weights
    assert reference.value_weights == original_values


@pytest.mark.parametrize("mode", ["", "unknown", None, [], 1])
def test_unknown_preference_initializer_is_rejected(profile_factory, mode):
    with pytest.raises(ValueError, match="Unknown preference initialization mode"):
        ConfigurableModel(profile_factory(), mode=mode)


@pytest.mark.parametrize("preference_class", [UniformEstimatedPreference, CBOMEstimatedPreference])
def test_zero_weights_and_single_value_normalize(profile_factory, preference_class):
    reference = profile_factory({"only": {"value": 1.}}, {"only": 1.})
    estimate = preference_class(reference)
    assert_normalized(estimate, reference.bids)
    estimate["only"] = 0.
    estimate["only", "value"] = 0.
    estimate.normalize()
    assert weights_of(estimate) == [1., 1.]


@pytest.mark.parametrize("model_class", MODELS)
def test_standalone_model_ignores_process_deadline_environment(profile_factory, monkeypatch, model_class):
    monkeypatch.delenv("DEADLINE_ROUND", raising=False)
    model = model_class(profile_factory())
    assert model.deadline_round == 1000
    monkeypatch.setenv("DEADLINE_ROUND", "not-a-number")
    assert model_class(profile_factory()).deadline_round == 1000
    model.set_deadline(np.int64(30))
    assert model.deadline_round == 30
    model.set_deadline(None)
    assert model.deadline_round == 1000


@pytest.mark.parametrize("model_class", DEADLINE_MODELS)
@pytest.mark.parametrize("deadline", [0, -1, True, 2.5, "1000"])
def test_invalid_deadline_is_rejected_at_construction(profile_factory, model_class, deadline):
    with pytest.raises(ValueError, match="positive integer or None"):
        model_class(profile_factory(), deadline_round=deadline)


def test_set_deadline_works_for_custom_constructor_and_updates_window(profile_factory):
    class LegacyConstructor(ConfigurableModel):
        def __init__(self):
            """Exercise a legacy constructor that omits base initialization."""

    legacy = LegacyConstructor()
    legacy.set_deadline(17)
    assert legacy.deadline_round == 17
    model = RegressionCOMBOpponentModel(profile_factory(), deadline_round=1)
    assert model.compact_gate == 1
    model.set_deadline(20)
    assert model.compact_gate == 2
    model.set_deadline(None)
    assert model.compact_gate == 100
    with pytest.raises(ValueError):
        model.set_deadline(0)
    assert model.deadline_round == 1000


@pytest.mark.parametrize("model_class", MODELS)
@pytest.mark.parametrize("single_value", [False, True])
def test_models_stay_finite_for_repeated_offers_and_single_value_domains(profile_factory, model_class, single_value):
    reference = (profile_factory({"only": {"value": 1.}}, {"only": 1.})
                 if single_value else profile_factory())
    model = model_class(reference)
    assert_normalized(model.preference, reference.bids)
    # Cross both 25-offer windows and include repeated offers.
    for step in range(55):
        bid = reference.bids[(step // 3) % len(reference.bids)]
        model.update(bid, step / 100)
        assert_normalized(model.preference, reference.bids)


def test_bayesian_deadline_decrement_counts_distinct_offers_and_stays_positive(profile_factory):
    reference = profile_factory()
    model = BayesianOpponentModel(reference, deadline_round=1)
    model.update(reference.bids[0], 0.)
    assert model.fPreviousBidUtility == pytest.approx(.1)
    model.update(reference.bids[0], .1)
    assert model.fPreviousBidUtility == pytest.approx(.1)
    for bid in reference.bids[1:]:
        model.update(bid, 1.)
        assert model.fPreviousBidUtility > 0
        assert_normalized(model.preference, reference.bids)


def test_cuhk_counts_repeats_while_conflict_model_ignores_identical_comparisons(profile_factory):
    reference = profile_factory()
    bid = reference.bids[0]
    cuhk = CUHKOpponentModel(reference)
    conflict = ConflictBasedOpponentModel(reference)
    for step in range(4):
        cuhk.update(bid, step / 10)
        conflict.update(bid, step / 10)
    assert len(cuhk._bidHistory) == 1
    assert cuhk._opponentBidsStatisticsForDiscrete[0][bid[reference.issues[0]]] == 4
    assert len(conflict.opponent_offer_history) == 4
    assert conflict.CM == []


EXPECTED_HISTORY_WEIGHTS = {
    ClassicFrequencyOpponentModel: [.5317460317460317, .4682539682539683, 1., .6, .75, .5, 1.],
    WindowedFrequencyOpponentModel: [.5, .5, 1., .8801117367933934, .9306048591020994, .8408964152537145, 1.],
    BayesianOpponentModel: [.5027298335049155, .4972701664950845, 1., .12242347369860777, .6731571397402853, .8367558793003245, 1.],
    ConflictBasedOpponentModel: [2 / 3, 1 / 3, 1., .5, 2 / 3, 1 / 3, 1.],
    CUHKOpponentModel: [.5, .5, 1., .5, 2 / 3, 1 / 3, 1.],
    StepwiseCOMBOpponentModel: [.5041769791355184, .4958230208644816, 1., .7679726861843559, .842551959761204, .6345657138944828, 1.],
    ExpectationCOMBOpponentModel: [.5172730640651894, .4827269359348106, 1., .8911426520024285, .884340662964962, .7920271857254296, 1.],
    RegressionCOMBOpponentModel: [.5052806906173192, .4947193093826808, 1., .7116111377165498, .7698260614573089, .6232067391867571, 1.],
}


@pytest.mark.parametrize("model_class", MODELS)
def test_fixed_offer_history_has_stable_preference_output(profile_factory, model_class):
    reference = profile_factory()
    model = model_class(reference)
    for step, index in enumerate([0, 0, 2, 3, 1, 5]):
        model.update(reference.bids[index], step / 10)
    assert weights_of(model.preference) == pytest.approx(EXPECTED_HISTORY_WEIGHTS[model_class], rel=1e-10, abs=1e-10)
