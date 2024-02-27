from typing import List, Set
from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel
from nenv.Preference import Preference
from nenv.Bid import Bid


class ConflictBasedOpponentModel(AbstractOpponentModel):
    """
        **Conflict-based opponent model**:
            It tries to extract the maximum information gained with limited interaction. It presents a conflict-based
            opponent modeling technique which resolves the conflicts by ordering the issues and values.
            The proposed model out-performs them despite the diversity of participants’ negotiation behaviors. Besides,
            the conflict-based opponent model estimates the entire bid space much more successfully than its competitors
            in automated negotiation sessions when a small portion of the outcome space was explored. [Keskin2023]_

        .. [Keskin2023] Keskin, M.O., Buzcu, B. & Aydoğan, R. Conflict-based negotiation strategy for human-agent negotiation. Appl Intell 53, 29741–29757 (2023). <https://doi.org/10.1007/s10489-023-05001-9>
    """

    opponent_history: List[Bid]

    def __init__(self, reference: Preference):
        super().__init__(reference)
        self.opponent_history = []

    @property
    def name(self) -> str:
        return "Conflict-Based Opponent Model"

    def update(self, bid: Bid, t: float):
        self.opponent_history.append(bid)

        # Dictionary that keeps number of same values as keys, and compared offers list as values.
        comparables_dict = {}

        for i in range(len(self.opponent_history)):
            for j in range(i + 1, len(self.opponent_history)):
                # Compare current and next bid's issue values. If they are same, add to the list

                # Create comparison variable for history offers.
                comparison_pair = ComparisonObject(self.opponent_history[i], self.opponent_history[j])

                # Check if this pair already exists in dict, append otherwise with same value count as a key
                comparing_issues_size = comparison_pair.comparing_issues_size

                # If count does not exist, create new empty list to append later on.
                if comparing_issues_size not in comparables_dict:
                    comparables_dict[comparing_issues_size] = []

                if comparison_pair not in comparables_dict[comparing_issues_size]:
                    comparables_dict[comparing_issues_size].append(comparison_pair)

        # List that keeps importance of the issues in descending order.
        # idx 0 is more important than idx 1
        # Initially at semi-random (the order which the values were inserted)

        issues_orderings = self.preference.issues
        value_orderings = {issue.name: issue.values for issue in self.preference.issues}
        issue_size = len(issues_orderings)

        all_pairwise_comparisons = {key: [] for key in issues_orderings}
        # "issue_name": (first_value, second_value)

        ground_truths = []  # list of 1 value pairwise comparisons

        # comparison pair size 1 equals comparing only 1 value, the rest of the values are the same
        for comparison_item in comparables_dict.get(1, []):
            for (issue_name, first_value, second_value) in comparison_item:
                first_value_idx = value_orderings[issue_name].index(first_value)
                second_value_idx = value_orderings[issue_name].index(second_value)

                all_pairwise_comparisons[issue_name].append((first_value, second_value))
                ground_truths.append((first_value, second_value))

                value_orderings[issue_name][first_value_idx], value_orderings[issue_name][second_value_idx] = value_orderings[issue_name][second_value_idx], value_orderings[issue_name][first_value_idx]

        for issue, ordering in value_orderings.items():
            for first_item, second_item in all_pairwise_comparisons[issue]:
                first_value_idx = ordering.index(first_item)
                second_value_idx = ordering.index(second_item)

                if first_value_idx > second_value_idx:
                    ordering[first_value_idx], ordering[second_value_idx] = ordering[second_value_idx], ordering[first_value_idx]

        while True:
            prev_size = sum(map(len, all_pairwise_comparisons.values()))
            for comparing_amount in range(2, issue_size):
                list_of_comparisons = comparables_dict.get(comparing_amount, [])

                for comparison_item in list_of_comparisons:
                    conflicts = []

                    for (issue_name, first_value, second_value) in comparison_item:
                        # first condition: if the reverse of what is proposed by this comparison item
                        # (e.g., the first_value > second_value) see if it is contradicted by the ground truths.
                        # and ignore it.

                        if (second_value, first_value) in ground_truths:
                            continue

                        if (second_value, first_value) in all_pairwise_comparisons[issue_name]:
                            conflicts.append(issue_name)

                    # if issue_size = 4, and we are evaluation by pairs (comparing_amount = 2)
                    # then 4 - 2 - 1 = 1 conflicts means 1 conflicting value is enough to
                    # determine that one value is weighted higher than the rest.

                    if len(conflicts) == issue_size - comparing_amount - 1:
                        final_issues = [issue for issue in issues_orderings if issue not in conflicts]

                        for issue in final_issues:
                            if issue in comparison_item.comparing_issues:
                                if comparison_item[issue] in all_pairwise_comparisons[issue]:
                                    continue

                                all_pairwise_comparisons[issue].append(comparison_item[issue])

            if prev_size == sum(map(len, all_pairwise_comparisons.values())):
                break

        for issue, ordering in value_orderings.items():
            for first_item, second_item in all_pairwise_comparisons[issue]:
                first_item_idx = ordering.index(first_item)
                second_item_idx = ordering.index(second_item)

                if first_item_idx > second_item_idx:
                    ordering[first_item_idx], ordering[second_item_idx] = ordering[second_item_idx], ordering[
                        first_item_idx]
        # swap_code:

        # value_orderings[issue_name][first_value_idx], value_orderings[issue_name][second_value_idx] = value_orderings[
        #    issue_name][second_value_idx], value_orderings[issue_name][first_value_idx]
        # second phase is we evaluate and gather information on the rest of the comparison sizes

        conflict_count = {}

        for comparing_issues_size, comparison_pair_list in comparables_dict.items():
            for comparison_pair in comparison_pair_list:
                comparing_issues = comparison_pair.comparing_issues
                conflict_issues = []

                for issue_name, first_value, second_value in comparison_pair:
                    ordering_for_issue_values = value_orderings[issue_name]

                    # given the values are held in descending order, this is a conflict
                    if ordering_for_issue_values.index(str(second_value)) < ordering_for_issue_values.index(str(first_value)):
                        conflict_issues.append(issue_name)

                if len(conflict_issues) == comparing_issues_size - 1:
                    conflict_count[tuple(comparing_issues)] = conflict_count.get(tuple(comparing_issues), 0) + 1

        # The conflicts are sorted by count, so the most count conflict will have the highest precedence
        # Since they are applied in order of their counts

        conflict_count_sorted_values = dict(sorted(conflict_count.items(), key=lambda item: item[1]))

        for conflict, amount in conflict_count_sorted_values.items():
            non_conflict_issues = [issue for issue in issues_orderings.copy() if issue not in conflict]

            # first_value is an earlier bid than second_value
            # the orderings are held in descending order
            # these conflicts are captured based on the fact that the first value is supposed to be higher
            # but they are actually not, therefore, the conflicting issues are the issues that should be
            # lower in value given our assumption of human concession in negotiations
            # code block below swaps the issue ordering based on above
            # since conflicting issue is considered to be causing the lowness, it must be swapped
            # with the non-conflicting comparing issues.

            for conflict_issue in conflict:
                for non_conflict_issue in non_conflict_issues:
                    conflict_idx = issues_orderings.index(conflict_issue)
                    non_conflict_idx = issues_orderings.index(non_conflict_issue)

                    if conflict_idx < non_conflict_idx:
                        issues_orderings[conflict_idx], issues_orderings[non_conflict_idx] = issues_orderings[non_conflict_idx], issues_orderings[conflict_idx]

            issue_weights = [0] * issue_size
            issues_mid = (issue_size - 1) // 2
            diff = 1 / issue_size
            issue_weights[issues_mid] = diff
            sum_diffs = diff

            for i in range(1, issue_size // 2 + 1):
                target = issues_mid + i
                if target < issue_size:
                    target_next = issue_weights[issues_mid + i - 1]
                    diff = target_next + target_next / issue_size
                    sum_diffs += diff
                    issue_weights[target] = diff

                target = issues_mid - i
                if target < issue_size:
                    target_prev = issue_weights[issues_mid - i + 1]
                    diff = target_prev - target_prev / issue_size
                    sum_diffs += diff
                    issue_weights[target] = diff

            issue_weights = [issue / sum_diffs for issue in issue_weights]
            issue_weights.reverse()

            value_weights = {}
            for issue, values in value_orderings.items():
                expected = []

                for i in range(1, len(values) + 1):
                    expected.append(i / len(values))

                expected.reverse()
                value_weights[issue] = dict(zip(values, expected))

            self._pref._value_weights = value_weights
            self._pref._issue_weights = dict(zip(issues_orderings, issue_weights))


class ComparisonObject:
    """
        Helper class for Conflict-Based Opponent Model
    """

    def __init__(self, first_offer: Bid, second_offer: Bid):
        self.comparing_issues = []
        self.first_offer, self.second_offer = self.reduce_elements(
            first_offer, second_offer
        )

        # self.comparing_issues = set(self.comparing_issues)

        self.comparing_issues_size = len(self.comparing_issues)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str(self.first_offer) + " > " + str(self.second_offer)

    def __eq__(self, other):
        """
        Takes comparison object as input as returns true if they are same otherwise false.
        """
        return self.__str__() == other.__str__()

    def __hash__(self):
        return self.__str__().__hash__()

    def __iter__(self):
        for i in set(self.first_offer).intersection(set(self.second_offer)):
            yield (i,) + (self.first_offer[i], self.second_offer[i])

    def __getitem__(self, issue):
        return (self.first_offer[issue], self.second_offer[issue])

    def reduce_elements(self, first_offer: Bid, second_offer: Bid):  # fix this with lambdas
        a = {}
        b = {}
        full_a = {}
        full_b = {}

        for key in first_offer.content.keys():
            full_a[key] = first_offer[key]
            full_b[key] = second_offer[key]

            if first_offer[key] != second_offer[key]:
                a[key] = first_offer[key]
                b[key] = second_offer[key]
                self.comparing_issues.append(key)

        if len(a) == 0:
            self.comparing_issues = set(full_a)

            return full_a, full_b

        return a, b

    def is_comparable(self, other):
        return self.comparing_issues in other.comparing_issues
