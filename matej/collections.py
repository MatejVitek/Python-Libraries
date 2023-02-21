from collections import defaultdict
from collections.abc import Iterable, Mapping, Iterator
import itertools as it
from functools import reduce
import operator as op
import random
from typing import List, Dict, Set, Tuple, Callable

from matej.callable import compose
from matej.math import ZERO, ONE


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


def is_iterable(x, noniterable_types=None):
	if noniterable_types is True:
		noniterable_types = (str, bytes)
	if noniterable_types is not None and isinstance(x, noniterable_types):
		return False
	try:
		for _ in x:
			break
		return True
	except Exception:  #pylint: disable=broad-except  # Can't just catch TypeError because other exceptions can be raised in some cases
		return False


def ensure_iterable(x, tuplify_single=None):
	return x if is_iterable(x, tuplify_single) else (x,)


def shuffle(l):
	random.shuffle(l)
	return l


def shuffled(l):
	new_l = random.sample(l, len(l))
	try:
		return type(l)(new_l)
	except TypeError:
		return new_l


def flatten(l, flatten_strings=False, flatten_dicts=True, flatten_generators=True):
	for x in l:
		if (
			is_iterable(x)
		    and (flatten_strings or not isinstance(x, (str, bytes)))
		    and (flatten_dicts or not isinstance(x, Mapping))
		    and (flatten_generators or not isinstance(x, Iterator))
		):
			yield from flatten(x)
		else:
			yield x


class DotDict(dict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for key, val in self.items():
			if isinstance(val, Mapping):
				self[key] = DotDict(val)

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


# dmap, lmap, lfilter, etc. which are equivalent to dict(map(...)), list(map(...)), list(filter(...)), etc.
# lmap_ and dmap_ are in-place versions of lmap and dmap
# First we define the types and initialise to a placeholder value (these three lines are just for type hinting and to avoid warnings)
_d = Callable[[Iterable], Dict]; _l = Callable[[Iterable], List]; _s = Callable[[Iterable], Set]; _t = Callable[[Iterable], Tuple]
dmap: _d; dmap_: _d; dfilter: _d; dzip: _d; dflatten: _d; lmap: _l; lmap_: _l; lfilter: _l; lzip: _l; lflatten: _l; smap: _s; sfilter: _s; szip: _s; sflatten: _s; tmap: _t; tfilter: _t; tzip: _t; tflatten: _t
dmap = dmap_ = dfilter = dzip = dflatten = lmap = lmap_ = lfilter = lzip = lflatten = smap = sfilter = szip = sflatten = tmap = tfilter = tzip = tflatten = lambda *_, **__: None
# And now we actually generate the functions and their docs
for col, func in it.product((dict, list, set, tuple), (map, filter, zip, flatten)):
	# The name is the first letter of the collection followed by the name of the function
	_name = f"{col.__name__[0]}{func.__name__}"

	# Compose the collection constructor and the function
	globals()[_name] = compose(col, func)
	globals()[_name].__doc__ = f""" Composition of {col.__name__} and {func.__name__}, equivalent to {col.__name__}({func.__name__}(...)). """

	# For mapping mutable collections, we also define an in-place version
	if col in (list, dict):
		def _func(f, ld):
			iterator = enumerate(ld) if isinstance(ld, list) else ld.items()
			for k, v in iterator:
				ld[k] = f(v)
			return ld
		globals()[_name + "_"] = _func
		globals()[_name + "_"].__doc__ = f""" In-place mapping of passed function on {col.__name__}. """


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
