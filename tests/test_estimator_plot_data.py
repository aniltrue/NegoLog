"""Real Excel inputs and captured plot data for generic logger regressions."""
import copy
import importlib

from nenv.logger.EstimatorMetricLogger import EstimatorMetricLogger


def test_median_plots_receive_truncated_means_without_mutating_inputs(tmp_path, monkeypatch):
    module = importlib.import_module('nenv.logger.EstimatorMetricLogger')
    plots = {}
    monkeypatch.setattr(module, 'draw_line', lambda data, path, *args: plots.update({path: copy.deepcopy(data)}))
    logger = EstimatorMetricLogger(str(tmp_path))
    rmse = {'First': [[1., 3.], [2., 4.], [6., 8.], [10., 12.]]}
    spearman = {'First': [[.1], [.2], [.3], [.4]]}
    kendall = {'First': [[.5], [.6], [.7], [.8]]}
    original = copy.deepcopy((rmse, spearman, kendall))
    logger.draw(rmse, spearman, kendall)
    assert (rmse, spearman, kendall) == original
    assert plots[logger.get_path('opponent model/estimator_rmse')]['First'] == [2., 3., 7., 11.]
    assert plots[logger.get_path('opponent model/estimator_rmse_until_median_round')]['First'] == [2., 3.]
    assert plots[logger.get_path('opponent model/estimator_spearman_until_median_round')]['First'] == [.1, .2]
    assert plots[logger.get_path('opponent model/estimator_kendall_tau_until_median_round')]['First'] == [.5, .6]
