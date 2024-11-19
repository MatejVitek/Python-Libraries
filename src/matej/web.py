# Selenium stuff should go in here too

import asyncio as aio
from pathlib import Path
import warnings

try:
	import requests
except ImportError as e:
	raise ImportError("The web module requires the requests library. Please install it using `pip install requests`.") from e
try:
	import aiohttp
except ImportError as e:
	aiohttp = None

from matej.collections import ensure_iterable


def get_html(url, session=None):
	""" Get the HTML content of a webpage. """
	if session is None:
		session = requests.Session()
	response = session.get(url)
	response.raise_for_status()
	return response.text


async def _get_htmls(urls, session=None):
	if session is None:
		session = aiohttp.ClientSession()
	async with session:
		tasks = [aio.to_thread(get_html, url, session) for url in urls]
		return await aio.gather(*tasks)


def get_htmls(urls, *args, session=None, asynchronous=True):
	""" Get the HTML content of multiple webpages. """
	urls = ensure_iterable(urls, True) + args

	if not asynchronous or aiohttp is None:
		if aiohttp is None:
			warnings.warn("The aiohttp library is not installed. Asynchronous requests will not work.")
		return [get_html(url, session) for url in urls]

	return aio.run(_get_htmls(urls, session))


# Class adapted from https://github.com/ndrplz/google-drive-downloader/blob/master/google_drive_downloader/google_drive_downloader.py
class GoogleDriveHandler:
	""" Google Drive interface. """

	CHUNK_SIZE = 32768
	DOWNLOAD_URL = 'https://docs.google.com/uc?export=download'

	@classmethod
	def download_file(cls, file_id, dest_path):
		""" Download a file from Google Drive. """
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


if __name__ == '__main__':
	from time import time
	URLS = [f'https://www.scrapingcourse.com/ecommerce/page/{i}' for i in range(2, 50)]

	start = time()
