from collections import defaultdict
from collections.abc import Iterable, Mapping
import itertools as it
from functools import partial, reduce
import operator as op
import random


# These will work without an explicit initial value, as is required for the built-in sum when not working with ints
# However they will fail on an empty array if an initial value isn't given
sum_ = partial(reduce, op.add)
mul = partial(reduce, op.mul)
union = partial(reduce, op.or_)
intersection = partial(reduce, op.and_)


def ensure_iterable(x, process_single_string=False):
	if isinstance(x, str) and process_single_string:
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


# Recursive defaultdict
treedict = lambda: defaultdict(treedict)


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
