import argparse
from ast import literal_eval
from contextlib import contextmanager
import os
from pathlib import Path
import requests
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
	def __or__(self, other):
		try:
			return type(self)(**(self.__dict__ | other))
		except TypeError as e:
			raise TypeError(str(e).replace('dict', type(self).__name__)) from e

	def __ror__(self, other):
		try:
			return type(self)(**(other | self.__dict__))
		except TypeError as e:
			raise TypeError(str(e).replace('dict', type(self).__name__)) from e

	def __ior__(self, other):
		self.__dict__.update(**other)
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
		return type(self)(**self.__dict__)


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
