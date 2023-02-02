from collections import defaultdict
from collections.abc import Iterable, Mapping
import itertools as it
from functools import reduce
import operator as op
import random

from matej import ZERO, ONE


_DEFAULT = object()
def _reductify(f, default_init=ZERO):
	def _reduce(iterable, init=default_init, value_if_empty=_DEFAULT):
		if not iterable and value_if_empty is not _DEFAULT:
			return value_if_empty
		return reduce(f, iterable, init)
	return _reduce
# Sum-like methods for different operators that will work even without an explicit initial value
# Can optionally specify a different value (such as None) to return if the iterable is empty
sum_ = _reductify(op.add)
mul = _reductify(op.mul, ONE)
union = _reductify(op.or_)
intersection = _reductify(op.and_, ONE)


def ensure_iterable(x, tuplify_single=None):
	if tuplify_single is not None and isinstance(x, tuplify_single):
		return x,
	try:
		iter(x)
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


def shuffled(l):
	new_l = random.sample(l, len(l))
	try:
		return type(l)(new_l)
	except TypeError:
		return new_l


def flatten(l):
	for x in l:
		if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
			yield from flatten(x)
		else:
			yield x


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


# Recursive defaultdict (we use a proper function instead of a lambda so that treedict objects are picklable)
def treedict():
	return defaultdict(treedict)


def dict_product(d):
	"""
	Cartesian product of all possible values for the corresponding keys.

	Example::

		>>> list(dict_product({'a': [1, 2], 'b': [3, 4]}))
		[{'a': 1, 'b': 3}, {'a': 1, 'b': 4}, {'a': 2, 'b': 3}, {'a': 2, 'b': 4}]
	"""
	for x in it.product(*d.values()):
		yield dzip(d, x)


def dmap(*args, **kw):
	return dict(map(*args, **kw))


def lmap(*args, **kw):
	return list(map(*args, **kw))


def smap(*args, **kw):
	return set(map(*args, **kw))


def tmap(*args, **kw):
	return tuple(map(*args, **kw))


def dfilter(*args, **kw):
	return dict(filter(*args, **kw))


def lfilter(*args, **kw):
	return list(filter(*args, **kw))


def sfilter(*args, **kw):
	return set(filter(*args, **kw))


def tfilter(*args, **kw):
	return tuple(filter(*args, **kw))


def dzip(*args, **kw):
	return dict(zip(*args, **kw))


def lzip(*args, **kw):
	return list(zip(*args, **kw))


def szip(*args, **kw):
	return set(zip(*args, **kw))


def tzip(*args, **kw):
	return tuple(zip(*args, **kw))


if __name__ == '__main__':
	print(sum_([1,2,3]))
	print(sum_([1,2,3], init=5))
	print(sum_([1,2,3], init=3, value_if_empty=None))
	print(sum_([]))
	print(sum_([], init=8))
	print(sum_([], init=8, value_if_empty=12))
	print(mul([1,2,3]))
	print(mul([1,2,3], init=4))
	print(mul([], init=4))
	print(mul([], value_if_empty=6))
	print(union([True, True, False]))
	print(union([]))
	print(intersection([True, True, False]))
	print(intersection([]))
