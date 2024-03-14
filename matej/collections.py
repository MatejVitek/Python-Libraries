from collections import defaultdict
from collections.abc import Iterable, Mapping, Iterator, MutableMapping
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
	# True/False functionality for backward compatibility
	if noniterable_types is True:
		noniterable_types = (str, bytes)
	if noniterable_types not in (None, False) and isinstance(x, noniterable_types):
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
		    and ((flatten_strings and len(x) > 1) or not isinstance(x, (str, bytes)))
		    and (flatten_dicts or not isinstance(x, Mapping))
		    and (flatten_generators or not isinstance(x, Iterator))
		):
			yield from flatten(x, flatten_strings, flatten_dicts, flatten_generators)
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


class SparseGrid(MutableMapping):
	""" An n-dimensional grid saved in a sparse format. """

	def __init__(self, dimensions=2):
		self._dimensions = dimensions
		self._grid = {}

	def __getitem__(self, coords):
		return self._grid[coords]

	def __setitem__(self, coords, value):
		if len(coords) != self.dimensions:
			self._raise(coords)
		self._grid[coords] = value

	def __delitem__(self, coords):
		del self._grid[coords]

	def __len__(self):
		return len(self._grid)

	def __iter__(self):
		yield from self._grid.values()

	def __contains__(self, value):
		return value in self._grid.values()

	def _raise(self, coords):
		raise ValueError(f"Expected {self.dimensions} coordinates, got {len(coords)}: {coords}")

	def __repr__(self):
		return f"{type(self).__name__}({self._grid})"

	def __str__(self):
		return str(self._grid)

	@property
	def dimensions(self):
		return self._dimensions

	# coordinates is the preferred callname but we provide the identical keys method too, since we need it for **-unpacking
	def keys(self):
		return self._grid.keys()
	coordinates = keys

	# And we provide values to be compatible with Mapping
	def values(self):
		return self._grid.values()

	def items(self):
		return self._grid.items()

	def sort(self, key=None):
		"""
		Sort the elements.

		Parameters
		----------
		key : callable, optional
			Function used to determine the sort order.
			It should accept a single tuple argument containing the coordinate tuple and the corresponding value.
			By default, the coordinate sum is used. This way nearby coordinates are hopefully close in the final sorted order.
		"""
		self._grid = dict(sorted(self._grid.items(), key=key or self._sort_key))

	@staticmethod
	def _sort_key(coords_and_element):
		coords, _ = coords_and_element
		return sum(coords)


class SparseMultiGrid(SparseGrid):
	""" An `SparseGrid` that allows multiple values at the same coordinates. """

	def __init__(self, dimensions=2):
		super().__init__(dimensions)
		self._grid = defaultdict(list)

	def __getitem__(self, coords):
		if len(coords) == self.dimensions + 1:
			return self._grid[coords[:-1]][coords[-1]]
		return super().__getitem__(coords)

	def __setitem__(self, coords, value):
		if len(coords) == self.dimensions:
			raise NotImplementedError("Cannot set element in multi-grid. Use add method instead.")
		if len(coords) == self.dimensions + 1:
			self._grid[coords[:-1]][coords[-1]] = value
		else:
			self._raise(coords)

	def __delitem__(self, coords):
		if len(coords) == self.dimensions + 1:
			del self._grid[coords[:-1]][coords[-1]]
		else:
			return super().__delitem__(coords)

	def __len__(self):
		return sum(len(v) for v in self._grid.values())

	def __iter__(self):
		return it.chain.from_iterable(self._grid.values())

	def __contains__(self, value):
		return any(value in v for v in self._grid.values())

	def add(self, coords, value):
		if len(coords) != self.dimensions:
			self._raise(coords)
		return self[coords].append(value)

	def insert(self, coords, value, index=-1):
		if len(coords) == self.dimensions + 1:
			index = coords[-1]
			coords = coords[:-1]
		if len(coords) != self.dimensions:
			self._raise(coords)
		return self[coords].insert(index, value)

	def remove(self, value):
		for coords, values in self._grid.items():
			if value in values:
				values.remove(value)
				if not values:
					del self[coords]
				return

	def sort(self, *args, **kw):
		# We need to restore defaultdict functionality after sorting
		super().sort(*args, **kw)
		self._grid = defaultdict(list, self._grid)


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
	# print(sum_([1,2,3]))
	# print(sum_([1,2,3], init=5))
	# print(sum_([1,2,3], init=3, value_if_empty=None))
	# print(sum_([]))
	# print(sum_([], init=8))
	# print(sum_([], init=8, value_if_empty=12))
	# print(mul([1,2,3]))
	# print(mul([1,2,3], init=4))
	# print(mul([], init=4))
	# print(mul([], value_if_empty=6))
	# print(union([True, True, False]))
	# print(union([]))
	# print(intersection([True, True, False]))
	# print(intersection([]))

	g = SparseGrid(3)
	g[0,0,1] = 's'
	g[0,0,0] = 1
	g[0,0,0] = 3
	print(g)
	g.sort()
	print(g)
	print(g[0,0,0])
	print(g[0,0,1])

	g = SparseMultiGrid(3)
	# g[0,0,0] = 1  # NotImplementedError
	g.add((0,0,1), 's')
	g.add((0,0,0), 1)
	g.add((0,0,0), 3)
	print(g)
	g.sort()
	print(g)
	print(g[0,0,0])
	print(g[0,0,1])
	print(g[0,0,1,0])
	print(g[0,0,0,0])
	print(g[0,0,0,-1])
	g.remove(3)
	g.remove('s')
	print(g)
