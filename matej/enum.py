from abc import ABCMeta, abstractmethod
from enum import Enum, EnumMeta
from functools import lru_cache, total_ordering

from matej.collections import lmap, sum_


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
	""" Metaclass for abstract Enum classes (using decorators from `abc`)

	Usage:
	>>> class MyEnum(Enum, metaclass=AbstractEnumMeta):
	... 	# This method must be overridden in subclasses
	... 	@abstractmethod
	... 	def my_method(self):
	... 		pass
	...
	"""


class DirectEnumMeta(EnumMeta):
	""" Metaclass for Enum classes that allow direct access to the member values as the members themselves, such as:
	>>> class MyEnum(Enum, metaclass=DirectEnumMeta):
	... 	X = 1
	...
	>>> MyEnum.X
	1
	"""

	def __getattribute__(cls, name):
		result = super().__getattribute__(name)
		if isinstance(result, cls):
			result = result.value
		return result


class AbstractDirectEnumMeta(AbstractEnumMeta):
	""" Metaclass that combines the functionalities of `AbstractEnumMeta` and `DirectEnumMeta`.

	This class does not allow member names to start with an underscore (_).

	Usage:
	>>> class MyEnum(Enum, metaclass=AbstractDirectEnumMeta):
	... 	...
	...
	"""

	def __getattribute__(cls, name):
		result = super().__getattribute__(name)
		if not name.startswith('_') and isinstance(result, cls):
			result = result.value
		return result


class LazyEnum(Enum, metaclass=AbstractEnumMeta):
	""" An abstract subclass of `Enum` that supports lazy evaluation of the members' values and attributes.

	Subclasses must implement the `_lazy_init` method, which takes the arguments from
	the member's definition and returns the actual value (such as reading an image from a path).
	It can also initialise other attributes of the member. The names of these attributes shouldn't start
	with underscores (`_`).

	When reimplementing `__init__` in a subclass, call `super().__init__` with the arguments
	you wish to use for `_lazy_init`. By default all the arguments are passed. If your `__init__`
	passes no arguments to `super().__init__`, lazy initialisation won't be used.
	Note that lazy initialisation will only be triggered by references to either the `value` attribute
	or attributes that weren't initialised in your `__init__` method.
	See the `MixedEnum` class for an example that reimplements `__init__` to allow mixing
	regular and lazy initialisation via the `Lazy` wrapper.

	Usage:
	>>> class MyLazyEnum(LazyEnum):
	... 	X = 'x'
	... 	Y = 'y'
	...
	... 	def _lazy_init(self, value):
	... 		print(f"Lazy init of {value}")
	... 		self.letter = value
	... 		return value * 2
	...
	>>> MyLazyEnum.X
	MyLazyEnum.X
	>>> MyLazyEnum.X.letter
	Lazy init of x
	'x'
	>>> MyLazyEnum.X.value
	'xx'
	>>> MyLazyEnum.X.letter
	'x'
	>>> MyLazyEnum.Y.value
	Lazy init of y
	'yy'
	>>> MyLazyEnum.Y.value
	'yy'
	"""

	def __init__(self, *args):
		self._lazy_args = args

	def __getattribute__(self, name):
		if name.startswith('_') or self._lazy_args is None or (name != 'value' and name in self.__dict__):
			return super().__getattribute__(name)
		result = self._lazy_init(*self._lazy_args)
		self._lazy_args = None
		if result is not None:
			self._value_ = result  #pylint: disable = attribute-defined-outside-init
		return getattr(self, name)

	@abstractmethod
	def _lazy_init(self, *args):
		pass


class LazyDirectEnum(LazyEnum, metaclass=AbstractDirectEnumMeta):
	""" An abstract `Enum` that supports lazy initialisation and also direct access to members' values.

	Note that `_lazy_init` is a classmethod in this class, as the member itself will be replaced by
	the value returned by `_lazy_init` at the end of its execution anyway.

	Usage:
	>>> class MyLazyDirectEnum(LazyDirectEnum):
	... 	X = 'x'
	... 	Y = 'y'
	...
	... 	@classmethod
	... 	def _lazy_init(cls, value):
	... 		print(f"Lazy init of {value}")
	... 		return value * 2
	...
	>>> MyLazyDirectEnum
	<enum 'MyLazyDirectEnum'>
	>>> MyLazyDirectEnum.X
	Lazy init of x
	'xx'
	>>> MyLazyDirectEnum.X
	'xx'
	>>> MyLazyDirectEnum.Y
	Lazy init of y
	'yy'
	"""

	@classmethod
	@abstractmethod
	def _lazy_init(cls, *args):
		# Keep this method abstract
		return args


class Lazy:
	""" Member wrapper for use with the :class:`LazyEagerEnum` class from this module. """
	def __init__(self, *lazy_init_arguments):
		self.args = lazy_init_arguments

	def __str__(self):
		return f"Lazy({self.args[0] if len(self.args) == 1 else lmap(str, self.args)})"


class LazyEagerEnum(LazyEnum):
	"""
	An abstract subclass of `LazyEnum` that supports mixing of regular `__init__` initialisation
	with lazy initialisation of the value via the `Lazy` wrapper (see below for an example).
	*Note that if several `Lazy`s appear in a single value, their argument lists will be concatenated.*

	When reimplementing `__init__` in a subclass, call this class' `__init__` to properly parse out
	the `Lazy` arguments. After the call, the remaining arguments will be in `self.init_args`.

	Usage:
	>>> class MyMixedEnum(LazyEagerEnum):
	... 	X = Lazy(1)
	... 	Y = 'y', Lazy(2), 'w', Lazy(3, 4)  # Only values in Lazy will be passed to _lazy_init
	... 	Z = 'z', 'a'  # Since there are no Lazy values, lazy initialisation won't be used
	...
	... 	def __init__(self, *args):
	... 		super().__init__(*args)
	... 		self.letters = ','.join(self.init_args)
	...
	... 	def _lazy_init(self, *numbers):
	... 		print("Lazy init called")
	... 		self.numbers = list(numbers)
	... 		return sum(numbers)
	...
	>>> MyMixedEnum.X
	MyMixedEnum.X
	>>> MyMixedEnum.X.letters
	''
	>>> MyMixedEnum.X.numbers
	Lazy init called
	[1]
	>>> MyMixedEnum.X.value
	1
	>>> MyMixedEnum.X.numbers
	[1]
	>>> MyMixedEnum.Y.letters
	'y,w'
	>>> MyMixedEnum.Y.value
	Lazy init called
	9
	>>> MyMixedEnum.Y.numbers
	[2, 3, 4]
	>>> MyMixedEnum.Z.letters
	'z,a'
	>>> MyMixedEnum.Z.value
	('z', 'a')
	>>> MyMixedEnum.Z.numbers  # Lazy initialisation wasn't used so this raises an error
	AttributeError: 'MyMixedEnum' object has no attribute 'numbers'
	"""

	def __init__(self, *args):
		# If we wanted to actually remove the lazy arguments from the __init__ call (so that we wouldn't need self.init_args),
		# we'd need to override __call__ in the metaclass. Since this is a horrid idea for Enums, we use this solution instead.
		lazy_args = sum_(arg.args for arg in args if isinstance(arg, Lazy))
		if lazy_args:
			super().__init__(*lazy_args)
		else:
			# No Lazy arguments (we can't use super().__init__ here)
			self._lazy_args = None
		self.init_args = tuple(arg for arg in args if not isinstance(arg, Lazy))

	@abstractmethod
	def _lazy_init(self, *args):
		# This method remains abstract
		pass


if __name__ == '__main__':
	class MyLazyEnum(LazyEnum):
		X = 'x'
		Y = 'y'

		def _lazy_init(self, value):
			print(f"Lazy init of {value}")
			self.letter = value
			return value * 2

	print(MyLazyEnum.X)
	print(MyLazyEnum.X.letter)
	print(MyLazyEnum.X.value)
	print(MyLazyEnum.X.letter)
	print(MyLazyEnum.Y.value)
	print(MyLazyEnum.Y.value)
	print(MyLazyEnum.Y.name)


	class MyLazyDirectEnum(LazyDirectEnum):
		X = 'x'
		Y = 'y'

		@classmethod
		def _lazy_init(cls, value):
			print(f"Lazy init of {value}")
			return value * 2

	print(MyLazyDirectEnum)
	print(MyLazyDirectEnum.X)
	print(MyLazyDirectEnum.X)
	print(MyLazyDirectEnum.Y)


	class MyMixedEnum(LazyEagerEnum):
		X = Lazy(1)
		Y = 'y', Lazy(2), 'w', Lazy(3, 4)  # Since mixed=True, only values in Lazy will be passed to _lazy_init
		Z = 'z', 'a'

		def __init__(self, *args):
			super().__init__(*args)
			self.letters = ','.join(self.init_args)

		def _lazy_init(self, *numbers):
			print("Lazy init called")
			self.numbers = list(numbers)
			return sum(numbers)


	print(MyMixedEnum.X)
	print(MyMixedEnum.X.letters)
	print(MyMixedEnum.X.numbers)
	print(MyMixedEnum.X.value)
	print(MyMixedEnum.X.numbers)
	print(MyMixedEnum.Y.letters)
	print(MyMixedEnum.Y.value)
	print(MyMixedEnum.Y.numbers)
	print(MyMixedEnum.Z.letters)
	print(MyMixedEnum.Z.value)
	try:
		MyMixedEnum.Z.numbers
	except AttributeError:
		print("This one correctly raises an error since lazy initialisation wasn't used")
