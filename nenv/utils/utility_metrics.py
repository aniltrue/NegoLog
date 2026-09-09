"""Utility pairs for assessment, with optional additive batch evaluation."""
import numpy as np

from nenv.Bid import (Bid, IssueIterator, _STANDARD_BID_ITER,
                      _STANDARD_ISSUE_ITER_INIT, _STANDARD_ISSUE_ITER_NEXT)
from nenv.Preference import Preference, _ADDITIVE_GET_UTILITY


# Keep the first-line summary (D212), rather than the conflicting D213 convention.
def utility_pairs(reference, estimate, *, vectorized=False):  # noqa: D213
    """Return paired true/estimated utilities in reference bid order.

    True utilities retain the assessment API's existing ``bid.utility``
    convention. The optional fast path uses the standard additive method only;
    custom utility functions and custom bid iterators use their normal calls.
    Nothing is cached: edits to weights, bids or bid order apply on every call.
    """
    bids = reference.bids
    true = np.asarray([bid.utility for bid in bids], dtype=float)
    method = estimate.get_utility
    if not vectorized or not bids:
        return true, np.asarray([method(bid) for bid in bids], dtype=float)
    # Import lazily to avoid the OpponentModel/utility module import cycle.
    from nenv.OpponentModel.UniformEstimatedPreference import UniformEstimatedPreference
    from nenv.OpponentModel.CBOMEstimatedPreference import CBOMEstimatedPreference
    from nenv.EditablePreference import EditablePreference

    standard = (type(estimate) in (Preference, UniformEstimatedPreference,
                                   CBOMEstimatedPreference, EditablePreference) and
                getattr(method, "__func__", None) is _ADDITIVE_GET_UTILITY and
                Bid.__iter__ is _STANDARD_BID_ITER and
                IssueIterator.__init__ is _STANDARD_ISSUE_ITER_INIT and
                IssueIterator.__next__ is _STANDARD_ISSUE_ITER_NEXT and
                # Exact types keep customized bid iteration on the scalar path.
                all(type(bid) is Bid and type(bid.content) is dict for bid in bids))  # pylint: disable=unidiomatic-typecheck
    if not standard:
        return true, np.asarray([method(bid) for bid in bids], dtype=float)

    # Keep each bid's issue summation order, including its floating-point order.
    issues = tuple(bids[0].content)
    if any(tuple(bid.content) != issues for bid in bids):
        return true, np.asarray([method(bid) for bid in bids], dtype=float)

    # Match the verified get_utility implementation's backing dictionaries;
    # public weight-view properties can themselves be customized independently.
    issue_weights = estimate._issue_weights
    value_weights = estimate._value_weights
    # Custom mappings can alter scalar arithmetic and must not enter this path.
    if type(issue_weights) is not dict or type(value_weights) is not dict or any(  # pylint: disable=unidiomatic-typecheck
            type(value_weights[issue]) is not dict for issue in issues):  # pylint: disable=unidiomatic-typecheck
        return true, np.asarray([method(bid) for bid in bids], dtype=float)
    # Float32/custom arithmetic can round before promotion in get_utility.
    # Keep its scalar operations rather than silently changing precision.
    standard_types = (float, np.float64)
    if any(type(issue_weights[issue]) not in standard_types or
           any(type(weight) not in standard_types for weight in value_weights[issue].values())
           for issue in issues):
        return true, np.asarray([method(bid) for bid in bids], dtype=float)

    values = np.zeros(len(bids), dtype=float)
    for issue in issues:
        evaluations = value_weights[issue]
        column = np.fromiter((evaluations[bid.content[issue]] for bid in bids),
                             dtype=float, count=len(bids))
        values += issue_weights[issue] * column
    return true, values
