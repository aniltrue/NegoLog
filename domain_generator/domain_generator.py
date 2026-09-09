from __future__ import annotations

import os
import math
import shutil
from typing import List, Dict, Union
import json
import matplotlib.pyplot as plt
import numba
import numpy as np
import random as rnd
from string import ascii_uppercase

import nenv
from domain_generator.domain_storage import atomic_domain_output, validate_profiles

EPSILON = 1e-5

# Default Parameters
UTILITY_RANGE = [None, None]
DOMAIN_SIZE_RANGE = [0, 100000]
DOMAIN_OPPOSITION_RANGE = [0.0, 1.0]
BALANCE_SCORE_RANGE = [0.0, 0.05]
VALUE_BOOST = [0.0]

def get_n_digit_float(val: float, n: int = 2) -> float:
    return round(val, n)


class Preference:
    issues: dict = {}
    issue_weights: dict = {}
    reservation_value: float

    def __init__(self, issues_values: list, 
                 inverse: bool, 
                 reservation_value: float = 0., 
                 value_boost: float = 0.,
                 min_utility: float = None, 
                 max_utility: float = None,
                 has_randomness: bool = True):
        
        self.issues = {}
        self.issue_weights = {}
        self.reservation_value = reservation_value

        VALUE_DIFF_A = 1.
        VALUE_DIFF_B = 1.
        randomness = 1. if has_randomness else 0.

        for i, values in enumerate(issues_values):
            issue_name = "issue" + ascii_uppercase[i]

            if not inverse:
                self.issue_weights[issue_name] = get_n_digit_float(i + 1 + rnd.gauss(0., 1.) * randomness)
            else:
                self.issue_weights[issue_name] = get_n_digit_float(len(issues_values) - i + rnd.gauss(0., 1.) * randomness)

            # Issue Weights cannot be negative
            while self.issue_weights[issue_name] <= 0:
                if not inverse:
                    self.issue_weights[issue_name] = get_n_digit_float(i + 1 + rnd.gauss(0., 1.) * randomness)
                else:
                    self.issue_weights[issue_name] = get_n_digit_float(len(issues_values) - i + rnd.gauss(0., 1.) * randomness)
            # poson dist
            self.issues[issue_name] = {}

            for j in range(values):
                value_name = "value" + ascii_uppercase[j]

                if not inverse:
                    self.issues[issue_name][value_name] = get_n_digit_float(j * VALUE_DIFF_A + 1 + rnd.gauss(0., 1.) * VALUE_DIFF_A * randomness) + value_boost
                else:
                    self.issues[issue_name][value_name] = get_n_digit_float(values - j * VALUE_DIFF_B + rnd.gauss(0., 1.) * VALUE_DIFF_B * randomness)

        self.__normalize()
        
        if min_utility is not None and max_utility is not None:
            for issue_name in self.issues:
                value_min, value_max = min(self.issues[issue_name].values()), max(self.issues[issue_name].values())
                if value_max == value_min:
                    value_max = 1.
                    value_min = 0.

                for value_name in self.issues[issue_name]:
                    value = self.issues[issue_name][value_name]
                    # Make range [0, 1]
                    value = (value - value_min) / (value_max - value_min)
                    # Scale
                    value = value * (max_utility - min_utility) + min_utility
    
                    self.issues[issue_name][value_name] = get_n_digit_float(value)

    def __normalize(self):
        issue_weights_sum = sum(self.issue_weights.values())

        for issue_name, values in self.issues.items():
            self.issue_weights[issue_name] /= issue_weights_sum
            self.issue_weights[issue_name] = round(self.issue_weights[issue_name], 2)

            value_max = max(values.values())
            value_min = min(values.values())

            if value_max == value_min:
                value_max = 1.
                value_min = 0.

            if value_min < 0:  # Value Weights cannot be negative
                for value_name in values.keys():
                    self.issues[issue_name][value_name] -= value_min
                    self.issues[issue_name][value_name] /= value_max - value_min
            else:
                for value_name in values.keys():
                    self.issues[issue_name][value_name] /= value_max

            for value_name in values:
                self.issues[issue_name][value_name] = round(self.issues[issue_name][value_name], 2)

        # Allocate 100 hundredths in bounded time, without retrying float equality.
        total = sum(self.issue_weights.values())
        scaled = {issue: weight * 100 / total for issue, weight in self.issue_weights.items()}
        units = {issue: math.floor(weight) for issue, weight in scaled.items()}
        remaining = 100 - sum(units.values())
        order = sorted(units, key=lambda issue: scaled[issue] - units[issue], reverse=True)
        for issue_name in order[:remaining]:
            units[issue_name] += 1
        self.issue_weights = {issue: count / 100 for issue, count in units.items()}

    def generate_bids(self, upper_bound: int = -1) -> List[Dict[str, str]]:
        """Enumerate complete bids, rejecting spaces above an explicit bound."""
        size = math.prod(len(values) for values in self.issues.values())
        if upper_bound != -1 and size > upper_bound:
            raise ValueError("The complete bid space exceeds upper_bound.")
        bids = [{}]

        for issue_name in self.issue_weights.keys():
            new_bids = []

            for value_name in self.issues[issue_name].keys():
                for bid in bids:
                    _bid = bid.copy()

                    _bid[issue_name] = value_name

                    new_bids.append(_bid)

            bids = new_bids

        return bids

    def get_utility(self, bid: dict) -> float:
        utility = 0.

        for issue_name, value_name in bid.items():
            utility += self.issue_weights[issue_name] * self.issues[issue_name][value_name]

        return utility


def get_points(bids: list, prefA: Preference, prefB: Preference) -> np.ndarray:
    return np.array([[prefA.get_utility(bid), prefB.get_utility(bid)] for bid in bids], dtype=float)


@numba.jit(nopython=True)
def get_pareto(points: np.ndarray) -> (List[np.ndarray], List[int]):
    size = points.shape[0]

    pareto_front_points = []
    pareto_front_indices = []

    for i in range(size):
        is_on_pareto = True

        for j in range(size):
            if (points[j, 0] >= points[i, 0] and points[j, 1] >= points[i, 1]) and (points[j, 0] > points[i, 0] or points[j, 1] > points[i, 1]):
                is_on_pareto = False

                break

        if is_on_pareto:
            pareto_front_points.append(points[i])
            pareto_front_indices.append(i)

    return pareto_front_points, pareto_front_indices


@numba.jit(nopython=True)
def find_nash_kalai(points: np.ndarray) -> (List[float], List[float], int, int):
    if points.shape[0] == 0:
        raise ValueError("At least one bid point is required.")
    nash = [points[0, 0], points[0, 1]]
    kalai = [points[0, 0], points[0, 1]]
    nash_index = 0
    kalai_index = 0

    for i in range(points.shape[0]):
        if points[i, 0] * points[i, 1] > nash[0] * nash[1]:
            nash = [points[i, 0], points[i, 1]]
            nash_index = i

        if points[i, 0] + points[i, 1] > kalai[0] + kalai[1]:
            kalai = [points[i, 0], points[i, 1]]
            kalai_index = i

    return nash, kalai, nash_index, kalai_index


def calculate_opposition(kalai: List[float]) -> float:
    return np.sqrt((kalai[0] - 1.) ** 2. + (kalai[1] - 1.) ** 2.)


def calculate_balance_score(points: np.ndarray) -> float:
    points_a = list(points[:, 0])
    points_b = list(points[:, 1])

    indices_a = sorted(list(range(len(points_a))), key=lambda i: points_a[i], reverse=True)
    indices_b = sorted(list(range(len(points_b))), key=lambda i: points_b[i], reverse=True)
    total = 0.

    for i in range(len(points_a)):
        total += points_a[indices_a[i]] - points_b[indices_b[i]]

    return total / len(points_a)


@numba.jit(nopython=True)
def calculate_normalized_balance_score(points: np.ndarray, nash: List[float]) -> float:
    points_a = list(points[:, 0])
    points_b = list(points[:, 1])

    nash_zero = np.sqrt(np.power(nash[0], 2.) + np.power(nash[1], 2.))
    if nash_zero == 0:
        return np.nan

    total = 0.

    for i, point_a in enumerate(points_a):
        nash_distance = np.sqrt(np.power(nash[0] - point_a, 2.) + np.power(nash[1] - points_b[i], 2.))

        total += (point_a - points_b[i]) * nash_distance / nash_zero

    return total / len(points_a)


def save_profile(path: str, pref: Preference):
    profile_data = {
        "reservationValue": pref.reservation_value,
        "issueWeights": pref.issue_weights,
        "issues": pref.issues
    }

    with open(path, "w") as f:
        json.dump(profile_data, f, indent=1)


def save_profile_genius(path: str, pref: Preference, profile_name: str, id: str):
    domain_name = "domain%s" % id

    profile_data = {
        "LinearAdditiveUtilitySpace":
            {
                "issueUtilities": {
                    issue_name: {"DiscreteValueSetUtilities": {"valueUtilities":
                                    {value_name: utility for value_name, utility in pref.issues[issue_name].items()}
                                                               }} for issue_name in pref.issues
                },
                "issueWeights": pref.issue_weights,
                "domain": {
                    "name": domain_name,
                    "issuesValues": {issue_name:
                                        {"values": [value_name for value_name in pref.issues[issue_name]]}
                                    for issue_name in pref.issues}
                },
                "name": profile_name
            }
    }

    with open(path, "w") as f:
        json.dump(profile_data, f, indent=1)


def convert2genius_specs(specs: dict, pref_a: Preference, pref_b: Preference):
    bids = pref_a.generate_bids()
    bids = sorted(bids, key=lambda bid: pref_a.get_utility(bid), reverse=True)

    points = get_points(bids, pref_a, pref_b)

    pareto, pareto_front = get_pareto(points)

    pareto_indices = pareto_front

    nash, kalai, nash_index, kalai_index = find_nash_kalai(points)

    return {
        "size": len(bids),
        "opposition": specs["Opposition"],
        "nash": {
            "bid": bids[nash_index],
            "utility": [nash[0], nash[1]]
        },
        "kalai": {
            "bid": bids[kalai_index],
            "utility": [kalai[0], kalai[1]]
        },
        "pareto_front": [
            {
                "bid": bids[pareto_indices[i]],
                "utility": [pareto[i][0], pareto[i][1]]
            } for i in range(len(pareto))
        ]
    }


def _range(value, default, label, *, integer=False, minimum=None, maximum=None):
    """Validate and copy a two-element range without changing caller inputs."""
    if value is None:
        value = default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = [value, value]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} must contain two bounds.")
    if all(bound is None for bound in value) and label == "utility_range":
        return [None, None]
    if any(isinstance(bound, bool) or not isinstance(bound, (int, float))
           or not math.isfinite(bound) for bound in value):
        raise ValueError(f"{label} must contain finite numeric bounds.")
    if integer and any(not isinstance(bound, int) for bound in value):
        raise ValueError(f"{label} must contain integer bounds.")
    if value[0] > value[1] or (minimum is not None and value[0] < minimum) or (maximum is not None and value[1] > maximum):
        raise ValueError(f"Invalid {label} bounds.")
    return list(value)


@atomic_domain_output
def generate_random_domain(name: str,
                           issue_size_range: Union[List[int] | int],
                           value_size_range: Union[List[int] | int],
                           value_boost: float = 0.,
                           opposition_range: Union[List[float] | None] = None,
                           balance_score_range: Union[List[float] | None] = None,
                           reservation_value_profile_a: float = 0.,
                           reservation_value_profile_b: float = 0.,
                           utility_range: Union[List[float] | None] = None,
                           domain_size_range: Union[List[int] | None] = None,
                           is_for_genius: bool = False,
                           has_randomness: bool = True,
                           *, output_dir=None, max_attempts: int = 1000):
    """Generate a domain within fixed constraints, or fail after max_attempts."""

    issue_size_range = _range(issue_size_range, None, "issue_size_range", integer=True, minimum=1, maximum=26)
    value_size_range = _range(value_size_range, None, "value_size_range", integer=True, minimum=1, maximum=26)
    opposition_range = _range(opposition_range, DOMAIN_OPPOSITION_RANGE, "opposition_range", minimum=0)
    balance_score_range = _range(balance_score_range, BALANCE_SCORE_RANGE, "balance_score_range", minimum=0)
    domain_size_range = _range(domain_size_range, DOMAIN_SIZE_RANGE, "domain_size_range", integer=True, minimum=0)
    utility_range = _range(utility_range, UTILITY_RANGE, "utility_range", minimum=0, maximum=1)
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer.")

    for label, number in [("value_boost", value_boost), ("reservation_value_profile_a", reservation_value_profile_a),
                          ("reservation_value_profile_b", reservation_value_profile_b)]:
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
            raise ValueError(f"{label} must be finite.")
    if not isinstance(has_randomness, bool) or not isinstance(is_for_genius, bool):
        raise ValueError("has_randomness and is_for_genius must be booleans.")

    # Generate domain folder
    path = output_dir or ("domains_genius" if is_for_genius else "domains")
    if os.path.exists("%s/domain%s/" % (path, name)):
        shutil.rmtree("%s/domain%s/" % (path, name))

    os.makedirs("%s/domain%s/" % (path, name))

    for _attempt in range(max_attempts):
        # Decide issues and values
        number_of_issues = rnd.randint(issue_size_range[0], issue_size_range[1])

        issue_list = [rnd.randint(value_size_range[0], value_size_range[1]) for _ in range(number_of_issues)]
        if not domain_size_range[0] <= math.prod(issue_list) <= domain_size_range[1]:
            continue

        # Generate Preferences
        prefA = Preference(issue_list, False, float(reservation_value_profile_a), value_boost, utility_range[0],
                           utility_range[1], bool(has_randomness))

        prefB = Preference(issue_list, False, float(reservation_value_profile_b), value_boost, utility_range[0],
                           utility_range[1], bool(has_randomness))

        # Generate Bids
        bids = prefA.generate_bids(int(domain_size_range[1]))

        bids = sorted(bids, key=lambda bid: prefA.get_utility(bid), reverse=True)

        # Get points
        points = get_points(bids, prefA, prefB)

        # Get pareto, nash and kalai
        pareto, _ = get_pareto(points)
        pareto = np.array(pareto)

        nash, kalai, nash_index, kalai_index = find_nash_kalai(points)

        # Calculate opposition and balance scores
        opposition = calculate_opposition(kalai)

        balance_score = calculate_balance_score(points)

        norm_balance_score = calculate_normalized_balance_score(points, nash)

        # Control given ranges
        if opposition < float(opposition_range[0]) or opposition > float(opposition_range[1]):
            continue

        if abs(balance_score) < float(balance_score_range[0]) or abs(balance_score) > float(balance_score_range[1]):
            continue

        # Draw bidspace
        plt.scatter(points[:, 0], points[:, 1], c="b", marker=".", label="Offer")
        plt.plot(pareto[:, 0], pareto[:, 1], "-*k", label="Pareto")

        plt.scatter(nash[0], nash[1], c="r", marker="^", label="Nash", s=75)
        plt.scatter(kalai[0], kalai[1], c="r", marker="o", label="Kalai", s=100)

        plt.xlim([0.0, 1.01])
        plt.ylim([0.0, 1.01])

        plt.title("Bid Space\nsize: %d | opposition: %.4f\nbalance: %.4f | normalized balance: %.4f" %
                  (len(bids), opposition, balance_score, norm_balance_score), fontsize=10)

        plt.xlabel("Profile A", fontsize=18)
        plt.ylabel("Profile B", fontsize=18)

        plt.legend()
        plt.savefig("%s/domain%s/bid_space.png" % (path, name), dpi=300, bbox_inches="tight")

        plt.close()

        # Generate specs.json

        min_utility = np.min(points)
        max_utility = np.max(points)

        specs = {
            "Name": "Domain%s" % name,
            "NumberOfBids": len(bids),
            "NumberOfIssues": len(prefA.issue_weights),
            "IssueValues": issue_list,
            "Opposition": opposition,
            "BalanceScore": balance_score,
            "NormalizedBalanceScore": float(norm_balance_score) if np.isfinite(norm_balance_score) else None,
            "Product Score": nash[0] * nash[1],
            "Social Welfare": kalai[0] + kalai[1],
            "Nash_A": nash[0],
            "Nash_B": nash[1],
            "Kalai_A": kalai[0],
            "Kalai_B": kalai[1],
            "NashBid": bids[nash_index],
            "KalaiBid": bids[kalai_index],
            "ReservationValueProfileA": reservation_value_profile_a,
            "ReservationValueProfileB": reservation_value_profile_b,
            "MinUtility": min_utility,
            "MaxUtility": max_utility
        }

        specs_file_name = "specials.json" if is_for_genius else "specs.json"

        if is_for_genius:
            specs = convert2genius_specs(specs, prefA, prefB)

        with open("%s/domain%s/%s" % (path, name, specs_file_name), "w") as f:
            json.dump(specs, f, indent=1)

        # domain json for genius
        if is_for_genius:
            with open("%s/domain%s/domain%s.json" % (path, name, name), "w") as f:
                domain_data = {
                    "name": f"domain{name}",
                    "issuesValues": {issue_name:
                                        {"values": [value_name for value_name in prefA.issues[issue_name]]}
                                    for issue_name in prefA.issues}
                               }
                json.dump(domain_data, f)

        # Profile JSON
        if is_for_genius:
            save_profile_genius("%s/domain%s/profileA.json" % (path, name), prefA, "profileA", name)
            save_profile_genius("%s/domain%s/profileB.json" % (path, name), prefB, "profileB", name)
        else:
            save_profile("%s/domain%s/profileA.json" % (path, name), prefA)
            save_profile("%s/domain%s/profileB.json" % (path, name), prefB)

        # Print details
        print("Domain%s" % name)

        print("Number of bids:", len(bids))

        print("Opposition:", opposition)

        print("Balance Score:", balance_score)

        print("Normalized Balance Score:", norm_balance_score)

        print("Kalai:", kalai[0] + kalai[1], kalai)

        print("Nash:", nash[0] * nash[1], nash)

        print()

        # Return for domains.csv
        return {
            "DomainName": name,
            "Size": len(bids),
            "NumberOfIssue": len(prefA.issues),
            "IssueValues": str(issue_list),
            "Opposition": opposition,
            "BalanceScore": balance_score,
            "NormalizedBalanceScore": float(norm_balance_score) if np.isfinite(norm_balance_score) else None,
            "ProductScore": nash[0] * nash[1],
            "SocialWelfare": kalai[0] + kalai[1],
            "ReservationValueA": reservation_value_profile_a,
            "ReservationValueB": reservation_value_profile_b,
            "NashA": nash[0],
            "NashB": nash[1],
            "KalaiA": kalai[0],
            "KalaiB": kalai[1],
            "MinUtility": min_utility,
            "MaxUtility": max_utility
        }


    raise ValueError(f"No domain satisfied the constraints in {max_attempts} attempts.")


@atomic_domain_output
def generate_domain(name: str,
                    issue_weights_a: Dict[str, float],
                    issue_weights_b: Dict[str, float],
                    issues_a: Dict[str, Dict[str, float]],
                    issues_b: Dict[str, Dict[str, float]],
                    reservation_value_profile_a: float = 0.,
                    reservation_value_profile_b: float = 0., *, output_dir=None):
    """Generate a validated two-profile domain using a staged output folder."""
    validate_profiles(issue_weights_a, issue_weights_b, issues_a, issues_b,
                      reservation_value_profile_a, reservation_value_profile_b)
    # Generate domain folder
    path = output_dir or "domains"
    if os.path.exists("%s/domain%s/" % (path, name)):
        shutil.rmtree("%s/domain%s/" % (path, name))

    os.makedirs("%s/domain%s/" % (path, name))

    # Generate Preferences

    preference_a = nenv.EditablePreference(issue_weights_a, issues_a, reservation_value_profile_a, True)
    preference_b = nenv.EditablePreference(issue_weights_b, issues_b, reservation_value_profile_b, True)

    bid_space = nenv.BidSpace(preference_a, preference_b)

    # Get pareto, nash and kalai
    pareto = bid_space.pareto
    pareto = np.array(pareto)

    nash_point, kalai_point = bid_space.nash_point, bid_space.kalai_point

    # Calculate opposition and balance scores
    opposition = bid_space.calculate_opposition()

    balance_score = bid_space.calculate_balance_score()

    norm_balance_score = bid_space.calculate_normalized_balance_score()

    # Get points
    points = np.array([[bid.utility_a, bid.utility_b] for bid in bid_space.bid_points])

    pareto_points = np.array([[bid.utility_a, bid.utility_b] for bid in pareto])

    # Draw bidspace
    plt.scatter(points[:, 0], points[:, 1], c="b", marker=".", label="Offer")
    plt.plot(pareto_points[:, 0], pareto_points[:, 1], "-*k", label="Pareto")

    plt.scatter(nash_point.utility_a, nash_point.utility_b, c="r", marker="^", label="Nash", s=75)
    plt.scatter(kalai_point.utility_a, kalai_point.utility_b, c="r", marker="o", label="Kalai", s=100)

    plt.xlim([0.0, 1.01])
    plt.ylim([0.0, 1.01])

    plt.title("Bid Space\nsize: %d | opposition: %.4f\nbalance: %.4f | normalized balance: %.4f" %
              (points.shape[0], opposition, balance_score, norm_balance_score), fontsize=10)

    plt.xlabel("Profile A", fontsize=18)
    plt.ylabel("Profile B", fontsize=18)

    plt.legend()
    plt.savefig("%s/domain%s/bid_space.png" % (path, name), dpi=300, bbox_inches="tight")

    plt.close()

    # Generate specs.json

    min_utility = np.min(points)
    max_utility = np.max(points)

    specs = {
        "Name": "Domain%s" % name,
        "NumberOfBids": points.shape[0],
        "NumberOfIssues": len(preference_a.issue_weights),
        "IssueValues": [len(values) for values in issues_a.values()],
        "Opposition": opposition,
        "BalanceScore": balance_score,
        "NormalizedBalanceScore": float(norm_balance_score) if np.isfinite(norm_balance_score) else None,
        "Product Score": nash_point.product_score,
        "Social Welfare": kalai_point.social_welfare,
        "Nash_A": nash_point.utility_a,
        "Nash_B": nash_point.utility_b,
        "Kalai_A": kalai_point.utility_a,
        "Kalai_B": kalai_point.utility_b,
        "NashBid": str(nash_point.bid),
        "KalaiBid": str(kalai_point.bid),
        "ReservationValueProfileA": reservation_value_profile_a,
        "ReservationValueProfileB": reservation_value_profile_b,
        "MinUtility": min_utility,
        "MaxUtility": max_utility
    }

    specs_file_name = "specs.json"

    with open("%s/domain%s/%s" % (path, name, specs_file_name), "w") as f:
        json.dump(specs, f, indent=1)

    # domain json for genius

    # Profile JSON
    profile_data = {
        "reservationValue": preference_a.reservation_value,
        "issueWeights": {issue.name: weight for issue, weight in preference_a.issue_weights.items()},
        "issues": {issue.name: preference_a.value_weights[issue] for issue in preference_a.issues}
    }

    with open("%s/domain%s/profileA.json" % (path, name), "w") as f:
        json.dump(profile_data, f, indent=1)

    profile_data = {
        "reservationValue": preference_b.reservation_value,
        "issueWeights": {issue.name: weight for issue, weight in preference_b.issue_weights.items()},
        "issues": {issue.name: preference_b.value_weights[issue] for issue in preference_b.issues}
    }

    with open("%s/domain%s/profileB.json" % (path, name), "w") as f:
        json.dump(profile_data, f, indent=1)

    # Print details
    print("Domain%s" % name)

    print("Number of bids:", points.shape)

    print("Opposition:", opposition)

    print("Balance Score:", balance_score)

    print("Normalized Balance Score:", norm_balance_score)

    print("Kalai:", kalai_point.social_welfare, kalai_point.bid)

    print("Nash:", nash_point.product_score, nash_point.bid)

    print()

    # Return for domains.csv
    return {
        "DomainName": name,
        "Size": points.shape[0],
        "NumberOfIssue": len(preference_a.issue_weights),
        "IssueValues": [len(values) for values in issues_a.values()],
        "Opposition": opposition,
        "BalanceScore": balance_score,
        "NormalizedBalanceScore": float(norm_balance_score) if np.isfinite(norm_balance_score) else None,
        "ProductScore": nash_point.product_score,
        "SocialWelfare": kalai_point.social_welfare,
        "ReservationValueA": reservation_value_profile_a,
        "ReservationValueB": reservation_value_profile_b,
        "NashA": nash_point.utility_a,
        "NashB": nash_point.utility_b,
        "KalaiA": kalai_point.utility_a,
        "KalaiB": kalai_point.utility_b,
        "MinUtility": min_utility,
        "MaxUtility": max_utility
    }
