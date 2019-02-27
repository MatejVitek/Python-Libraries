from types import SimpleNamespace


class Config(SimpleNamespace):
	def __add__(self, other):
		if isinstance(other, dict):
			return Config(**{**self.__dict__, **other})
		if isinstance(other, SimpleNamespace):
			return Config(**{**self.__dict__, **other.__dict__})
		raise TypeError(f"Addition not supported for types '{type(self)}' and '{type(other)}'.")

	# This is implemented to support sum builtin
	def __radd__(self, other):
		if other == 0:
			return self
		if isinstance(other, dict):
			return Config(**{**other, **self.__dict__})
		if isinstance(other, SimpleNamespace):
			return Config(**{**other.__dict__, **self.__dict__})
		raise TypeError(f"Addition not supported for types '{type(self)}' and '{type(other)}'.")

	def __iadd__(self, other):
		if isinstance(other, dict):
			self.__dict__.update(**other)
		elif isinstance(other, SimpleNamespace):
			self.__dict__.update(**other.__dict__)
		else:
			raise TypeError(f"Addition not supported for types '{type(self)}' and '{type(other)}'.")

	def __getitem__(self, key):
		return self.__dict__[key]

	def __setitem__(self, key, value):
		self.__dict__[key] = value

	def __delitem__(self, key):
		del self.__dict__[key]

	def __contains__(self, item):
		return item in self.__dict__
