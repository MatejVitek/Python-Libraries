from functools import reduce
import math
import operator as op


def ncr(n, r):
    r = min(r, n - r)
    numerator = reduce(op.mul, range(n - r + 1, n + 1), 1)
    return numerator // math.factorial(r)


def dfactorial(n):
    return reduce(op.mul, range(n, 2, -2), 1)
