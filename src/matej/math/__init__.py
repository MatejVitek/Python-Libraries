from copy import deepcopy
from functools import reduce
import math
import multiprocessing
import numpy as np
import operator as op
import threading

from matej import Singleton


class _Zero(metaclass=Singleton):
	def __add__(self, other):
		return other

	__radd__ = __add__

	def __mul__(self, other):
		return self

	__rmul__ = __mul__

	def __or__(self, other):
		return other

	__ror__ = __or__

	def __and__(self, other):
		return self

	__rand__ = __and__

	def __bool__(self):
		return False

	def __str__(self):
		return "0"

	def __index__(self):
		return 0

ZERO = _Zero()


class _One(metaclass=Singleton):
	def __mul__(self, other):
		return other

	__rmul__ = __mul__

	def __or__(self, other):
		return self

	__ror__ = __or__

	def __and__(self, other):
		return other

	__rand__ = __and__

	def __bool__(self):
		return True

	def __str__(self):
		return "1"

	def __index__(self):
		return 1

ONE = _One()


def ncr(n, r):
	r = min(r, n - r)
	numerator = reduce(op.mul, range(n - r + 1, n + 1), 1)
	return numerator // math.factorial(r)


def dfactorial(n):
	return reduce(op.mul, range(n, 2, -2), 1)


_ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}
def ordinal(n):
	suffix = "th" if 10 <= n % 100 <= 20 else _ORDINAL_SUFFIXES.get(n % 10, "th")
	return str(n) + suffix


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

		self._init_lock()

	# Welford's algorithm update step
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

	def last(self, n=1):
		if n == 1:
			return self._cache[-1] if self._cache else None
		elif n == 'all':
			return list(self._cache)
		else:
			return self._cache[-n:]

	def latex(self, *args, include_name=True, format_f=np.format_float_positional, **kw):
		result = f"{self.name} & " if include_name else ""
		mean = format_f(self.mean, *args, **kw)
		std = format_f(self.std, *args, **kw)
		result += "$" + (fr"{mean} \pm {std}" if self.std else mean) + "$"
		return result

	def __str__(self):
		if self.std:
			#return f"{self.name} (\u03BC \u00B1 \u03C3): {self.mean} \u00B1 {self.std}"
			return f"{self.name} (μ ± σ): {self.mean} ± {self.std}"
		else:
			return f"{self.name}: {self.mean}"

	def __len__(self):
		return self._n

	def _init_lock(self):
		if self._parallel == 'multiprocessing':
			self._lock = multiprocessing.Lock()
		elif self._parallel == 'threading':
			self._lock = threading.Lock()

	# Support for pickling and deepcopy
	def __getstate__(self):
		state = self.__dict__.copy()
		if '_lock' in state:
			del state['_lock']
		return state

	def __setstate__(self, state):
		self.__dict__ = state
		self._init_lock()

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

	def __or__(self, other):
		return deepcopy(self).__ior__(other)
