"""Generic utility fixtures for the public opponent-model assessment API."""
import math
import random
from types import SimpleNamespace

import pytest

from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel


class TableModel(AbstractOpponentModel):
    def __init__(self, estimates):
        self._pref = SimpleNamespace(get_utility=lambda bid: estimates[bid.key])

    @property
    def name(self):
        return 'TableModel'

    def update(self, bid, t):
        pass


def reference(utilities, order=None):
    order = range(len(utilities)) if order is None else order
    return SimpleNamespace(bids=[SimpleNamespace(key=i, utility=utilities[i]) for i in order])


@pytest.mark.parametrize('order', [(0, 1, 2, 3), (0, 1, 3, 2), (2, 0, 3, 1)])
def test_correlations_follow_utilities_not_bid_identifiers(order):
    model = TableModel([.8, .4, 1., .6])
    rmse, spearman, kendall = model.calculate_error(reference([1., .8, .6, .4], order))
    assert rmse == pytest.approx(math.sqrt(.1))
    assert spearman == pytest.approx(0.)
    assert kendall == pytest.approx(0.)


def test_tied_utilities_use_tied_ranks():
    _, spearman, kendall = TableModel([1., 1., 0.]).calculate_error(reference([1., .5, 0.]))
    assert spearman == pytest.approx(math.sqrt(3) / 2)
    assert kendall == pytest.approx(math.sqrt(2 / 3))


@pytest.mark.parametrize('true,estimated', [([1., .5, 0.], [1., 1., 1.]), ([1., 1., 1.], [1., .5, 0.]), ([1.], [1.])])
def test_constant_or_single_bid_rank_is_undefined(true, estimated):
    rmse, spearman, kendall = TableModel(estimated).calculate_error(reference(true))
    assert math.isfinite(rmse)
    assert math.isnan(spearman)
    assert math.isnan(kendall)


def test_disabled_metrics_preserve_three_value_api_and_rng():
    random.seed(73)
    before = random.getstate()
    result = TableModel([.2, .8]).calculate_error(reference([1., 0.]), False, False, False)
    assert result == (None, None, None)
    assert random.getstate() == before
    TableModel([.2, .8]).calculate_error(reference([1., 0.]))
    assert random.getstate() == before


@pytest.mark.parametrize('estimate,expected', [([1., .5, 0.], 1.), ([0., .5, 1.], -1.)])
def test_perfect_and_reversed_order(estimate, expected):
    _, spearman, kendall = TableModel(estimate).calculate_error(reference([1., .5, 0.]))
    assert spearman == pytest.approx(expected)
    assert kendall == pytest.approx(expected)
