from abc import ABCMeta, abstractmethod
from enum import Enum, EnumMeta
from functools import lru_cache, total_ordering


# Ordered Enums courtesy of https://blog.yossarian.net/2020/03/02/Totally-ordered-enums-in-python-with-ordered_enum
@total_ordering
class OrderedEnum(Enum):
	@classmethod
	@lru_cache(maxsize=None)
	def _member_list(cls):
		return list(cls)

	def __lt__(self, other):
		if type(self) is not type(other):
			return NotImplemented
		member_list = self._member_list()
		return member_list.index(self) < member_list.index(other)


@total_ordering
class ValueOrderedEnum(Enum):
	def __lt__(self, other):
		if type(self) is not type(other):
			return NotImplemented
		return self.value < other.value


class AbstractEnumMeta(EnumMeta, ABCMeta):
	pass


class Lazy:
	""" Member wrapper for use with the :class:`SometimesLazyEnum` class from this module. """
	def __init__(self, *lazy_init_args):
		self.args = lazy_init_args


class SometimesLazyEnum(Enum, metaclass=AbstractEnumMeta):
	"""
	An :class:`Enum` subclass that allows lazy evaluation only for selected members.

	This class functions like a standard :class:`Enum` but will only evaluate the value of the members
	wrapped in :class:`Lazy` upon first access of their `value` attribute. For detailed usage instructions
	refer to the documentation of the original :class:`Enum` class.

	Subclasses must implement the :meth:`_lazy_init` method, which computes the actual value from the arguments
	passed at the `Enum` creation.

	Sample usage::

		class MyEnum(SometimesLazyEnum):
			X = Lazy('x')
			Y = Lazy('y')
			Z = 'z'

			@classmethod
			def _lazy_init(cls, value):
				print(f"Lazy init of {value}")
				return value * 2

		>>> MyEnum.Z
		MyEnum.Z
		>>> MyEnum.Z.value
		'z'
		>>> MyEnum.X
		MyEnum.X
		>>> MyEnum.X.value
		Lazy init of x
		'xx'
		>>> MyEnum.X.value
		'xx'
	"""

	def __getattribute__(self, name):
		result = super().__getattribute__(name)
		if name == 'value' and isinstance(result, Lazy):
			result = self._lazy_init(*result.args)
			self._value_ = result  #pylint: disable=attribute-defined-outside-init  # Hacky solution but it works
		return result

	@classmethod
	@abstractmethod
	def _lazy_init(cls, *args):
		""" This method must be overridden to return the actual value of a member from the originally passed arguments. """
		return args


class LazyEnum(SometimesLazyEnum):  #pylint:disable=abstract-method
	"""
	An :class:`Enum` subclass with lazy evaluation.

	This class functions like a standard :class:`Enum` but will only evaluate the value of its members
	upon first access of their `value` attribute. For detailed usage instructions refer to the documentation
	of the original :class:`Enum` class.

	Subclasses must implement the :meth:`_lazy_init` method, which computes the actual value from the arguments
	passed at the `Enum` creation.

	Sample usage::

		class MyEnum(LazyEnum):
			X = 'x'
			Y = 'y'
			Z = 'z'

			@classmethod
			def _lazy_init(cls, value):
				print(f"Lazy init of {value}")
				return value * 2

		>>> MyEnum.Z
		MyEnum.Z
		>>> MyEnum.Z.value
		Lazy init of z
		'z'
		>>> MyEnum.X
		MyEnum.X
		>>> MyEnum.X.value
		Lazy init of x
		'xx'
		>>> MyEnum.X.value
		'xx'
	"""

	def __init__(self, *args):
		super().__init__()
		self._value_ = Lazy(*args)
