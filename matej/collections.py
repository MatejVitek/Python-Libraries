from collections.abc import Mapping
from functools import reduce
import random

from matej import ZERO


def sum_(it, start=None):
	if start is not None:
		return sum(it, start)
	try:
		return sum(it)
	except TypeError:
		return sum(it, ZERO)


def ensure_iterable(x, process_single_string=False):
	if isinstance(x, str) and process_single_string:
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


def shuffled(l):
	new_l = random.sample(l, len(l))
	try:
		return type(l)(new_l)
	except TypeError:
		return new_l


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


def lmap(*args, **kw):
	return list(map(*args, **kw))


def smap(*args, **kw):
	return set(map(*args, **kw))


def tmap(*args, **kw):
	return tuple(map(*args, **kw))


def lfilter(*args, **kw):
	return list(filter(*args, **kw))


def sfilter(*args, **kw):
	return set(filter(*args, **kw))


def tfilter(*args, **kw):
	return tuple(filter(*args, **kw))


def lreduce(*args, **kw):
	return list(reduce(*args, **kw))


def sreduce(*args, **kw):
	return set(reduce(*args, **kw))


def treduce(*args, **kw):
	return tuple(reduce(*args, **kw))


def lzip(*args, **kw):
	return list(zip(*args, **kw))


def szip(*args, **kw):
	return set(zip(*args, **kw))


def tzip(*args, **kw):
	return tuple(zip(*args, **kw))
