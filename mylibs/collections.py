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


def shuffle(l):
	random.shuffle(l)
	return l
