from copy import deepcopy
from functools import reduce
import math
import multiprocessing
import numpy as np
import operator as op
import threading


def ncr(n, r):
	r = min(r, n - r)
	numerator = reduce(op.mul, range(n - r + 1, n + 1), 1)
	return numerator // math.factorial(r)


def dfactorial(n):
	return reduce(op.mul, range(n, 2, -2), 1)


class RunningStats:
	def __init__(self, name="", init_values=None, ddof=0, parallel=None, max_cache_size=100):
		self.name = name

		self.mean = 0
		self.var = 0
		self.std = 0

		self._n = 0
		self._s = 0
		self._ddof = ddof
		self._parallel = parallel
		self._lock = None

		self._cache = []
		self._cache_len = max_cache_size

		if init_values is not None:
			self.update(init_values)

		if self._parallel == 'multiprocessing':
			self._lock = multiprocessing.Lock()
		elif self._parallel == 'threading':
			self._lock = threading.Lock()

	# Welford's algorithm update step for multiple values
	def update(self, values):
		if self._parallel:
			self._lock.acquire()

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

		if self._parallel:
			self._lock.release()

	# Welford's algorithm update step for single value
	def update_single(self, value):
		if self._parallel:
			self._lock.acquire()

		self._n += 1
		self._cache.append(value)
		self._cache = self._cache[-self._cache_len:]

		old_mean = self.mean
		self.mean += (value - old_mean) / self._n

		self._s += (value - old_mean) * (value - self.mean)
		self.var = self._s / (self._n - self._ddof) if self._n > self._ddof else 0
		self.std = np.sqrt(self.var)

		if self._parallel:
			self._lock.release()

	def last(self, n=1):
		if n == 1:
			return self._cache[-1] if self._cache else None
		elif n == 'all':
			return list(self._cache)
		else:
			return self._cache[-n:]

	def __str__(self):
		if self.std:
			#return f"{self.name} (\u03BC \u00B1 \u03C3): {self.mean} \u00B1 {self.std}"
			return f"{self.name} (μ ± σ): {self.mean} ± {self.std}"
		else:
			return f"{self.name}: {self.mean}"

	def __len__(self):
		return self._n

	def __deepcopy__(self, memo):
		result = type(self)()
		result.__dict__.update({
			k: deepcopy(v)
			for k, v in self.__dict__.items()
			if k != '_lock'
		})

		if result._parallel == 'multiprocessing':
			result._lock = multiprocessing.Lock()
		elif result._parallel == 'threading':
			result._lock = threading.Lock()

		return result

	# Pooling
	def __or__(self, other):
		return deepcopy(self).__ior__(other)

	# Concatenated streams (https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Parallel_algorithm)
	def __ior__(self, other):
		if self._parallel:
			self._lock.acquire()

		n = self._n + other._n
		delta = other.mean - self.mean
		self.mean = (self._n * self.mean + other._n * other.mean) / n
		self._s += other._s + delta ** 2 * self._n * other._n / n
		self.var = self._s / (n - self._ddof)
		self.std = np.sqrt(self.var)
		self._n = n

		if self._parallel:
			self._lock.release()

		return self
