import random

import numpy as np


class Regression:
    w1: float
    w2: float
    initial_utility: float
    y: float
    __grad_w1_squared: float
    __grad_w2_squared: float
    __cost: float
    __counter: int

    def __init__(self, initial_utility: float):
        self.y = 0.
        self.initial_utility = initial_utility
        self.w1 = random.gauss(mu=0., sigma=0.01)
        self.w2 = random.gauss(mu=0., sigma=0.01)
        self.__grad_w1_squared = None
        self.__grad_w2_squared = None
        self.__cost = -1
        self.__counter = 0

    def feed_forward(self, x: float) -> float:
        self.y = self.initial_utility + np.exp(self.w1) * np.power(x, self.w2)

        return self.y

    def __feed_forward(self, x: np.ndarray):
        return self.initial_utility + np.exp(self.w1) * np.power(x, self.w2)

    def __grad_w1(self, x: np.ndarray):
        return np.exp(self.w1) * np.power(x, self.w2)

    def __grad_w2(self, x: np.ndarray):
        return np.exp(self.w1) * np.power(x, self.w2) * np.log(x)

    def fit(self, x: list, y: list, weights: list, epoch: int = 1, lr: float = 0.001, rho: float = 0.9, epsilon: float = 1e-8, lr_decay: float = .9):
        x = np.array(x, dtype=np.float32)
        y = np.array(y, dtype=np.float32)
        weights = np.array(weights, dtype=np.float32)
        weights /= np.sum(weights)

        # self.w1 = random.gauss(mu=0., sigma=0.01)
        # self.w2 = random.gauss(mu=0., sigma=0.01)

        self.__counter = 0
        self.__cost = -1

        for _ in range(epoch):
            y_pred = self.__feed_forward(x)

            cost = np.sum(np.power(y - y_pred, 2.) * weights)

            if self.__cost != -1 and cost >= self.__cost:
                self.__counter += 1

                if self.__counter == 5:
                    lr *= lr_decay
                    self.__counter = 0

            self.__cost = float(cost)

            grad_base = 2 * (y - y_pred) * weights

            grad_w1 = np.sum(grad_base * self.__grad_w1(x))
            grad_w2 = np.sum(grad_base * self.__grad_w2(x))

            if self.__grad_w1_squared is None:
                self.__grad_w1_squared = grad_w1 * grad_w1
            else:
                self.__grad_w1_squared = rho * self.__grad_w1_squared + (1 - rho) * grad_w1 * grad_w1
                sqrt = np.sqrt(self.__grad_w1_squared + epsilon)
                grad_w1 /= sqrt

            if self.__grad_w2_squared is None:
                self.__grad_w2_squared = grad_w2 * grad_w2
            else:
                self.__grad_w2_squared = rho * self.__grad_w2_squared + (1 - rho) * grad_w2 * grad_w2
                sqrt = np.sqrt(self.__grad_w2_squared + epsilon)
                grad_w2 /= sqrt

            self.w1 -= lr * grad_w1
            self.w2 -= lr * grad_w2
