import random

import matej.collections as mc


class TestCollections:
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