from functools import reduce
import math
import numpy as np
import operator as op


def ncr(n, r):
    r = min(r, n - r)
    numerator = reduce(op.mul, range(n - r + 1, n + 1), 1)
    return numerator // math.factorial(r)


def dfactorial(n):
    return reduce(op.mul, range(n, 2, -2), 1)
    

class RunningStatisticsVar:
	def __init__(self, name="", init_values=None, ddof=0, cache_len=100):
		self.name = name

		self.mean = 0
		self.var = 0
		self.std = 0

		self._n = 0
		self._s = 0
		self._ddof = ddof
		
		self._cache = []
		self._cache_len = cache_len

		if init_values is not None:
			self.update(init_values)

	def update(self, values):
		values = np.array(values, ndmin=1)
		n = len(values)
		
		self._n += n
		self._cache.extend(values)
		self._cache = self._cache[-self._cache_len:]
		
		delta = values - self.mean
		self.mean += (delta / self._n).sum()
		
		self._s += (delta * (values - self.mean)).sum()
		self.var = self._s / (self._n - self._ddof) if self._n > self._ddof else 0
		self.std = np.sqrt(self.var)

	def update_single(self, value):
		self._n += 1
		self._cache.append(value)
		self._cache = self._cache[-self._cache_len:]

		old_mean = self.mean
		self.mean += (value - old_mean) / self._n

		self._s += (value - old_mean) * (value - self.mean)
		self.var = self._s / (self._n - self._ddof) if self._n > self._ddof else 0
		self.std = np.sqrt(self.var)
		
	def last(self, n=1):
		if n == 1:
			return self._cache[-1] if self._cache else None
		else:
			return self._cache[-n:]

	def __str__(self):
		if self.std:
			return f"{self.name} (\u03BC \u00B1 \u03C3): {self.mean} \u00B1 {self.std}"
		else:
			return f"{self.name}: {self.mean}"

	def __len__(self):
		return self._n
