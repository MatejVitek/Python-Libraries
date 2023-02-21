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


# Class adapted from https://github.com/ndrplz/google-drive-downloader/blob/master/google_drive_downloader/google_drive_downloader.py
class GoogleDriveHandler:
	""" Google Drive interface. """

	CHUNK_SIZE = 32768
	DOWNLOAD_URL = 'https://docs.google.com/uc?export=download'

	@classmethod
	def download_file(cls, file_id, dest_path):
		""" Download a file from Google Drive. """
		try:
			import requests
		except ImportError as e:
			raise ImportError(
				"This function requires the requests library."
				"Please install it using `pip install requests`."
			) from e

		dest_path = Path(dest_path)
		dest_path.parent.mkdir(parents=True, exist_ok=True)

		session = requests.Session()

		print(f"Downloading {file_id} into {dest_path} ... ", end="", flush=True)

		response = session.get(cls.DOWNLOAD_URL, params={'id': file_id}, stream=True)

		token = cls._get_confirm_token(response)
		if token:
			params = {'id': file_id, 'confirm': token}
			response = session.get(cls.DOWNLOAD_URL, params=params, stream=True)

		cls._save_response_content(response, dest_path)
		print('Done.')

	@staticmethod
	def _get_confirm_token(response):
		for key, value in response.cookies.items():
			if key.startswith('download_warning'):
				return value
		return None

	@classmethod
	def _save_response_content(cls, response, destination):
		with open(destination, 'wb') as f:
			for chunk in response.iter_content(cls.CHUNK_SIZE):
				if chunk:  # filter out keep-alive new chunks
					f.write(chunk)
