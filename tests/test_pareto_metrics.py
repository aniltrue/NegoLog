"""Set membership fixtures exercise precision and recall independently."""
import pytest
from nenv.logger.EstimatedParetoLogger import EstimatedParetoLogger


def test_precision_and_recall_have_distinct_denominators(tmp_path):
    logger = EstimatedParetoLogger(str(tmp_path))
    logger.real_pareto = ['a', 'b', 'c']
    precision, recall, f1 = logger.calculate_error(['a', 'x'])
    assert precision == pytest.approx(1 / 2)
    assert recall == pytest.approx(1 / 3)
    assert f1 == pytest.approx(2 / 5)


@pytest.mark.parametrize('real,estimated', [(['a'], ['b']), (['a'], []), ([], ['b']), ([], [])])
def test_disjoint_and_empty_frontiers_have_zero_scores(tmp_path, real, estimated):
    logger = EstimatedParetoLogger(str(tmp_path))
    logger.real_pareto = real
    assert logger.calculate_error(estimated) == (0., 0., 0.)
