import argparse
from ast import literal_eval
from collections.abc import Mapping
from configparser import ConfigParser
from contextlib import contextmanager
import itertools as it
import os
from pathlib import Path
import requests
import sys
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
	_instances = {}

	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super().__call__(*args, **kwargs)
		return cls._instances[cls]

# class SampleSingleton(metaclass=Singleton):
# 	pass


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
	def __init__(self, d=None, /, **kw):
		# Initialisation can be done with a single (possibly nested) dict or with **kw
		if d:
			kw = d | kw  # In case of key clashes, values from **kw prevail
		super().__init__(**kw)

		# Nested initialisation
		for key, value in self.items():
			if isinstance(value, Mapping):
				self[key] = type(self)(value)

	# Support union/update dict-like operations
	def __or__(self, other):
		try:
			return type(self)(self.__dict__ | other)
		except TypeError as e:
			raise TypeError(str(e).replace('dict', type(self).__name__)) from e

	def __ror__(self, other):
		try:
			return type(self)(other | self.__dict__)
		except TypeError as e:
			raise TypeError(str(e).replace('dict', type(self).__name__)) from e

	def __ior__(self, other):
		self.update(other)
		return self

	def update(self, other, **kw):
		try:
			other |= kw
			for key, value in other.items():
				if isinstance(value, Mapping):
					other[key] = type(self)(value)
			self.__dict__ |= other
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

	# Support **unpacking and dict-like iteration
	def keys(self):
		return self.__dict__.keys()

	def values(self):
		return self.__dict__.values()

	def items(self):
		return self.__dict__.items()

	# Support copying
	def copy(self):
		return type(self)(self.__dict__)

	# Support INI writing and reading. In these methods the leaves of the Config are considered
	# to be the keys and values. Non-leaf nodes are the (possibly nested) sections.
	def write_ini(self, ini_file):
		# If path-like object is passed, open it and pass the file object instead
		if isinstance(ini_file, (str, os.PathLike)):
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
				print(f"{indent}{cls.variable_to_name(key)} = {value}", file=f)
			if sections:  # Empty new line to end the section except at the end of the file
				print(file=f)

		# Write sections recursively
		if sections:
			for section_name, section in sections:
				section_name = cls.variable_to_name(section_name)
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
			subsection_split = cls.name_to_variable(section).split('.')
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
				cfg[cls.name_to_variable(key)] = literal_eval(value)
			except (ValueError, SyntaxError):
				cfg[cls.name_to_variable(key)] = value

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


# Call as make_module_callable(__name__, function_to_call) at the end of the module definition
def make_module_callable(module_name, f):
	class _CallableModule(types.ModuleType):
		def __call__(self, *args, **kw):
			return f(*args, **kw)
	sys.modules[module_name].__class__ = _CallableModule
