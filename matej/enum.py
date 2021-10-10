from enum import Enum
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
