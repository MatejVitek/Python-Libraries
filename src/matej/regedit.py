"""
Windows registry editor.

This module allows easier access and handling of Windows registry entries than the `winreg`
module from Python's standard library.
"""

from contextlib import suppress
import itertools as it
from pathlib import Path
from typing import *
import winreg as reg


def _parse(path):
	hive, *path = Path(path).parts
	shorthand = {'HKCR': 'HKEY_CLASSES_ROOT', 'HKLM': 'HKEY_LOCAL_MACHINE', 'HKCU': 'HKEY_CURRENT_USER', 'HKU': 'HKEY_USERS'}
	if (hive := hive.upper()) in shorthand:
		hive = shorthand[hive]
	return getattr(reg, hive), Path(*path)


def exists(key: Union[str, Path], value_name: Optional[str] = None) -> bool:
	"""
	Determine whether a key/value exists.

	Parameters
	----------
	key
		The full path to the key.
	value_name
		The value name. If `None`, checks for the key only. If `''`, checks for the default value.

	Returns
	-------
		`True` if value exists in specified key, `False` otherwise.
	"""
	hive, path = _parse(key)
	with suppress(OSError), reg.OpenKey(hive, str(path)) as key:
		if value_name is not None:
			reg.QueryValueEx(key, value_name)
		return True
	return False


def get_value(key: Union[str, Path], value_name: str = '', return_type: bool = False) -> Union[Optional[Union[str, int]], Tuple[Optional[Union[str, int]], Optional[int]]]:
	"""
	Get the specified value from the specified key.

	Parameters
	----------
	key
		The full path to the key.
	value_name
		The value name. If `''`, get the default value.
	return_type
		If `True`, returns the value type as well.

	Returns
	-------
		The value if it exists, `None` otherwise.
		If `return_type` is `True`, instead returns a tuple of the value and its type,
		or `(None, None)` if the value does not exist.
	"""
	hive, path = _parse(key)
	with suppress(OSError), reg.OpenKey(hive, str(path)) as key:
		value, value_type = reg.QueryValueEx(key, value_name)
		return (value, value_type) if return_type else value
	return (None, None) if return_type else None


def set_value(key: Union[str, Path], value_name: str = '', value: Union[str, int] = '', value_type: Union[str, int] = 'REG_SZ', create_keys: Optional[bool] = None):
	"""
	Set the specified value at the specified key.

	Parameters
	----------
	key
		The full path to the key.
	value_name
		The value name. If `''`, sets the default value.
	value
		The value to assign to the specified value name.
	value_type
		The value type to use for the specified value. Defaults to `'REG_SZ'`.
	create_keys
		Whether to create necessary keys if they do not exist.
		By default (or if `None` is passed), only creates the key specified by `key` if it does not exist.
		If `False`, no keys are created and this function fails if the key does not exist.
		If `True`, the specified key and any non-existing parents are created.

	Raises
	------
	OSError
		If the necessary keys did not exist (and were not created by this function as per `create_keys`),
		or if the keys/value could not be created or set for some reason (such as permission errors).
	"""

	hive, path = _parse(key)
	if isinstance(value_type, str):
		value_type = getattr(reg, value_type)
	if create_keys:
		key = hive
		for parent in path.parts:
			with reg.CreateKey(key, parent) as key:
				if parent == path.name:
					reg.SetValueEx(key, value_name, 0, value_type, value)
	elif create_keys is None:
		with reg.CreateKeyEx(hive, str(path)) as key:
			reg.SetValueEx(key, value_name, 0, value_type, value)
	else:
		reg.SetValueEx(key, value_name, 0, value_type, value)


def delete_value(key: Union[str, Path], value_name: str = ''):
	"""
	Delete the specified value.

	Parameters
	----------
	key
		The full path to the key.
	value_name
		The value name. If `''`, deletes the default value.

	Raises
	------
	OSError
		If the specified value was not found or could not be deleted for some reason (such as permission errors).
	"""
	hive, path = _parse(key)
	with reg.OpenKey(hive, str(path), access=reg.KEY_WRITE) as key:
		reg.DeleteValue(key, value_name)


def delete_key(key: Union[str, Path], recursive: bool = False):
	"""
	Delete the specified key (and its values), which must not contain subkeys (unless `recursive=True` is passed).

	Parameters
	----------
	key
		The full path to the key.
	recursive
		If `True`, recursively deletes subkeys as well.
		If `False`, this function fails if the specified key contains subkeys.

	Raises
	------
	OSError
		If the specified key was not found or contained subkeys (with `recursive=False`),
		or could not be deleted for some other reason (such as permission errors).
	"""
	path = Path(key)
	if recursive:
		for subkey in subkeys(path):
			delete_key(Path(path)/subkey, True)
	hive, path = _parse(path)
	reg.DeleteKey(hive, str(path))


def subkeys(key: Union[str, Path]) -> Iterator[str]:
	"""
	Iterate over subkeys of a registry key.

	Parameters
	----------
	key
		The full path to the key.

	Returns
	-------
		An iterator over all the subkey names of the specified key.
	"""
	hive, path = _parse(key)
	with suppress(OSError), reg.OpenKey(hive, str(path)) as key:
		for i in it.count():
			yield reg.EnumKey(key, i)
