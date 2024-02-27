import time
from typing import List
import nenv
import nenv.OpponentModel
import random
from scipy.stats import spearmanr


class GeneticAlgorithm:
    """
        Genetic Algorithm approach to estimate the own preference for the Uncertainty Challenge
    """
    pop_size: int               # Population size
    max_generation: int         # Maximum generation
    cross_rate: float           # Cross-Over rate
    reference: nenv.Preference  # Real preferences as a reference
    rnd: random.Random          # Random object
    start_time: float           # Start-time of the algorithm
    time_limit: float           # Time-Limit for the algorithm in terms of seconds

    def __init__(self, reference: nenv.Preference, pop_size: int = 50, max_generation: int = 200, cross_rate: float = 3.0, time_limit: float = 10):
        """
            Constructor
        :param reference: Real preferences
        :param pop_size: Population size, Default: 50, Original: 500
        :param max_generation: Maximum generation, Default: 200
        :param cross_rate: Cross-Over rate, Default: 3.0
        :param time_limit: Time-Limit for the algorithm in terms of seconds, Default: 10 seconds
        """
        self.pop_size = pop_size
        self.max_generation = max_generation
        self.cross_rate = cross_rate
        self.reference = reference
        self.rnd = random.Random()
        self.time_limit = time_limit
        self.start_time = time.time()

    def estimate_preferences(self) -> nenv.OpponentModel.EstimatedPreference:
        """
            This method applies the Genetic Algorithm approach to estimate the preferences.
        :return: Preference in the population which has the highest fitness score
        """

        self.start_time = time.time()

        # Random population
        population = [self.random_preference() for _ in range(self.pop_size)]

        # Iterate generations
        for gen in range(self.max_generation):
            # Fitness scores of the current generation
            fitness_list = [self.fitness(individual) for individual in population]

            # Apply Roulette Selection approach to choice next generation from the previous population
            population = self.select_by_roulette(population, fitness_list)

            # Generate new individuals for the population
            for i in range(int(self.pop_size * self.cross_rate)):
                parent1, parent2 = self.rnd.choice(population), self.rnd.choice(population)

                child = self.cross_over(parent1, parent2)

                population.append(child)

            # Time-Limit condition
            if time.time() - self.start_time >= self.time_limit:
                break

        return max(population, key=self.fitness)  # Return the individual which has the maximum fitness score

    def random_preference(self) -> nenv.OpponentModel.EstimatedPreference:
        """
            This method generates a random preferences for the initial population
        :return: Preferences with random weights
        """
        preference = nenv.OpponentModel.EstimatedPreference(self.reference)

        for issue in preference.issues:
            preference[issue] = self.rnd.random()

            for value_name in issue.values:
                preference[issue, value_name] = self.rnd.random()

        # Normalize
        preference.normalize()

        return preference

    def fitness(self, individual: nenv.OpponentModel.EstimatedPreference) -> float:
        """
            This method calculates the fitness score for the given individual.

            Fitness Function = 10 * spearman + (1 - low_diff) + (1 - high_diff)
        :param individual: Preference
        :return: Fitness score
        """

        # Calculate the spearman correlation
        bids = self.reference.bids

        org_indices = list(range(len(bids)))
        estimated_indices = list(range(len(bids)))

        random.shuffle(estimated_indices)

        estimated_indices = sorted(estimated_indices, key=lambda i: individual.get_utility(bids[i]), reverse=True)

        spearman, _ = spearmanr(org_indices, estimated_indices)

        # Calculate the utility difference of the highest and lowest bids
        low_diff = self.reference.min_util_bid.utility - individual.min_util_bid.utility
        high_diff = self.reference.max_util_bid.utility - individual.max_util_bid.utility

        # Calculate the fitness score
        return spearman * 10 + (1 - low_diff) + (1 - high_diff)

    def cross_over(self, parent1: nenv.OpponentModel.EstimatedPreference, parent2: nenv.OpponentModel.EstimatedPreference) -> nenv.OpponentModel.EstimatedPreference:
        """
            This method generates a child from the given parents
        :param parent1: Individual in the population
        :param parent2: Individual in the population
        :return: Generated child
        """

        # Parameters
        alpha = 0.3
        mutate_prob = 0.005

        child = nenv.OpponentModel.EstimatedPreference(self.reference)

        # Generate a child
        for issue in child.issues:
            # For issue weight
            w1 = parent1[issue]
            w2 = parent2[issue]

            low = min(w1, w2) - alpha * abs(w1 - w2)
            high = max(w1, w2) + alpha * abs(w1 - w2)

            w = self.rnd.random() * (high - low) + low
            w = max(w, 0.01)  # Weight must be >= 0.01

            # Apply mutation
            if self.rnd.random() < mutate_prob:
                w = self.rnd.random()

            child[issue] = w

            for value_name in issue.values:
                # For value weight
                w1 = parent1[issue, value_name]
                w2 = parent2[issue, value_name]

                low = min(w1, w2) - alpha * abs(w1 - w2)
                high = max(w1, w2) + alpha * abs(w1 - w2)

                w = self.rnd.random() * (high - low) + low
                w = max(w, 0.01)  # Weight must be >= 0.01

                # Apply mutation
                if self.rnd.random() < mutate_prob:
                    w = self.rnd.random()

                child[issue, value_name] = w

        return child

    def select_by_roulette(self, population: List[nenv.OpponentModel.EstimatedPreference], fitness_list: List[float]) -> List[nenv.OpponentModel.EstimatedPreference]:
        """
            This method applies Roulette approach to select next generation.
        :param population: Current population
        :param fitness_list: Fitness scores of the current population
        :return: Next generation
        """
        next_generation = []

        # Find the individual which has the highest fitness score
        max_fit = -1.0
        max_index = -1

        # Sum of the fitness scores
        fit_sum = 0.

        for i in range(len(fitness_list)):
            fit = fitness_list[i]

            if max_fit < fit:
                max_fit = fit
                max_index = i

            fit_sum += fit

        # The individual which has the highest fitness score always exists in the next generation
        next_generation.append(population[max_index])

        # The number of individuals in a generation must equal to population size
        for i in range(self.pop_size - 1):
            random_num = self.rnd.random() * fit_sum
            count = 0.

            for n in range(len(population)):
                count += fitness_list[n]

                if count > random_num:
                    next_generation.append(population[n])
                    break

        return next_generation
