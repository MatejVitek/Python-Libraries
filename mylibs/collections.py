from collections.abc import Mapping
import random

from mylibs.general import Singleton


class _Zero(metaclass=Singleton):
	def __add__(self, other):
		return other

	def __radd__(self, other):
		return other

ZERO = _Zero()


def sum_(it, start=None):
	if start is not None:
		return sum(it, start)
	try:
		return sum(it, 0)
	except TypeError:
		return sum(it, ZERO)


def ensure_iterable(x, process_single_string=False):
	if isinstance(x, str) and listify_single_string:
		return x,
	try:
		_ = iter(x)
		return x
	except TypeError:
		try:
			for _ in x:
				pass
			return x
		except TypeError:
			return x,


def shuffle(l):
	random.shuffle(l)
	return l


class DotDict(dict):
	def __init__(self, *args, **kwargs):
		d = dict(*args, **kwargs)
		for key, val in d.items():
			if isinstance(val, Mapping):
			    value = DotDict(val)
			else:
			    value = val
			self[key] = value

	def __delattr__(self, name):
		try:
			del self[name]
		except KeyError as ex:
			raise AttributeError(f"No attribute called: {name}") from ex

	def __getattr__(self, k):
		try:
			return self[k]
		except KeyError as ex:
			raise AttributeError(f"No attribute called: {k}") from ex

	__setattr__ = dict.__setitem__
