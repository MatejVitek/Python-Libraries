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


def _parse(path, default=True):
	if default:
		hive, *path = Path(path).parts
		name = ''
	else:
		hive, *path, name = Path(path).parts
	shorthand = {'HKCR': 'HKEY_CLASSES_ROOT', 'HKLM': 'HKEY_LOCAL_MACHINE', 'HKCU': 'HKEY_CURRENT_USER', 'HKU': 'HKEY_USERS'}
	if (hive := hive.upper()) in shorthand:
		hive = shorthand[hive]
	hive = getattr(reg, hive)
	path = Path(*path)
	return hive, path, name


def has_value(path: Union[str, Path], default: bool = False) -> bool:
	"""
	Determine whether a key exists and contains the specified value.

	Args:
		path: The full path to the value.
		default: If `True`, look for the default value of the key specified by `path`.

	Returns:
		`True` if value exists in specified key, `False` otherwise.
	"""

	return get_value(path, default) is not None


def get_value(path: Union[str, Path], default: bool = False, return_type: bool = False) -> Union[Optional[Union[str, int]], Tuple[Optional[Union[str, int]], Optional[int]]]:
	"""
	Get the value from the specified registry path.

	Args:
		path: The full path to the value.
		default: If `True`, get the default value of the key specified by `path`.
		return_type: If `True`, will return the value type as well.

	Returns:
		The value if it exists, `None` otherwise.
		If `return_type` is `True`, will instead return a tuple of the value and its type,
		or `(None, None)` if the value does not exist.
	"""

	hive, path, name = _parse(path, default)
	with suppress(OSError), reg.OpenKey(hive, str(path)) as key:
		value, value_type = reg.QueryValueEx(key, name)
		return (value, value_type) if return_type else value
	return (None, None) if return_type else None


def set_value(path: Union[str, Path], value: Union[str, int] = '', value_type: Union[str, int] = 'REG_SZ', default: bool = False, create_parent_keys: Optional[bool] = None):
	"""
	Sets the value at the specified registry path.

	Args:
		path: The full path to the value.
		value: The value to assign to the specified value path.
		default: If `True`, set the default value of the key specified by `path`.
		value_type: The value type to use for the specified value. Defaults to `'REG_SZ'`.
		create_parent_keys: Whether to create parent keys if they do not exist.
			By default (or if `None` is passed), will only create the immediate parent.
			If `False`, no parents will be created.
			If `True`, all necessary parents will be created.

	Raises:
		OSError: If the necessary parents did not exist and `create_parent_keys` was not `True`,
			or if the keys/value could not be created or set for some reason (such as permission errors).
	"""

	hive, path, name = _parse(path, default)
	if isinstance(value_type, str):
		value_type = getattr(reg, value_type)
	if create_parent_keys:
		key = hive
		for parent in path.parts:
			with reg.CreateKey(key, parent) as key:
				if parent == path.name:
					reg.SetValueEx(key, name, 0, value_type, value)
	elif create_parent_keys is None:
		with reg.CreateKeyEx(hive, str(path)) as key:
			reg.SetValueEx(key, name, 0, value_type, value)
	else:
		reg.SetValueEx(key, name, 0, value_type, value)


def delete_value(path: Union[str, Path], default: bool = False):
	"""
	Deletes the value at the specified registry path.

	Args:
		path: The full path to the value.
		default: If `True`, delete the default value of the key specified by `path`.

	Raises:
		OSError: If the specified value was not found or could not be deleted for some reason (such as permission errors).
	"""

	hive, path, name = _parse(path, default)
	with reg.OpenKey(hive, str(path), access=reg.KEY_WRITE) as key:
		reg.DeleteValue(key, name)
		return True


def has_key(path: Union[str, Path]) -> bool:
	"""
	Determines whether a key exists.

	Args:
		path: The full path to the key.

	Returns:
		`True` if the key exists, `False` otherwise.
	"""

	hive, path, _ = _parse(path)
	with suppress(OSError), reg.OpenKey(hive, str(path)):
		return True
	return False


def delete_key(path: Union[str, Path], recursive: bool = False):
	"""
	Deletes the key (and its values) at the specified registry path.

	Args:
		path: The full path to the value.
		recursive: If `True`, will delete subkeys as well.
			If `False`, will fail if the specified key contains subkeys.

	Raises:
		OSError: If the specified key was not found or could not be deleted for some reason (such as permission errors).
	"""

	path = Path(path)
	if recursive:
		for subkey in subkeys(path):
			delete_key(Path(path)/subkey, True)
	hive, path, _ = _parse(path)
	reg.DeleteKey(hive, str(path))


def subkeys(path: Union[str, Path, int]) -> Iterator[str]:
	"""
	Iterates over subkeys of a registry key.

	Args:
		path: The full path to the key.

	Returns:
		An iterator over all the subkey names of the specified key.
	"""

	hive, path, _ = _parse(path)
	with suppress(OSError), reg.OpenKey(hive, str(path)) as key:
		for i in it.count():
			yield reg.EnumKey(key, i)
