# When debugging use the Python: Current Module configuration
#
# Hack so I can import modules with the same name as mine (untested, because apparently now it works without this?)
# import importlib
# from pathlib import Path
# import sys
# _old_path = sys.path
# _parent_dir = Path(__file__).parent.absolute()
# for path in sys.path:
# 	if str(_parent_dir) in path:
# 		sys.path.remove(path)
# for file in _parent_dir.rglob('*'):
# 	if file.is_dir() and (file/'__init__.py').is_file() or file.suffix == '.py' and file.stem != '__init__':
# 		try:
# 			importlib.import_module(file.stem)
# 		except ModuleNotFoundError:
# 			pass
# sys.path = _old_path


from contextlib import contextmanager
import importlib.metadata
import os
import sys


try:
	__version__ = importlib.metadata.version(__package__ or __name__)
except importlib.metadata.PackageNotFoundError:
	from pathlib import Path
	import re
	with (Path(__file__).resolve().parent.parent.parent/'pyproject.toml').open('r', encoding='utf-8') as f:
		__version__ = re.search(r'version\s*=\s*[\'"]?([^\'"]*)[\'"]?', f.read()).group(1)


@contextmanager
def working_dir(path):
	""" Temporarily change working directory. """
	oldwd = os.getcwd()
	os.chdir(path)
	try:
		yield
	finally:
		os.chdir(oldwd)


@contextmanager
def pythonpath(*paths):
	""" Temporarily add paths to sys.path. """
	paths = list(map(str, paths))  # In case PathLike objects are passed
	oldpath = sys.path
	sys.path = paths + [p for p in sys.path if p not in paths]
	try:
		yield
	finally:
		sys.path = oldpath


@contextmanager
def verbosity(verbosity=True):
	"""
	Temporarily override the built-in print function to respect the `verbosity` setting.

	Use this context manager to control whether print statements are executed or not.

	Parameters
	----------
	verbosity : bool, default=True
		If `True`, `print` statements will be executed. If `False`, they will be suppressed.
	"""
	old_print = print
	print = lambda *args, **kw: old_print(*args, **kw) if verbosity else None
	try:
		yield
	finally:
		print = old_print


class Singleton(type):
	"""
	Singleton metaclass.

	Usage:
	>>> class SampleSingleton(metaclass=Singleton):
	... 	pass
	"""

	_instances = {}

	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super().__call__(*args, **kwargs)
		return cls._instances[cls]


#TODO: Is this possible to do in a robust way?
class MultiSubclassMeta(type):
	"""
	A metaclass that lets parent classes with different __new__/__init__ arguments play nicely.

	# The below stuff is copied from my old PyQt generic Widget class, which had this similar functionality. It's just for reference.
	When creating a new instance of this class a simple call to this class' constructor will try to match the arguments of the call
	to each of the 5 methods above (for `_init`, `_connect_signals` and `_init_ui_values` only if they are defined in the subclass).
	Below is a detailed description of how this argument matching works, but for the most part you shouldn't have to worry about this
	if you define your methods and call this class' constructor in a reasonable way. The best way to achieve intuitive, predictable,
	and reliable behaviour is to pass all arguments into the constructor as keywords. Passing them as keywords also allows you to pass
	the same argument to multiple initialisation methods, as long as its name matches in all of them.

	The argument matching procedure uses the following order of methods: `_init`, `_init_ui`, `_connect_signals`, `_init_ui_values`, `super().__init__`.
	Note that this order is different to the order in which the methods are actually called, which is described in the bullet list above
	(the difference is that for argument matching the superclass' `__init__` method is considered last, while in the calling order it appears first).
	The argument matching procedure works as follows:

	- Determine *how many* positional `*args` go to each method in 5 stages:
	  - First, enough `*args` must be reserved for positional-only parameters of all methods in order. If there aren't enough `*args` for this, raise Error.
	  - Second, reserve enough `*args` for positional-or-keyword arguments that don't appear in the passed `**kwargs` and don't have default values.
		Again, if there aren't enough remaining `*args` for this, raise an Error.
		If any of them are after the first positional-or-keyword argument that *does* appear in the passed `**kwargs`, also raise an Error.
	  - Third, if there are still `*args` left over, reserve enough for positional-or-keyword arguments with default values
		up to the first one that appears in the passed `**kwargs`.
	  - Finally, if `*args` are still not exhausted, as many as remain will be passed to the first method with `*args` in its signature.
		Note that only methods whose positional-or-keyword arguments don't appear in the passed `**kwargs` will be considered.
		If no such method is found, raise an Error.
	- Note that these stages are only used to determine the *number* of arguments passed, not *which* arguments are passed.
	  Since we now know how many positional arguments should be passed to each method, simply iterate over the methods in order
	  and pass that many `*args` to it, removing the passed arguments from `*args` in the process.
	- Finally, determine the keyword arguments that should be passed to each method. If the method has `**kwargs` in its signature, simply pass
	  all passed keyword arguments to it and let the method sort them out. Otherwise all the passed `**kwargs` that appear in the method's
	  signature will be passed to the method. This way multiple methods can be passed the same keyword argument.

	Usage:
	>>> class A:
	... 	def __init__(self, a):
	... 		self.a = a
	>>> class B:
	... 	def __init__(self, b):
	... 		self.b = b
	>>> class C(A, B, metaclass=MultiSubclassMeta):
	... 	pass
	>>> c = C(1, 2)
	>>> c.a
	1
	>>> c.b
	2
	"""