from pathlib import Path
import shutil

from matej import verbosity


def extract(archive, to_dir=None, recursive=True, delete=False, verbose=True):
	"""
	Extract an archive to a directory.

	Parameters
	----------
	archive : Path
		The path to the archive to extract.
	to_dir : Path, optional
		The directory to extract the archive to. By default, the directory will be determined automatically.
		If the archive contains a single top-level directory or file, `to_dir` will be set to the parent directory of the archive.
		If the archive contains multiple files or directories, `to_dir` will be set to the directory with the same name as the archive (without the extension).
	recursive: bool, default=True
		Only relevant if the archive contains a single top-level file. If `True`, the file will also be extracted, also recursively.
	delete: bool, default=False
		Whether to delete the archive after extraction.
	verbose : bool, default=True
		If True, print messages about the extraction process.
	"""
	if not (archive := Path(archive)).is_file():
		raise FileNotFoundError(f"Archive {archive} does not exist or is not a file.")
	move_if_single = not to_dir
	to_dir = Path(to_dir) if to_dir else archive.resolve().parent/archive.stem

	with verbosity(verbose):
		print(f"Extracting archive {archive} to {to_dir}...")
		try:
			shutil.unpack_archive(archive, to_dir)
		except shutil.ReadError:
			print("Simple extraction failed, trying dedicated libraries...")
			if not _builtin_extract(archive, to_dir):
				raise RuntimeError(f"Failed to extract archive {archive}. No suitable extraction method found.")
		#TODO: Properly handle recursion and moving single
		print(f"Archive {archive} extracted to {to_dir}.")

#TODO: Test this method with different archives
def _builtin_extract(archive, to_dir):
	# Built-in libraries
	import zipfile
	if zipfile.is_zipfile(archive):
		with zipfile.ZipFile(archive, 'r') as f:
			f.extractall(to_dir)
		print("Extracted as ZIP archive")
		return True
	import tarfile
	if tarfile.is_tarfile(archive):
		with tarfile.open(archive, 'r:*') as f:
			f.extractall(to_dir)
		print("Extracted as TAR archive")
		return True
	import lzma
	try:
		with lzma.open(archive, 'rb') as f:
			with open(to_dir, 'wb') as out_f:
				shutil.copyfileobj(f, out_f)
		print("Extracted as LZMA archive")
		return True
	except lzma.LZMAError:
		pass
	import bz2
	try:
		with bz2.open(archive, 'rb') as f:
			with open(to_dir, 'wb') as out_f:
				shutil.copyfileobj(f, out_f)
		print("Extracted as BZ2 archive")
		return True
	except bz2.BZ2File:
		pass
	import gzip
	try:
		with gzip.open(archive, 'rb') as f:
			with open(to_dir, 'wb') as out_f:
				shutil.copyfileobj(f, out_f)
		print("Extracted as GZ archive")
		return True
	except gzip.BadGzipFile:
		pass

	# Third-party libraries
	if archive.suffix.lower() == '.rar' or archive.read_bytes().startswith(b'\x52\x61\x72\x21\x1a\x07\x00'):
		try:
			import rarfile
			try:
				with rarfile.RarFile(archive, 'r') as f:
					f.extractall(to_dir)
				print("Extracted as RAR archive")
				return True
			except rarfile.BadRarFile:
				pass
		except ImportError:
			print("Tried to extract RAR archive, but the rarfile module was not found. You can install it via pip or other package managers.")
	elif archive.suffix.lower().startswith('.7z') or archive.read_bytes().startswith(b'\x37\x7a\xbc\xaf\x27\x1c'):
		try:
			import py7zr
			try:
				py7zr.unpack_7zarchive(archive, to_dir)
				print("Extracted as 7z archive")
				return True
			except py7zr.Bad7zFile:
				pass
		except ImportError as e:
			print("Tried to extract RAR archive, but the rarfile module was not found. You can install it via pip or other package managers.")

	return False