from pytest import raises
import random

import matej.collections as mc


class TestCollections:
	def test_sumlike(self):
		assert mc.sum_([1, 2, 3]) == 6
		assert mc.sum_([1, 2, 3], init=5, value_if_empty=2) == 11
		assert not mc.sum_([])
		assert mc.sum_([], init=5) == 5
		assert mc.sum_([], init=5, value_if_empty=2) == 2
		assert mc.sum_([(1, 2), (3, 4)]) == (1, 2, 3, 4)
		assert mc.mul([1, 2, 3, 4]) == 24
		assert mc.union([{1, 2}, {2, 3}, {2, 4}, {3, 2}]) == {1, 2, 3, 4}
		assert mc.union([True, True, False])
		assert mc.intersection([{1, 2}, {2, 3}, {2, 4}, {3, 2}]) == {2}
		assert mc.intersection([{1, 2}, {2, 3}, {2, 4}, {3, 2}, {1, 3}]) == set()
		assert not mc.intersection([True, True, False])

	def test_ensure_iterable(self):
		assert not mc.is_iterable(1)
		assert mc.is_iterable([1])
		assert mc.is_iterable((1,))
		assert mc.is_iterable('asdf')
		assert mc.is_iterable('asdf', False)
		assert not mc.is_iterable('asdf', True)
		assert not mc.is_iterable('asdf', str)
		assert mc.is_iterable('asdf', bytes)
		assert mc.is_iterable(b'asdf', str)
		assert not mc.is_iterable(b'asdf', bytes)

		assert mc.ensure_iterable(1) == (1,)
		assert mc.ensure_iterable([1]) == [1]
		assert mc.ensure_iterable((1,)) == (1,)
		assert mc.ensure_iterable('asdf') == 'asdf'
		assert mc.ensure_iterable('asdf', False) == 'asdf'
		assert mc.ensure_iterable('asdf', True) == ('asdf',)
		assert mc.ensure_iterable('asdf', str) == ('asdf',)
		assert mc.ensure_iterable('asdf', bytes) == 'asdf'
		assert mc.ensure_iterable(b'asdf', str) == b'asdf'
		assert mc.ensure_iterable(b'asdf', bytes) == (b'asdf',)

	def test_shuffle(self):
		random.seed(42)  # Seed that doesn't result in the same list after shuffling
		l = [1, 2, 3, 4, 5]
		old_l = l.copy()
		mc.shuffle(l)
		assert l != old_l
		l = mc.shuffled(l)
		assert l != old_l
		assert type(l) is list
		assert type(mc.shuffled((1, 2, 3))) is tuple

	def test_flatten(self):
		assert list(mc.flatten([[[1, 2], 3], 4, 5, [6, [7, 8]]])) == [1, 2, 3, 4, 5, 6, 7, 8]
		assert list(mc.flatten([[1, 2], ['bc', 'ad']])) == [1, 2, 'bc', 'ad']
		assert list(mc.flatten([[1, 2], ['bc', 'ad']], flatten_strings=True)) == [1, 2, 'b', 'c', 'a', 'd']
		assert list(mc.flatten([[1, 2], {3: 'a', 4: 'b'}])) == [1, 2, 3, 4]
		assert list(mc.flatten([[1, 2], {3: 'a', 4: 'b'}], flatten_dicts=False)) == [1, 2, {3: 'a', 4: 'b'}]
		assert list(mc.flatten([[1, 2], (x for x in range(3))])) == [1, 2, 0, 1, 2]
		l = list(mc.flatten([[1, 2], (x for x in range(3))], flatten_generators=False))
		assert l[:2] == [1, 2]
		assert type(l[2]) == type((x for x in range(3)))

	def test_dotdict(self):
		d = mc.DotDict(a=1, b=2, c={'d': 3, 'e': {'f': 4}})
		assert d.a == 1
		assert d.b == 2
		assert d.c.d == 3
		assert d.c.e.f == 4
		assert d['a'] == 1
		assert d['b'] == 2
		assert d['c'].e.f == 4

	def test_treedict(self):
		d = mc.TreeDict()
		d['a']['b']['c'] = 1
		assert d['a']['b'] == {'c': 1}

	def test_sparse_grid(self):
		g = mc.SparseGrid()
		g[1, 2] = 's'
		g[10, 5] = 5
		g[10, 10] = 2
		assert g[1, 2] == 's'
		assert g[10, 5] == 5
		assert len(g) == 3
		assert 5 in g
		assert 6 not in g
		assert g.dimensions == 2
		assert list(g.coordinates()) == [(1, 2), (10, 5), (10, 10)]
		g.sort()
		assert list(g.values()) == ['s', 5, 2]
		g.sort(reverse=True)
		assert list(g.values()) == [2, 5, 's']
		g.sort(key=lambda x: x[1] if isinstance(x[1], int) else len(x[1]))
		assert list(g.values()) == ['s', 2, 5]

		g = mc.SparseMultiGrid()
		with raises(NotImplementedError):
			g[1, 2] = 3
		g.add((1, 2), 3)
		g.add((10, 5), 5)
		g.add((1, 2), 2)
		assert g[1, 2] == [3, 2]
		assert g[10, 5] == [5]
		assert g[1, 2, 0] == 3
		assert g[1, 2, -1] == 2
		assert len(g) == 3
		assert 5 in g
		assert 3 in g
		assert 2 in g
		assert 6 not in g
		assert g.dimensions == 2
		assert list(g.coordinates()) == [(1, 2), (10, 5)]
		g.sort(key=lambda x: sum(x[0]) + sum(x[1]))
		assert list(g.values()) == [[3, 2], [5]]
		g.sort(key=lambda x: sum(x[0]) + sum(x[1]), reverse=True)
		assert list(g.values()) == [[5], [3, 2]]
		g.remove(3)
		assert g[1, 2, 0] == g[1, 2, -1] == 2

	def test_dict_product(self):
		assert list(mc.dict_product({'a': [1, 2], 'b': [3, 4]})) == [{'a': 1, 'b': 3}, {'a': 1, 'b': 4}, {'a': 2, 'b': 3}, {'a': 2, 'b': 4}]

	def test_aliases(self):
		# map
		d = {1: 2, 3: 4}
		assert mc.dmap(lambda x: (x[0] + 1, x[1] + 2), d.items()) == {2: 4, 4: 6}
		assert d == {1: 2, 3: 4}
		mc.dmap_(lambda x: x + 1, d)
		assert d == {1: 3, 3: 5}
		l = [1, 2, 3]
		assert mc.tmap(lambda x: x + 1, l) == [2, 3, 4]
		assert l == [1, 2, 3]
		mc.lmap_(lambda x: x + 1, l)
		assert l == [2, 3, 4]
		assert mc.smap(lambda x: x + 1, (1, 2, 3)) == {2, 3, 4}
		assert mc.tmap(lambda x: x + 1, [1, 2, 3]) == (2, 3, 4)

		# filter
		assert mc.dfilter(lambda x: x[0] % 2 and not(x[1] % 2), ((1, 2), (3, 4), (5, 3))) == {1: 2, 3: 4}
		assert mc.lfilter(lambda x: x % 2, (1, 2, 3)) == [1, 3]
		assert mc.sfilter(lambda x: x % 2, (1, 2, 3)) == {1, 3}
		assert mc.tfilter(lambda x: x % 2, [1, 2, 3]) == (1, 3)

		# flatten
		# assert mc.dflatten() == ???   # dflatten doesn't make much sense
		assert mc.lflatten(((1, 2), (3, (4, 5)))) == [1, 2, 3, 4, 5]
		assert mc.sflatten(((1, 2), (3, (4, 5)))) == {1, 2, 3, 4, 5}
		assert mc.tflatten([(1, 2), (3, (4, 5))]) == (1, 2, 3, 4, 5)

		# zip
		assert mc.dzip([1, 2], [3, 4]) == {1: 3, 2: 4}
		assert mc.lzip((1, 2), (3, 4)) == [(1, 3), (2, 4)]
		assert mc.szip((1, 2), (3, 4)) == {(1, 3), (2, 4)}
		assert mc.tzip([1, 2], [3, 4]) == ((1, 3), (2, 4))
