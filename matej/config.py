from ast import literal_eval
from collections.abc import MutableMapping, Mapping
from configparser import ConfigParser
from copy import deepcopy
import itertools as it
import os
from pathlib import Path
from types import SimpleNamespace

from matej.collections import flatten, lmap, is_iterable
from matej.string import multi_replace


class Config(SimpleNamespace, MutableMapping):
	"""
	Config class that supports nested initialisation and recursive merging.

	Also supports saving to and reading from the following file formats:
	- INI,
	- YAML,
	- JSON.
	"""
	#TODO: Support JSON. Also CSV, XML maybe?

	def __init__(self, d=None, /, **kw):
		"""
		Initialise the Config object.

		Initialisation can be done with a single (possibly nested) dict or with `**kw` arguments.
		"""

		if d:
			kw = d | kw  # In case of key clashes, values from **kw prevail
		super().__init__(**kw)

		# Recursively convert all nested dicts to Configs
		for key, value in self.items():
			self[key] = self._recursive_init(value)

	@classmethod
	def _recursive_init(cls, value):
		if isinstance(value, Mapping) and not isinstance(value, Config):
			return cls(value)
		if is_iterable(value, (str, bytes, Config)):
			return type(value)(cls._recursive_init(item) for item in value)
		return value

	# Support shallow copying directly (like a dict does)
	# For deep copying and pickling use copy.deepcopy and pickle instead
	def copy(self):
		""" Create a shallow copy of the `Config`. """
		return type(self)(self.__dict__)

	#################################################
	# Recursive conversion to dict and clearer repr #
	#################################################
	def to_dict(self):
		""" Recursive conversion to a dict. """
		return {k: self._recursive_to_dict(v) for k, v in self.items()}

	@classmethod
	def _recursive_to_dict(cls, node):
		if isinstance(node, Config):
			return node.to_dict()
		if is_iterable(node, True):
			return type(node)(cls._recursive_to_dict(item) for item in node)
		return node

	def __repr__(self):
		return f"{type(self).__name__}{self._repr(self)}"

	@classmethod
	def _repr(cls, node):
		if isinstance(node, Config):
			return "{" + ", ".join(f"{k}{cls._sep(v)}{cls._repr(v)}" for k, v in node.items()) + "}"
		if is_iterable(node, True):
			subrepr = repr(node)
			return subrepr[0] + ", ".join(cls._repr(v) for v in node) + subrepr[-1]
		return repr(node)

	@classmethod
	def _sep(cls, node):
		""" Return "=" for leaves and ": " for inner nodes. """
		if isinstance(node, Config) or is_iterable(node, True) and any(cls._sep(v) == ": " for v in node):
			return ": "
		return "="

	####################################################################
	# Support union/update dict-like operations with recursive merging #
	####################################################################
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

	def update(self, other=None, /, **kw):
		""" Update the Config object with another dict-like object or with `**kw` arguments. """
		# In case of key clashes **kw values prevail over the ones in other
		if other is None:
			return self.update(kw)
		other = deepcopy(other)
		if kw:
			other |= kw
		try:
			for key, value in other.items():
				# Turn any nested dictionaries into Configs
				other[key] = self._recursive_init(value)
				# Config recursive merging
				if key in self:
					if isinstance(self[key], Config) and isinstance(value, Config):
						self[key] |= value
						continue
					# Only merge non-leaf lists
					if is_iterable(self[key], True) and is_iterable(value, True) and any(isinstance(v, Config) for v in flatten(self[key] + value, flatten_dicts=False)):
						#TODO: Right now this just shallowly merges the lists. Instead, could do something like
						# value = set(value)
						# for i, self_item in enumerate(self[key]):
						# 	for j, other_item in enumerate(value):
						# 		if isinstance(self_item, Config) and isinstance(other_item, Config) and match(self_item, other_item):
						# 			self[key][i] |= other_item
						# 			value.remove(other_item)
						# 			break
						# Just have to decide how to match the Configs. Can probably ignore (read: just merge) nested lists, the merging logic is very unclear in that case anyway.
						self[key] += value
						continue
				self[key] = value
		except TypeError as e:
			raise TypeError(str(e).replace('dict', type(self).__name__)) from e

	###########################################################################
	# Support dict-style and dot-style attribute getting and (nested) setting #
	###########################################################################
	def __getitem__(self, key):
		return self.__dict__[key]

	def __setitem__(self, key, value):
		if isinstance(value, Mapping):
			value = type(self)(value)
		self.__dict__[key] = value

	def __delitem__(self, key):
		del self.__dict__[key]

	def __setattr__(self, key, value):
		if isinstance(value, Mapping):
			return super().__setattr__(key, type(self)(value))
		return super().__setattr__(key, value)

	def __contains__(self, item):
		return item in self.__dict__

	###############################################
	# Support **unpacking and dict-like iteration #
	###############################################
	def keys(self):
		""" Iterate over the keys. """
		return self.__dict__.keys()

	def values(self):
		""" Iterate over the values. """
		return self.__dict__.values()

	def items(self):
		""" Iterate over the (key, value) pairs. """
		return self.__dict__.items()

	def __iter__(self):
		return iter(self.__dict__)

	def __len__(self):
		return len(self.__dict__)

	###################################
	# Support INI writing and reading #
	###################################
	def save_ini(self, ini_file):
		"""
		Write the `Config` to an INI file.

		The leaves of the `Config` are considered to be the keys and values.
		Non-leaf nodes are the (possibly nested) sections.

		Note that INI files have limited support for certain more complex cases available in `Config`,
		such as nested `Config`s inside list elements. For these cases, YAML or JSON is recommended.
		"""

		# If path-like object is passed, handle opening it here
		if isinstance(ini_file, (str, os.PathLike)):
			Path(ini_file).parent.mkdir(parents=True, exist_ok=True)
			with open(ini_file, 'w', encoding='utf-8') as f:
				return self._write_ini(self, f)
		self._write_ini(self, ini_file)

	@classmethod
	def _write_ini(cls, cfg, f, header=''):
		indent = "\t" * (header.count('.') + 1 if header else 0)
		leaves = [(k, v) for k, v in cfg.items() if not isinstance(v, Config)]
		sections = [(k, v) for k, v in cfg.items() if isinstance(v, Config)]

		# Write out the leaves first
		if leaves:
			for key, value in leaves:
				print(f"{indent}{cls.ini_var2str(key)} = {value}", file=f)
			if sections:  # Empty new line to end the section except at the end of the file
				print(file=f)

		# Write sections recursively
		if sections:
			for section_name, section in sections:
				section_name = cls.ini_var2str(section_name)
				if header:
					section_name = f"{header}.{section_name}"
				print(f"{indent}[{section_name}]", file=f)
				cls._write_ini(section, f, section_name)

	@classmethod
	def from_ini(cls, ini_file):
		"""
		Read the `Config` from an INI file.

		The leaves of the `Config` are considered to be the keys and values.
		Non-leaf nodes are the (possibly nested) sections.
		"""

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
			subsection_split = cls.ini_str2var(section).split('.')
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

			cfg[cls.ini_str2var(key)] = value

	_replace_dict = {' ': '_', '_': '__', '-': '___'}
	@classmethod
	def ini_str2var(cls, key):
		""" Translate INI section header or key to `Config` attribute name. """
		return multi_replace(key, cls._replace_dict).lower()

	@classmethod
	def ini_var2str(cls, attr):
		""" Translate `Config` attribute name to INI section header or key. """
		return multi_replace(attr, {v: k for k, v in cls._replace_dict.items()}).title()

	####################################
	# Support YAML writing and reading #
	####################################
	def save_yaml(self, yaml_file, **kw):
		""" Write the `Config` to a YAML file. """
		# If path-like object is passed, open it and pass the file object instead
		if isinstance(yaml_file, (str, os.PathLike)):
			Path(yaml_file).parent.mkdir(parents=True, exist_ok=True)
			with open(yaml_file, 'w', encoding='utf-8') as f:
				return self.save_yaml(f, **kw)
		yaml = self._create_yaml_handler(**kw)
		yaml.dump(self.to_dict(), yaml_file)

	@classmethod
	def save_yamls(cls, configs, yaml_file, **kw):
		""" Write multiple `Config`s to a YAML file. """
		# If path-like object is passed, open it and pass the file object instead
		if isinstance(yaml_file, (str, os.PathLike)):
			Path(yaml_file).parent.mkdir(parents=True, exist_ok=True)
			with open(yaml_file, 'w', encoding='utf-8') as f:
				return cls.save_yamls(configs, f)
		yaml = cls._create_yaml_handler(**kw)
		yaml.dump_all([config.to_dict() for config in configs], yaml_file)

	@classmethod
	def from_yaml(cls, yaml_file, **kw):
		""" Read the `Config` from a YAML file.

		Note: If the YAML file contains multiple documents, each document will be read as a separate `Config`.
		In this case, a list of `Config`s will be returned.
		"""

		# If path-like object is passed, open it and pass the file object instead
		if isinstance(yaml_file, (str, os.PathLike)):
			with open(yaml_file, 'r', encoding='utf-8') as f:
				return cls.from_yaml(f, **kw)
		yaml = cls._create_yaml_handler(**kw)
		configs = lmap(cls, yaml.load_all(yaml_file))
		return configs if len(configs) > 1 else configs[0]

	@staticmethod
	def _create_yaml_handler(**kw):
		try:
			from ruamel.yaml import YAML
		except ImportError as e:
			raise ImportError(
				"YAML file handling requires the ruamel.yaml library."
				"Please install it with `pip install ruamel.yaml`."
			) from e

		return YAML(**kw)


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
	c6.update(h={'i': 21, 'j': 22})
	print(c1, c2, c1 | c2, c2 | c1, c3, c4, c5, c6, sep="\n")
	c7 = Config.from_yaml('F:/Downloads/asdf.yaml')
	c8 = c7[0] | c7[1]
	print(c8)
