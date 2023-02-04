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

from ast import literal_eval
from collections.abc import Mapping
from configparser import ConfigParser
from contextlib import contextmanager
from copy import deepcopy
import itertools as it
import os
from pathlib import Path
import requests
import types

from .string import multi_replace


@contextmanager
def working_dir(path):
	oldwd = os.getcwd()
	os.chdir(path)
	try:
		yield
	finally:
		os.chdir(oldwd)


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


class Config(types.SimpleNamespace):
	def __init__(self, d=None, /, **kw):
		# Initialisation can be done with a single (possibly nested) dict or with **kw
		if d:
			kw = d | kw  # In case of key clashes, values from **kw prevail
		super().__init__(**kw)

		# Nested initialisation
		for key, value in self.items():
			if isinstance(value, Mapping):
				self[key] = type(self)(value)

	# Support union/update dict-like operations with recursive merging
	def __or__(self, other):
		result = deepcopy(self)
		result |= other
		return result

	def __ror__(self, other):
		result = deepcopy(type(self)(other))
		result |= self
		return result

	def __ior__(self, other):
		self.update(other)
		return self

	def update(self, other, **kw):
		# In case of key clashes **kw values prevail over the ones in other
		if kw:
			other = deepcopy(other)
			other |= kw
		try:
			for key in other:
				# Turn any nested dictionaries into Configs
				if isinstance(other[key], Mapping):
					other[key] = type(self)(other[key])
				# Recursive merging
				if key in self and isinstance(self[key], Config) and isinstance(other[key], Config):
					self[key] |= other[key]
				else:
					self[key] = other[key]
		except TypeError as e:
			raise TypeError(str(e).replace('dict', type(self).__name__)) from e

	# Support dict-style attribute getting
	def __getitem__(self, key):
		return self.__dict__[key]

	# Support dict-style (possibly nested) attribute setting
	def __setitem__(self, key, value):
		if isinstance(value, Mapping):
			value = type(self)(value)
		self.__dict__[key] = value

	# Support dict-style attribute deleting
	def __delitem__(self, key):
		del self.__dict__[key]

	# Support nested attribute setting
	def __setattr__(self, key, value):
		if isinstance(value, Mapping):
			return super().__setattr__(key, type(self)(value))
		return super().__setattr__(key, value)

	# Support `in` checks
	def __contains__(self, item):
		return item in self.__dict__

	# Override __repr__ to replace inner Configs with section headers
	def __repr__(self):
		kv_reprs = [
			f"{key}:{repr(value).replace(type(value).__name__, '')}" if isinstance(value, Config)
			else f"{key}={repr(value)}"
			for key, value in self.items()
		]
		return f"{type(self).__name__}{{{', '.join(kv_reprs)}}}"

	# Support **unpacking and dict-like iteration
	def keys(self):
		return self.__dict__.keys()

	def values(self):
		return self.__dict__.values()

	def items(self):
		return self.__dict__.items()

	def __iter__(self):
		return iter(self.__dict__)

	# Support shallow copying directly (like a dict does)
	# For deep copying and pickling use copy.deepcopy and pickle instead
	def copy(self):
		return type(self)(self.__dict__)

	# Support INI writing and reading. In these methods the leaves of the Config are considered
	# to be the keys and values. Non-leaf nodes are the (possibly nested) sections.
	def write_ini(self, ini_file):
		# If path-like object is passed, open it and pass the file object instead
		if isinstance(ini_file, (str, os.PathLike)):
			Path(ini_file).parent.mkdir(parents=True, exist_ok=True)
			with open(ini_file, 'w', encoding='utf-8') as f:
				self.write_ini(f)
		# When the file object is passed, write the Config to it
		else:
			self._write_ini(self, ini_file)

	@classmethod
	def _write_ini(cls, cfg, f, header=''):
		indent = "\t" * (header.count('.') + 1 if header else 0)
		leaves = [(k, v) for k, v in cfg.items() if not isinstance(v, Config)]
		sections = [(k, v) for k, v in cfg.items() if isinstance(v, Config)]

		# Write out the leaves first
		if leaves:
			for key, value in leaves:
				print(f"{indent}{cls.var2str(key)} = {value}", file=f)
			if sections:  # Empty new line to end the section except at the end of the file
				print(file=f)

		# Write sections recursively
		if sections:
			for section_name, section in sections:
				section_name = cls.var2str(section_name)
				if header:
					section_name = f"{header}.{section_name}"
				print(f"{indent}[{section_name}]", file=f)
				cls._write_ini(section, f, section_name)

	@classmethod
	def from_ini(cls, ini_file):
		# If path-like object is passed, open it and pass the file object instead
		if isinstance(ini_file, (str, os.PathLike)):
			with open(ini_file, 'r', encoding='utf-8') as f:
				return cls.from_ini(f)

		# When the file object is passed, read the Config from it
		cfg = cls()
		parser = ConfigParser()
		parser.read_file(it.chain(('[__dummy]',), ini_file))  # Prepend a dummy header in case of sectionless items

		# Read sectionless items
		cls._read_section(cfg, parser['__dummy'])
		del parser['__dummy']

		# Read sections
		for section in parser.sections():
			subsection_split = cls.str2var(section).split('.')
			curr_cfg = cfg
			# Create subsection (and its parents if necessary) in the Config if it doesn't exist
			for section_name in subsection_split:
				if section_name not in curr_cfg:
					curr_cfg[section_name] = cls()
				curr_cfg = curr_cfg[section_name]
			cls._read_section(curr_cfg, parser[section])

		return cfg

	@classmethod
	def _read_section(cls, cfg, section):
		for key, value in section.items():
			try:
				value = literal_eval(value)
			except (ValueError, SyntaxError):
				pass

			# Handle Paths
			if isinstance(value, str):
				path = Path(value)
				# A fairly conservative way of detecting whether the string is meant to be a path
				# It either needs to be an absolute path or it needs to exist and have at least one separator (\ or /)
				if path.is_absolute() or path.exists() and len(path.parts) > 1:
					value = path

			cfg[cls.str2var(key)] = value

	_replace_dict = {' ': '_', '_': '__', '-': '___'}
	# Translate INI section header or key to Config attribute name
	@classmethod
	def str2var(cls, key):
		return multi_replace(key, cls._replace_dict).lower()

	# Translate Config attribute name to INI section header or key
	@classmethod
	def var2str(cls, attr):
		return multi_replace(attr, {v: k for k, v in cls._replace_dict.items()}).title()


# Class adapted from https://github.com/ndrplz/google-drive-downloader/blob/master/google_drive_downloader/google_drive_downloader.py
class GoogleDriveDownloader:
	CHUNK_SIZE = 32768
	DOWNLOAD_URL = 'https://docs.google.com/uc?export=download'

	@staticmethod
	def download_file_from_google_drive(file_id, dest_path):
		dest_path = Path(dest_path)
		dest_path.parent.mkdir(parents=True, exist_ok=True)

		session = requests.Session()

		print('Downloading {} into {}... '.format(file_id, dest_path), end='', flush=True)

		response = session.get(GoogleDriveDownloader.DOWNLOAD_URL, params={'id': file_id}, stream=True)

		token = GoogleDriveDownloader._get_confirm_token(response)
		if token:
			params = {'id': file_id, 'confirm': token}
			response = session.get(GoogleDriveDownloader.DOWNLOAD_URL, params=params, stream=True)

		GoogleDriveDownloader._save_response_content(response, dest_path)
		print('Done.')

	@staticmethod
	def _get_confirm_token(response):
		for key, value in response.cookies.items():
			if key.startswith('download_warning'):
				return value
		return None

	@staticmethod
	def _save_response_content(response, destination):
		with open(destination, 'wb') as f:
			for chunk in response.iter_content(GoogleDriveDownloader.CHUNK_SIZE):
				if chunk:  # filter out keep-alive new chunks
					f.write(chunk)


if __name__ == '__main__':
	c1 = Config({
		'a': 3,
		'b': {
			'c': (4, 5, 6),
			'd': [7, 8, 9],
			'e': {
				'f': 'asdf',
				'g': 10.11
			}
		},
		'h': 12
	})
	c2 = Config({
		'a': 13,
		'b': {
			'c': 14.15,
			'd': [16, 17],
			'e': 18,
			'f': 19,
			'g': 'fdsa'
		}
	})
	c3 = deepcopy(c1)
	c4 = deepcopy(c1)
	c5 = deepcopy(c2)
	c6 = deepcopy(c2)
	c3 |= c2
	c4.update(c2, b=20)
	c5 |= c1
	c6.update(c1, h={'i': 21, 'j': 22})
	print(c1, c2, c1 | c2, c2 | c1, c3, c4, c5, c6, sep="\n")
