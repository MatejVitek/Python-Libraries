import argparse
from ast import literal_eval
from contextlib import contextmanager
import os
import sys
import types


@contextmanager
def working_dir(path):
	oldwd = os.getcwd()
	os.chdir(path)
	try:
		yield
	finally:
		os.chdir(oldwd)


class Singleton(type):
	_instances = {}

	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super().__call__(*args, **kwargs)
		return cls._instances[cls]

# class SampleSingleton(metaclass=Singleton):
#     pass


class _Zero(metaclass=Singleton):
	def __add__(self, other):
		return other

	__radd__ = __add__

	def __mul__(self, other):
		return self

	__rmul__ = __mul__

	def __or__(self, other):
		return other

	__ror__ = __or__

	def __and__(self, other):
		return self

	__rand__ = __and__

	def __bool__(self):
		return False

	def __str__(self):
		return "0"

	def __index__(self):
		return 0

ZERO = _Zero()


class _One(metaclass=Singleton):
	def __mul__(self, other):
		return other

	__rmul__ = __mul__

	def __or__(self, other):
		return self

	__ror__ = __or__

	def __and__(self, other):
		return other

	__rand__ = __and__

	def __bool__(self):
		return True

	def __str__(self):
		return "1"

	def __index__(self):
		return 1

ONE = _One()


class StoreDictPairs(argparse.Action):
	def __call__(self, parser, namespace, values, option_string):
		d = getattr(namespace, self.dest)
		if d is None:
			d = {}
		unpacked = []
		for value in values:
			if '=' in value:
				unpacked.extend(value.split('='))
			else:
				unpacked.append(value)
		if len(unpacked) % 2 != 0:
			raise ValueError("Each key should have a corresponding value")
		for key, value in zip(unpacked[0::2], unpacked[1::2]):
			try:
				d[key] = literal_eval(value)
			except ValueError:
				d[key] = value
		setattr(namespace, self.dest, d)  # necessary if new dictionary was created


class Config(types.SimpleNamespace):
	def __add__(self, other):
		if isinstance(other, dict):
			return Config(**{**self.__dict__, **other})
		if isinstance(other, types.SimpleNamespace):
			return Config(**{**self.__dict__, **other.__dict__})
		raise TypeError(f"Addition not supported for types '{type(self)}' and '{type(other)}'.")

	# This is implemented to support sum builtin
	def __radd__(self, other):
		if other == 0:
			return self
		if isinstance(other, dict):
			return Config(**{**other, **self.__dict__})
		if isinstance(other, types.SimpleNamespace):
			return Config(**{**other.__dict__, **self.__dict__})
		raise TypeError(f"Addition not supported for types '{type(self)}' and '{type(other)}'.")

	def __iadd__(self, other):
		if isinstance(other, dict):
			self.__dict__.update(**other)
		elif isinstance(other, types.SimpleNamespace):
			self.__dict__.update(**other.__dict__)
		else:
			raise TypeError(f"Addition not supported for types '{type(self)}' and '{type(other)}'.")
		return self

	def __getitem__(self, key):
		return self.__dict__[key]

	def __setitem__(self, key, value):
		self.__dict__[key] = value

	def __delitem__(self, key):
		del self.__dict__[key]

	def __contains__(self, item):
		return item in self.__dict__
	
	# Support **unpacking
	def keys(self):
		return self.__dict__.keys()

	def copy(self):
		return Config(**self.__dict__)


# Call as make_module_callable(__name__, function_to_call) at the end of the module definition
def make_module_callable(module_name, f):
	class _CallableModule(types.ModuleType):
		def __call__(self, *args, **kw):
			return f(*args, **kw)
	sys.modules[module_name].__class__ = _CallableModule

