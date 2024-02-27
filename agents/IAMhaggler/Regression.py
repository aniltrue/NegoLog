from typing import List
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor, kernels


class Regression:
    """
        This class helps for the prediction and training of the Gaussian Process Regression
    """
    regressor: GaussianProcessRegressor  # Scikit-Learn model
    kernel: kernels.Kernel               # Kernel
    means: np.ndarray                    # Predicted means
    sigma: np.ndarray                    # Predicted variances
    utility_samples: List[float]         # Utility sample list [0.01 - 1.00]
    time_samples_list: List[float]       # Time sample list [0.01 - 1.00]
    time_samples: np.ndarray             # Numpy array version of the time sample list

    def __init__(self):
        """
            Constructor
        """

        # Mixed kernel
        self.kernel = kernels.DotProduct() * kernels.Matern()

        # Model
        self.regressor = GaussianProcessRegressor(self.kernel)

        # Default values
        self.means = None
        self.sigma = None
        self.utility_samples = [i * 0.01 for i in range(101)]
        self.time_samples_list = [i * 0.01 for i in range(101)]
        self.time_samples = np.reshape(np.array(self.time_samples_list, dtype=np.float32), (-1, 1))

    def fit_and_predict(self, x: np.ndarray, y: np.ndarray, intercept: float, t_current: float, risk_factor: float = 3.0):
        """
            This method trains the model.
            Also, it returns predicted maximum negotiation time and predicted maximum utility at that time
        :param x: Adjusted negotiation time
        :param y: Utility
        :param intercept: First utility of the opponent
        :param t_current: Current negotiation time
        :param risk_factor: Risk factor, Default: 3.0
        :return: Predicted maximum negotiation time and predicted maximum utility at that time
        """

        # Train the model
        self.fit(x, y)

        # Predict mean and variance
        self.predict_mean_variance(intercept)

        # Predict a negotiation time that the opponent will make the highest concession
        max_time = self.predict_maximum_time(risk_factor, t_current)
        max_time_index = self.time_samples_list.index(max_time)

        # Predict the maximum utility in that time
        max_utility = self.predict_maximum_utility(risk_factor, self.means[max_time_index], self.sigma[max_time_index])

        return max_time, max_utility

    def fit(self, x: np.ndarray, y: np.ndarray):
        """
            This method trains the model.
        :param x: Adjusted negotiation time
        :param y: Utility
        :return: Nothing
        """
        self.regressor = GaussianProcessRegressor(self.kernel)
        self.regressor.fit(x, y)

    def predict_mean_variance(self, intercept: float):
        """
            This method predicts the mean and variance
        :param intercept: First utility of the opponent
        :return: Nothing
        """

        # Prediction by the model
        self.means, self.sigma = self.regressor.predict(self.time_samples, return_std=True)

        # adjust = first_utility + gradient * t
        adjust = intercept + self.time_samples * (0.9 - intercept)
        adjust = adjust.reshape((adjust.shape[0], ))

        self.means += adjust  # Adjusted mean

    def predict_maximum_time(self, risk_factor: float, t_current: float) -> float:
        """
            This method predicts the negotiation time when the opponent makes the highest concession.
        :param risk_factor: Risk factor
        :param t_current: Current negotiation time
        :return: Predicted negotiation time
        """
        time_map = {}   # Negotiation Time: Predicted Total Utility

        for i, t in enumerate(self.time_samples_list):
            total_utility = 0.  # Total utility value

            if t_current < t:  # Look only future negotiation times
                for utility in self.utility_samples:  # Iterate over all possible utility values
                    # Get normalized probability of the utility in that time
                    prob = self.normalized_probability(utility, self.means[i], self.sigma[i])
                    # Total Utility = sum(probability * utility ^ (risk factor))
                    total_utility += np.power(utility, risk_factor) * prob

            time_map[float(t)] = total_utility

        # Find the highest one by sorting based on predicted total utility.
        # Also, the highest t is prioritized.
        times = sorted(reversed(self.time_samples_list), key=lambda t: time_map[t], reverse=True)

        return times[0]

    def predict_maximum_utility(self, risk_factor: float, mu: float, sigma: float) -> float:
        """
            This method predicts the highest utility that the opponent makes in the given negotiation time.
        :param risk_factor: Risk factor
        :param mu: Mean of the negotiation time
        :param sigma: Stdev. of the negotiation time
        :return: Predicted maximum utility
        """
        cumulative_prob = 0.

        utility_map = {}

        for utility in self.utility_samples:
            # Get normalized probability of the utility in that time
            prob = self.normalized_probability(utility, mu, sigma)
            utility_map[utility] = np.power(utility, risk_factor) * (cumulative_prob + prob)
            cumulative_prob += prob

        # Find the highest one by sorting.
        utilities = sorted(self.utility_samples, key=lambda u: utility_map[u], reverse=True)

        return utilities[0]

    def normalized_probability(self, utility: float, mu: float, sigma: float) -> float:
        """
            This method normalizes the probability for the given utility.
        :param utility: Utility value
        :param mu: Mean of the distribution
        :param sigma: Stdev. of the distribution
        :return: Normalized probability.
        """
        return self.get_probability(utility, mu, sigma) / \
               (self.get_probability(1., mu, sigma) - self.get_probability(0., mu, sigma))

    def get_probability(self, utility: float, mu: float, sigma: float) -> float:
        """
            This method calculates the probability for the given utility via PDF of Gaussian Distribution.
        :param utility: Utility value
        :param mu: Mean of the distribution
        :param sigma: Stdev. of the distribution
        :return: Probability
        """
        return np.exp(-np.power(utility - mu, 2.) / (2. * sigma * sigma)) / (sigma * np.sqrt(2. * np.pi))
