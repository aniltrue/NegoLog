import math


def subtract(a: list, b: list) -> list:
    return [a[i] - b[i] for i in range(len(a))]


def equals(a: list, b: list, precision: float) -> bool:
    distances = subtract(a, b)

    for i in range(len(a)):
        if distances[i] > precision:
            return False

    return True


def getEuclideanDistance(a: list, b: list) -> float:
    distance = 0.

    for i in range(len(a)):
        distance = math.pow(a[i] - b[i], 2)

    return math.sqrt(distance)


def norm(a: list) -> float:
    return math.sqrt(a[-1] * a[-1])


def divide(a: list, number: float) -> list:
    return [a[i] / number for i in range(len(a))]


def add(a: list, b: list) -> list:
    return [a[i] + b[i] for i in range(len(a))]


def multiply(a: list, number: float) -> list:
    return [a[i] * number for i in range(len(a))]


def calculateUnitVector(a: list, b: list) -> list:
    unitVector = subtract(b, a)
    normed = norm(unitVector)

    if normed == 0.:
        unitVector = multiply(unitVector, 0.)
    else:
        unitVector = divide(unitVector, normed)

    return unitVector


def normalize(a: list) -> list:
    return divide(a, sum(a))


def toString(a: list, delimiter: str) -> str:
    return delimiter.join(a)
