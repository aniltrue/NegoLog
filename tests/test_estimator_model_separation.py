"""Real Excel inputs and captured plot data for generic logger regressions."""
from nenv.logger.EstimatorMetricLogger import EstimatorMetricLogger
from nenv.utils.ExcelLog import ExcelLog


def test_multiple_models_remain_separate(tmp_path):
    (tmp_path / 'sessions').mkdir()
    session = ExcelLog(['Session', 'First', 'Second'])
    for round_number in range(2):
        row = {'Session': {'Action': 'Offer', 'Round': round_number}}
        for name, offset in [('First', 1.), ('Second', 10.)]:
            row[name] = {'RMSE_A': offset, 'RMSE_B': offset + 1,
                         'SpearmanA': offset + 2, 'SpearmanB': offset + 3,
                         'KendallTauA': offset + 4, 'KendallTauB': offset + 5}
        session.append(row)
    session.save(str(tmp_path / 'sessions/A_B_Domain1.xlsx'))
    tournament = ExcelLog(['TournamentResults'])
    tournament.append({'TournamentResults': {'AgentA': 'A', 'AgentB': 'B', 'DomainName': '1', 'Round': 1}})
    rmse, spearman, kendall = EstimatorMetricLogger(str(tmp_path)).get_estimator_results(tournament, ['First', 'Second'])
    assert rmse == {'First': [[1., 2.], [1., 2.]], 'Second': [[10., 11.], [10., 11.]]}
    assert spearman['First'][0] == [3., 4.]
    assert spearman['Second'][0] == [12., 13.]
    assert kendall['First'][0] == [5., 6.]
    assert kendall['Second'][0] == [14., 15.]
