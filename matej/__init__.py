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
import os
from pathlib import Path
import sys


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
