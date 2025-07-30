from pathlib import Path

try:
	import requests
except ImportError as e:
	raise ImportError("The web module requires the requests library. Please install it using `pip install requests`.") from e


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
