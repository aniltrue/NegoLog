"""Additive batch evaluation must preserve public customization and mutation."""
import json
import random
from types import MethodType, SimpleNamespace

import numpy as np
import pytest

from nenv import Bid, EditablePreference, Preference
from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.OpponentModel.CBOMEstimatedPreference import CBOMEstimatedPreference
from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from nenv.OpponentModel.UniformEstimatedPreference import UniformEstimatedPreference
from nenv.utils.utility_metrics import utility_pairs


class Model(AbstractOpponentModel):
    def __init__(self, preference):
        """Use the supplied preference to exercise assessment customization."""
        self._pref = preference

    @property
    def name(self):
        return "Model"

    def update(self, bid, t):
        pass


def preferences():
    reference = EditablePreference({"color": .7, "size": .3},
        {"color": {"red": 1., "blue": .2}, "size": {"small": .2, "medium": .6, "large": 1.}})
    estimate = EditablePreference({"color": .2, "size": .8},
        {"color": {"red": .2, "blue": 1.}, "size": {"small": 1., "medium": .5, "large": .2}})
    return reference, estimate


def assert_matches(reference, estimate):
    slow = utility_pairs(reference, estimate)
    fast = utility_pairs(reference, estimate, vectorized=True)
    np.testing.assert_array_equal(fast, slow)
    model = Model(estimate)
    assert model.calculate_error(reference, vectorized=True) == pytest.approx(model.calculate_error(reference), nan_ok=True)


def test_batch_metrics_equal_scalar_and_do_not_consume_rng():
    reference, estimate = preferences()
    before = random.getstate()
    assert_matches(reference, estimate)
    assert random.getstate() == before


def test_no_stale_state_after_weight_content_utility_or_bid_order_edits():
    reference, estimate = preferences()
    assert_matches(reference, estimate)
    estimate["color"] = .9
    estimate["size", "medium"] = .25
    assert_matches(reference, estimate)
    reference._bids.reverse()
    reference._bids[0].utility = .33
    reference._bids[0].content["color"] = "red"
    assert_matches(reference, estimate)
    reference._bids = reference._bids[::2]
    assert_matches(reference, estimate)


def test_instance_override_is_called_instead_of_additive_fast_path():
    reference, estimate = preferences()
    calls = []

    def custom(self, bid):
        calls.append(bid)
        return .42

    estimate.get_utility = MethodType(custom, estimate)
    true, values = utility_pairs(reference, estimate, vectorized=True)
    assert len(calls) == len(reference.bids)
    assert values.tolist() == [.42] * len(true)


def test_custom_subclass_utility_is_respected():
    class Custom(EditablePreference):
        def get_utility(self, bid):
            return .73

    reference, _ = preferences()
    custom = Custom({"color": 1.}, {"color": {"red": 1., "blue": .5}})
    _, values = utility_pairs(reference, custom, vectorized=True)
    assert values.tolist() == [.73] * len(reference.bids)


def test_different_bid_iteration_orders_fall_back_without_roundoff_change():
    reference, estimate = preferences()
    reference._bids[0].content = dict(reversed(list(reference._bids[0].content.items())))
    assert_matches(reference, estimate)


def test_nonstandard_bid_iterator_is_respected():
    reference, estimate = preferences()

    class CustomBid(Bid):
        def __iter__(self):
            return iter([("color", "blue")])

    custom = CustomBid(reference.bids[0].content, .9)
    _, predicted = utility_pairs(SimpleNamespace(bids=[custom]), estimate, vectorized=True)
    assert predicted.tolist() == [estimate.get_utility(custom)]


def test_original_positional_metric_flags_and_three_tuple_remain_valid():
    reference, estimate = preferences()
    model = Model(estimate)
    assert model.calculate_error(reference, False, False, False) == (None, None, None)
    assert model.calculate_error(reference, False, False, False, vectorized=True) == (None, None, None)


def test_base_bid_iterator_override_is_respected(monkeypatch):
    reference, estimate = preferences()
    monkeypatch.setattr(Bid, "__iter__", lambda self: iter([("color", "blue")]))
    assert_matches(reference, estimate)


def test_float32_weights_keep_scalar_rounding():
    reference, estimate = preferences()
    for issue in estimate.issues:
        estimate[issue] = np.float32(.1234567)
        for value in issue.values:
            estimate[issue, value] = np.float32(.7654321)
    assert_matches(reference, estimate)


def test_custom_weight_view_does_not_override_additive_storage_semantics(monkeypatch):
    reference, estimate = preferences()
    monkeypatch.setattr(Preference, "issue_weights", property(
        lambda self: {issue: weight / 2 for issue, weight in self._issue_weights.items()}))
    assert_matches(reference, estimate)


def test_base_utility_override_before_lazy_module_import_is_respected():
    import os
    # Isolate import order in the current Python interpreter.
    import subprocess  # nosec B404
    import sys
    code = '''
from nenv import Preference, EditablePreference
Preference.get_utility = lambda self, bid: .42
from nenv.utils.utility_metrics import utility_pairs
pref = EditablePreference({'issue': 1.}, {'issue': {'a': 1., 'b': .5}})
assert utility_pairs(pref, pref, vectorized=True)[1].tolist() == [.42, .42]
'''
    # The executable and script are trusted test inputs; no shell is involved.
    subprocess.run([sys.executable, "-c", code], check=True,  # nosec B603
                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


@pytest.mark.parametrize("true,predicted,expected", [
    ([1., .5], [.5, .25], 50.), ([1., .5], [1., .5], 0.),
])
def test_additional_metrics_are_named_opt_in_and_mape_is_percent(true, predicted, expected):
    reference = SimpleNamespace(bids=[SimpleNamespace(key=i, utility=v) for i, v in enumerate(true)])
    model = Model(SimpleNamespace(get_utility=lambda bid: predicted[bid.key]))
    assert model.calculate_additional_metrics(reference) == {}
    result = model.calculate_additional_metrics(reference, pearson=True, mape=True)
    assert set(result) == {"Pearson", "MAPE"}
    assert result["Pearson"] == pytest.approx(1.)
    assert result["MAPE"] == pytest.approx(expected)
    assert len(model.calculate_error(reference)) == 3


@pytest.mark.parametrize("true,predicted", [([1., 0.], [1., .5]), ([0.], [0.])])
def test_zero_utility_is_explicit_and_never_dropped(true, predicted):
    reference = SimpleNamespace(bids=[SimpleNamespace(key=i, utility=v) for i, v in enumerate(true)])
    model = Model(SimpleNamespace(get_utility=lambda bid: predicted[bid.key]))
    assert np.isnan(model.calculate_additional_metrics(reference, mape=True)["MAPE"])
    with pytest.raises(ValueError, match="zero true utility"):
        model.calculate_additional_metrics(reference, mape=True, zero_utility="raise")


@pytest.mark.parametrize("true,predicted", [([1., 1.], [.8, .4]), ([1., .5], [.3, .3]), ([1.], [.5]), ([], [])])
def test_pearson_constant_singleton_and_empty_are_undefined(true, predicted):
    reference = SimpleNamespace(bids=[SimpleNamespace(key=i, utility=v) for i, v in enumerate(true)])
    model = Model(SimpleNamespace(get_utility=lambda bid: predicted[bid.key]))
    assert np.isnan(model.calculate_additional_metrics(reference, pearson=True)["Pearson"])


def test_extra_metric_invalid_policy_and_vectorized_equivalence():
    reference, estimate = preferences()
    model = Model(estimate)
    with pytest.raises(ValueError, match="zero_utility"):
        model.calculate_additional_metrics(reference, mape=True, zero_utility="drop")
    assert model.calculate_additional_metrics(reference, pearson=True, mape=True, vectorized=True) == pytest.approx(
        model.calculate_additional_metrics(reference, pearson=True, mape=True))


@pytest.fixture
def stored_reference(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "reservationValue": 0.,
        "issueWeights": {"color": .7, "size": .3},
        "issues": {"color": {"red": 1., "blue": .2},
                   "size": {"small": .2, "medium": .6, "large": 1.}},
    }))
    return Preference(str(path))


@pytest.mark.parametrize("preference_class", [UniformEstimatedPreference, CBOMEstimatedPreference])
def test_concrete_initializers_use_batch_without_changing_metrics_or_state(
        stored_reference, preference_class, monkeypatch):
    estimate = preference_class(stored_reference)
    before_issues = estimate.issue_weights
    before_values = estimate.value_weights
    column_calls = []
    original_fromiter = np.fromiter

    def counted_fromiter(*args, **kwargs):
        column_calls.append(True)
        return original_fromiter(*args, **kwargs)

    monkeypatch.setattr(np, "fromiter", counted_fromiter)
    assert_matches(stored_reference, estimate)
    assert column_calls, "Concrete additive preferences should use the optional batch path"
    model = Model(estimate)
    assert model.calculate_additional_metrics(
        stored_reference, pearson=True, mape=True, vectorized=True) == pytest.approx(
            model.calculate_additional_metrics(stored_reference, pearson=True, mape=True), nan_ok=True)
    assert estimate.issue_weights == before_issues
    assert estimate.value_weights == before_values

    estimate["color"] = .6
    estimate["size", "medium"] = .35
    estimate.normalize()
    stored_reference._bids.reverse()
    stored_reference._bids[0].utility = .33
    stored_reference._bids[0].content["color"] = "blue"
    assert_matches(stored_reference, estimate)


@pytest.mark.parametrize("preference_class", [UniformEstimatedPreference, CBOMEstimatedPreference])
def test_concrete_preference_instance_override_falls_back(stored_reference, preference_class):
    estimate = preference_class(stored_reference)
    calls = []

    def custom(self, bid):
        calls.append(bid)
        return .37

    estimate.get_utility = MethodType(custom, estimate)
    true, predicted = utility_pairs(stored_reference, estimate, vectorized=True)
    assert calls == stored_reference.bids
    np.testing.assert_array_equal(predicted, np.full(len(true), .37))


@pytest.mark.parametrize("preference_class", [UniformEstimatedPreference, CBOMEstimatedPreference])
def test_custom_initializer_subclass_uses_scalar_calls(stored_reference, preference_class, monkeypatch):
    class CustomPreference(preference_class):
        pass

    def unexpected_batch(*args, **kwargs):
        pytest.fail("Custom preference subclasses must retain scalar evaluation")

    estimate = CustomPreference(stored_reference)
    monkeypatch.setattr(np, "fromiter", unexpected_batch)
    assert_matches(stored_reference, estimate)


def test_optional_metrics_preserve_model_initialization_and_deadline_api(stored_reference):
    class ConfigurableModel(AbstractOpponentModel):
        @property
        def name(self):
            return "Configurable model"

        def update(self, bid, t):
            pass

    with pytest.raises(TypeError):
        # Instantiation must fail: this is the abstract API's negative test.
        EstimatedPreference(stored_reference)  # pylint: disable=abstract-class-instantiated
    default = ConfigurableModel(stored_reference)
    # The contract selects this exact implementation, not an arbitrary subclass.
    assert type(default.preference) is UniformEstimatedPreference  # pylint: disable=unidiomatic-typecheck
    assert default.deadline_round == 1000
    assert [default.preference[issue] for issue in default.preference.issues] == [.5, .5]
    inverse = ConfigurableModel(stored_reference, "cbom", 17)
    assert type(inverse.preference) is CBOMEstimatedPreference  # pylint: disable=unidiomatic-typecheck
    assert inverse.deadline_round == 17
    assert [inverse.preference[issue] for issue in inverse.preference.issues] == pytest.approx([.3, .7])
    assert len(inverse.calculate_error(stored_reference, vectorized=True)) == 3
    inverse.calculate_additional_metrics(stored_reference, pearson=True, mape=True, vectorized=True)
    assert inverse.deadline_round == 17
    inverse.initialize_preference(stored_reference, "uniform")
    assert type(inverse.preference) is UniformEstimatedPreference  # pylint: disable=unidiomatic-typecheck
    assert inverse.deadline_round == 17
    inverse.set_deadline(None)
    assert inverse.deadline_round == 1000
