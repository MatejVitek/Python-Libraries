# Selenium stuff should go in here too

import asyncio as aio
import warnings

try:
	import requests
except ImportError as e:
	raise ImportError("The web module requires the requests library. Please install it using `pip install requests`.") from e
try:
	import aiohttp
except ImportError:
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
