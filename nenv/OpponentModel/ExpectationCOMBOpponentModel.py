import numpy as np
from functools import wraps
from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from nenv.Preference import Preference
from nenv.Bid import Bid

NUMPY_TYPE = 'float64'


def likelihood_none_zero(likelihood_cal):
    @wraps(likelihood_cal)
    def wraplikelihood(*args, **kw):
        likelihood = likelihood_cal(*args, **kw)
        if likelihood.max() == 0:
            likelihood[:] = 1
        likelihood = (likelihood.shape[0] * likelihood) / likelihood.sum()
        return likelihood.astype(NUMPY_TYPE)
    return wraplikelihood


class weight_space:

    def __init__(self, reference: Preference, num_hypothesis=11) -> None:
        self.num_issues = len(reference.issues)
        self.num_hypothesis = num_hypothesis
        self.h_space = None
        self.h_probs = None
        self.expectation = None
        self.temp_h_probs = None

        self.issue_values_range = {}
        self.issue_num_values = {}
        _i = 0
        _ii = 0
        for k in range(len(reference.issues)):
            self.issue_values_range[k] = [_ii]
            _i = len(reference.issues[k].values)
            self.issue_num_values[k] = _i
            _ii = _ii + _i
            self.issue_values_range[k].append(_ii)
        self.num_values = _ii

        self.initial_expectation_mode()
        self.initial_sapce()
        self.accume = self.get_expectation()

    def initial_sapce(self):
        Hs, Ps = self.Grid_First_decopuled_WHS()
        self.h_space = Hs
        self.h_probs = Ps.copy()
        self.initial_h_probs = Ps.copy()

    def flatten_weights_HS(self, W_Hspace):
        len_E_HS = self.num_values
        weights_flatten = np.ones([W_Hspace.shape[0], len_E_HS], dtype=NUMPY_TYPE)
        for i in range(self.num_issues):
            range_se = self.issue_values_range[i]
            range_s = range_se[0]
            range_e = range_se[1]
            repeat_times = self.issue_num_values[i]
            weights_flatten[:, range_s:range_e] = np.repeat(W_Hspace[:, i].reshape([-1, 1]), repeat_times, axis=1)
        return weights_flatten

    def initial_expectation_mode(self):
        self.get_expectation = self._get_expectation_1

    def _get_expectation_1(self):
        accume_w = (self.h_space * self.h_probs).sum(axis=1) / self.h_probs.sum(axis=1)
        sum_w = accume_w.sum()
        accume_w = accume_w / sum_w
        return accume_w

    def update_accume(self):
        self.accume = self.get_expectation()

    def expectation_except_issue_i(self, issue_i):
        wh_issue_i = self.h_space[issue_i, :]
        expectation = np.copy(self.accume)
        expectation = expectation.reshape([1, -1]).repeat(repeats=wh_issue_i.shape[0], axis=0)
        expectation[:, issue_i] = wh_issue_i
        return expectation

    def Grid_First_decopuled_WHS(self):
        weights_HS = np.linspace(0, 1, self.num_hypothesis).reshape([1, -1]).repeat(axis=0, repeats=self.num_issues)
        WH_probs = np.ones_like(weights_HS)
        return weights_HS, WH_probs


class evaluation_space:

    def __init__(self, reference: Preference, num_hypothesis=11) -> None:
        self.h_space = None
        self.h_probs = None
        self.expectation = None
        self.num_values = None
        self.issue_num_values = {}
        self.issue_values_range = {}
        self.num_issues = len(reference.issues)

        _i = 0
        _ii = 0
        for k in range(len(reference.issues)):
            self.issue_values_range[k] = [_ii]
            _i = len(reference.issues[k].values)
            self.issue_num_values[k] = _i
            _ii = _ii + _i
            self.issue_values_range[k].append(_ii)
        self.num_values = _ii

        self.num_hypothesis = num_hypothesis

        self.initial_expectation_mode()
        self.initial_sapce()
        self.accume = self.get_expectation()

    def initial_sapce(self):
        Hs, Ps = self.Second_decopuled_EHS_mean()
        self.h_space = Hs
        self.h_probs = Ps.copy()
        self.initial_h_probs = Ps.copy()

    def Second_decopuled_EHS_mean(self):
        num_values = self.num_values
        Hs = np.linspace(0, 1, self.num_hypothesis).reshape([1, -1]).repeat(axis=0, repeats=num_values).astype(
            NUMPY_TYPE)
        Ps = np.ones_like(Hs)
        return Hs, Ps

    def initial_expectation_mode(self):
        self.get_expectation = self._get_expectation_2b

    def _get_expectation_2b(self):
        accume_e = (self.h_space * self.h_probs).sum(axis=1) / self.h_probs.sum(axis=1)
        return accume_e

    def update_accume(self):
        self.accume = self.get_expectation()

    def expectation_except_issue_i(self, issue_i):
        h_issue_i = self.h_space[issue_i]
        expectation = np.copy(self.accume)
        expectation = expectation.reshape([1, -1]).repeat(repeats=h_issue_i.shape[0], axis=0)
        value_range = self.issue_values_range[issue_i]
        expectation[:, value_range[0]:value_range[1]] = h_issue_i
        return expectation

    def expectation_except_issue_i_value_j_rank(self, issue_i, value_j):
        h_issue_i_value_j = self.h_space[issue_i][value_j, :]
        expectation = np.copy(self.accume)
        expectation = expectation.reshape([1, -1]).repeat(repeats=h_issue_i_value_j.shape[0], axis=0)
        value_range = self.issue_values_range[issue_i]
        value_start = value_range[0]
        value_update = value_start + value_j
        expectation[:, value_update] = h_issue_i_value_j
        return expectation

    def expectation_except_issue_i_value_j_mean(self, faltten_value_j):
        h_issue_i_value_j = self.h_space[faltten_value_j, :]
        expectation = np.copy(self.accume)
        expectation = expectation.reshape([1, -1]).repeat(repeats=h_issue_i_value_j.shape[0], axis=0)
        expectation[:, faltten_value_j] = h_issue_i_value_j
        return expectation


class ExpectationCOMBOpponentModel(AbstractOpponentModel):
    """
        **Expectation COMB Opponent Model**:
            This model uses Bayesian learning with decoupled hypothesis spaces for weights and evaluations.
            The expectation variant compares the newest bid to the mean of all previous bids.
    """

    def __init__(self, reference: Preference, deadline_round=None):
        super().__init__(reference, deadline_round=deadline_round)

        self.SIGMA = 0.15
        self.compact_gate = 500

        # Calculate num_outcomes
        self.num_outcomes = 1
        for issue in reference.issues:
            self.num_outcomes *= len(issue.values)

        self.bids_history = []
        self.onehot_bids_history = None
        self.onehot_bids_history_origin = None
        self.time_sequence = np.array([], dtype=NUMPY_TYPE)
        self.time_sequence_origin = np.array([], dtype=NUMPY_TYPE)

        self.times_i = 0
        self.first_update = 1

        self.issues = []
        self.values = {}
        self.issue_num = {}
        self.value_num_issue = {}
        self.issue_value_num_flatten = {}
        self.issueID_valueID_flatten = {}
        self.num_issues = len(reference.issues)
        _i = 0
        _iii = 0
        self.weights_range = {}
        for k in reference.issues:
            k_name = k.name
            k_values = k.values
            self.issues.append(k_name)
            self.values[k_name] = k_values
            self.issue_num[k_name] = _i
            self.issue_value_num_flatten[_i] = {}
            self.weights_range[_i] = []
            self.value_num_issue[_i] = {}
            self.issueID_valueID_flatten[_i] = {}
            _ii = 0
            for v in k_values:
                self.value_num_issue[_i][v] = _ii
                self.issueID_valueID_flatten[_i][_ii] = _iii
                _ii = _ii + 1
                self.issue_value_num_flatten[_i][v] = _iii
                self.weights_range[_i].append(_iii)
                _iii = _iii + 1
            _i = _i + 1
        self.num_values = _iii

        self.weights = weight_space(reference=reference)
        self.evaluations = evaluation_space(reference=reference)

        self.update_weights = self.update_weights_v1
        self.update_evaluations = self.update_evaluations_v2b

        self.update_func = self._first_update_func
        self.likelihood_func = self._first_likelihood_func

        self.compact_bids_times = self._compact_bids_times_None

    @property
    def name(self) -> str:
        return "Expectation COMB Opponent Model"

    def flatten_weights_HS(self, W_Hspace):
        len_E_HS = self.num_values
        weights_flatten = np.ones([W_Hspace.shape[0], len_E_HS], dtype=NUMPY_TYPE)
        for i in range(self.num_issues):
            range_repeat = self.weights_range[i]
            repeat_times = len(range_repeat)
            weights_flatten[:, range_repeat] = np.repeat(W_Hspace[:, i].reshape([-1, 1]), repeat_times, axis=1)
        return weights_flatten

    def update_weights_v1(self, accume_e):
        for i in range(self.weights.num_issues):
            hs_i = self.weights.expectation_except_issue_i(i)
            hs_i_flatten = self.flatten_weights_HS(hs_i)
            ufun_flatten = hs_i_flatten * accume_e
            Ls = self.likelihood_func(ufun_flatten)
            h_probs_i = self.weights.h_probs[i, :] * Ls

            prob_sum = h_probs_i.sum()
            if prob_sum != 0:
                self.weights.h_probs[i, :] = (h_probs_i * h_probs_i.size) / prob_sum
            else:
                self.weights.h_probs[i, :] = np.ones_like(h_probs_i)

            self.weights.update_accume()

    def update_evaluations_v2b(self, accume_w_flatten):
        for j in range(self.num_values):
            hs_j = self.evaluations.expectation_except_issue_i_value_j_mean(j)
            ufun_j = hs_j * accume_w_flatten
            Ls = self.likelihood_func(ufun_j)
            h_probs_j = self.evaluations.h_probs[j, :] * Ls

            sum_prob = h_probs_j.sum()
            if sum_prob != 0:
                self.evaluations.h_probs[j, :] = (h_probs_j * h_probs_j.size) / sum_prob
            else:
                self.evaluations.h_probs[j, :] = np.ones_like(h_probs_j)

            self.evaluations.update_accume()

    def _update_base(self, offer):
        offer_onehot = self.offer_2_onehot(offer)
        self.onehot_bids_history_origin = np.append(self.onehot_bids_history_origin, offer_onehot.reshape([1, -1]),
                                                     axis=0)
        self.bids_history.append(offer)
        self.update_time_sequence()
        self.compact_bids_times()

    def _compact_bids_times_None(self):
        self.onehot_bids_history = self.onehot_bids_history_origin
        self.time_sequence = self.time_sequence_origin

    def _update_base_first(self, offer):
        offer_onehot = self.offer_2_onehot(offer)
        self.onehot_bids_history_origin = offer_onehot.reshape([1, -1])
        self.onehot_bids_history = self.onehot_bids_history_origin

        self.not_proposed = np.ones(self.num_values) * self.num_outcomes / 2
        self.not_proposed = self.not_proposed - offer_onehot
        self.num_unproposed = self.num_outcomes - 1

        self.bids_history.append(offer)
        self.first_update_time_sequence()
        self.time_sequence = self.time_sequence_origin

    def update_Sequence(self, offer, t):
        self._update_base(offer)

        accume_e = self.evaluations.accume.reshape([1, -1])
        self.update_weights(accume_e=accume_e)
        self.weights.update_accume()

        accume_w_flatten = self.flatten_weights_HS(self.weights.accume.reshape([1, -1]))
        self.update_evaluations(accume_w_flatten=accume_w_flatten)
        self.evaluations.update_accume()

        self.update_accumed_ufun()

    def _first_update_func(self, offer, t):
        self._update_base_first(offer)

        accume_e = self.evaluations.accume.reshape([1, -1])
        self.update_weights(accume_e=accume_e)
        accume_w_flatten = self.flatten_weights_HS(self.weights.accume.reshape([1, -1]))
        self.update_evaluations(accume_w_flatten=accume_w_flatten)
        self.update_accumed_ufun()

        self.evaluations.initial_h_probs = self.evaluations.h_probs
        self.weights.initial_h_probs = self.weights.h_probs
        self.first_update = 0

        self.update_func = self.update_Sequence
        self.likelihood_func = self._likelihood_func

    def offer_2_onehot(self, bid: Bid):
        offer_onehot = np.zeros(self.num_values, dtype='int')
        for issue_idx, issue in enumerate(self._pref.issues):
            value = bid[issue]
            loc_value = self.issue_value_num_flatten[issue_idx][value]
            offer_onehot[loc_value] = 1
        return offer_onehot

    def update_time_sequence(self):
        t_i = self.times_i / self.deadline_round
        self.time_sequence_origin = np.append(self.time_sequence_origin, t_i)
        self.times_i = self.times_i + 1

    def first_update_time_sequence(self):
        t_i = self.times_i / self.deadline_round
        self.time_sequence_origin = np.array([t_i])
        self.times_i = self.times_i + 1

    def update_accumed_ufun(self):
        evaluations = self.evaluations.accume
        flatten_weights = self.flatten_weights_HS(self.weights.accume.reshape([1, -1])).reshape([-1])
        self.accume_ufun = flatten_weights * evaluations

    @likelihood_none_zero
    def _first_likelihood_func(self, ufuns):
        sigma = self.SIGMA
        first_bid = self.onehot_bids_history[0, :]
        estimated_utilities = (ufuns * first_bid).sum(axis=1)
        delta = estimated_utilities - 1
        delta[np.where(delta >= 0)] = 0
        likelihood = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-(delta * delta) / (2 * sigma * sigma))
        return likelihood

    @likelihood_none_zero
    def _likelihood_func(self, ufuns):
        sigma = self.SIGMA
        bids_till_now = self.onehot_bids_history
        previous_expected_bid = bids_till_now[:-1, :].mean(axis=0)
        newest_bid = bids_till_now[-1, :]

        diff_bid = newest_bid - previous_expected_bid
        CIM_single_step = (ufuns * diff_bid).sum(axis=1)

        CIM_single_step[np.where((-0.1 <= CIM_single_step) & (CIM_single_step <= 0))] = 0
        likelihood_single = 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(-(CIM_single_step ** 2) / (2 * sigma * sigma))
        return likelihood_single

    def update(self, bid: Bid, t: float):
        self.update_func(bid, t)

    @property
    def preference(self) -> EstimatedPreference:
        # Map accumulated weights to issue weights
        accume_weights = self.weights.accume
        for i, issue in enumerate(self._pref.issues):
            self._pref[issue] = accume_weights[i]

        # Map accumulated evaluations to value weights
        accume_evaluations = self.evaluations.accume
        for i, issue in enumerate(self._pref.issues):
            value_range = self.evaluations.issue_values_range[i]
            for j, value in enumerate(issue.values):
                flat_idx = value_range[0] + j
                self._pref[issue, value] = accume_evaluations[flat_idx]

        self._pref.normalize()

        return self._pref
