from abc import ABC
import argparse
from ast import literal_eval
from pathlib import Path
import textwrap

from matej.collections import ensure_iterable


# Auxiliary stuff
#pylint: disable = redefined-builtin  # Disable this warning since argparse also redefines a bunch of builtins in its methods
QUERY = object()  #TODO: Use this for the default parameter in add_argument to query the user for the argument's value if the argument is not provided. Can also add an optional query parameter that determines the query string (default should probably be dest.title().replace('_', ' '))


class ArgParser(argparse.ArgumentParser):
	"""
	An :class:`argparse.ArgumentParser` subclass with methods for adding common argument types.

	This parser uses :class:`HelpfulFormatter` as its formatter class by default.
	It also provides the `'store_dict'` action, which allows the user to pass key-value pairs as argument values.
	"""

	def __init__(self, *args, **kw):
		""" Initialise the parser. See the documentation of :class:`argparse.ArgumentParser` for more information. """
		if 'formatter_class' not in kw:
			kw['formatter_class'] = HelpfulFormatter
		super().__init__(*args, **kw)
		self.register('action', 'store_dict', StoreDictPairsAction)

	def add_arg(self, arg):
		""" Add an :class:`Arg` instance to this parser. """
		arg.add_to_ap(self)

	def add_str_arg(self, *args, **kw):
		"""
		Auxiliary method for adding a :class:`StrArg` to the parser. See the documentation of :class:`StrArg` for details.

		Examples
		--------
		>>> ap.add_str_arg(default="Hello, world!", dest='message', help="Message to print")
		>>> ap.add_str_arg('-m', '--message', help="Message to print")
		"""
		return self.add_arg(StrArg(*args, **kw))

	def add_path_arg(self, *args, **kw):
		"""
		Auxiliary method for adding a :class:`PathArg` to the parser. See the documentation of :class:`PathArg` for details.

		Examples
		--------
		>>> ap.add_path_arg(default=Path(), dest='file', help="Path to a file")
		>>> ap.add_path_arg('-p', '--path', help="Path to a file")
		"""
		return self.add_arg(PathArg(*args, **kw))

	def add_bool_arg(self, *args, **kw):
		"""
		Auxiliary method for adding a :class:`BoolArg` to the parser. See the documentation of :class:`BoolArg` for details.

		Examples
		--------
		>>> ap.add_bool_arg('-v', '--verbose', default=True, help="Print verbose output")
		"""
		return self.add_arg(BoolArg(*args, **kw))


	def add_choice_arg(self, *args, **kw):
		"""
		Auxiliary method for adding a :class:`ChoiceArg` to the parser. See the documentation of :class:`ChoiceArg` for details.

		Examples
		--------
		>>> ap.add_choice_arg((1, 2, 3), '-c', '--choice', default=1, type=float, help="Choose one of the options")
		>>> ap.add_choice_arg(('t2b', 'b2t'), '-m', '--method', choice_descriptions=("Top-to-bottom", "Bottom-to-top"), help="Method to use")
		"""
		return self.add_arg(ChoiceArg(*args, **kw))

	def add_number_arg(self, *args, **kw):
		"""
		Auxiliary method for adding a :class:`NumberArg` to the parser. See the documentation of :class:`NumberArg` for details.

		Examples
		--------
		>>> ap.add_number_arg('-n', '--number', min=0, max=1, nargs=1, type=float, help="A number between 0 and 1")
		>>> ap.add_number_arg('-l', '--list', min=0, nargs='+', type=int, help="A list of non-negative numbers")
		>>> ap.add_number_arg('-c', '--color', range=(0, 255), nargs=3, metavar=("R", "G", "B"), help="A color in RGB format")
		"""
		return self.add_arg(NumberArg(*args, **kw))


class Arg(ABC):
	"""
	Base class for all arguments.

	Instances of this class's subclasses can be added to an arbitrary :class:`argparse.ArgumentParser` instance
	using the :meth:`add_to_ap` method,	although certain restrictions apply, as specified in the subclasses' docs.
	"""
	def __init__(self, *flags, **kw):
		"""
		Initialise the argument.

		Parameters
		----------
		flags : Collection[str]
			Optional flags for the argument. If no flags are provided, the `dest` keyword argument must be provided.
		**kw
			Keyword arguments to pass to the :meth:`argparse.ArgumentParser.add_argument` method.
		"""
		self.flags = flags
		self.kw = kw

	def add_to_ap(self, parser, **kw):
		""" Add this argument to the given parser. """
		kw = self.kw | kw
		if not self.flags and 'dest' not in kw:
			raise ValueError("You must provide a destination name for flagless arguments")
		return parser.add_argument(*self.flags, **kw)


class StrArg(Arg):
	""" String argument. """
	def __init__(self, *flags, **kw):
		"""
		Initialise the argument.

		By default this argument is optional and accepts a single string as its value.

		Parameters
		----------
		nargs : int or str, default='?'
			Number of arguments to accept. See the documentation of :meth:`argparse.ArgumentParser.add_argument` for details.
		type : type, default=str
			Type of the argument.

		For other parameters, see the documentation of :meth:`Arg.__init__`.
		"""
		kw.setdefault('nargs', '?')
		kw.setdefault('type', str)
		super().__init__(*flags, **kw)


class PathArg(Arg):
	""" Path argument. """
	def __init__(self, *flags, **kw):
		"""
		Initialise the argument.

		By default this argument is optional and accepts a single path as its value.

		Parameters
		----------
		nargs : int or str, default='?'
			Number of arguments to accept. See the documentation of :meth:`argparse.ArgumentParser.add_argument` for details.
		type : type, default=Path
			Type of the argument.

		For other parameters, see the documentation of :meth:`Arg.__init__`.
		"""
		kw.setdefault('nargs', '?')
		kw.setdefault('type', Path)
		super().__init__(*flags, **kw)


class BoolArg(Arg):
	""" Boolean argument. """
	def __init__(self, *flags, default=False, help="", negative_help=None, **kw):
		"""
		Initialise the argument.

		Parameters
		----------
		default : bool, default=False
			Default value for the argument.
		help : str, default=""
			Help string for the long positive form of the argument.
		negative_help : str, default=None
			Help string for the long negative form of the argument. If not provided, the negative form will simply prefix `help` with "Do not".
		dest : str, optional
			Destination in which to save the argument value (see the documentation of :meth:`argparse.ArgumentParser.add_argument` for details).
			If not explicitly provided, it is inferred from the first long flag, or from the first short flag if no long flags are passed.

		For other parameters, see the documentation of :meth:`Arg.__init__`.
		"""
		super().__init__(*flags, **kw)
		self.short_flags = [flag for flag in flags if flag[0] == '-' and flag[1] != '-']
		self.long_flags = [flag for flag in flags if flag[:2] == '--']
		self.dest = kw.get('dest', (self.long_flags[0] if self.long_flags else flags[0]).strip('-').replace('-', '_'))
		self.default = default

		self.short_help = help + " (this toggles the default if no value is passed)" if help else help
		self.yes_help = help
		self.no_help = negative_help if negative_help is not None else "Do not " + help[0].lower() + help[1:] if help else help
		if default:
			self.yes_help += " <default>"
		else:
			self.no_help += " <default>"

	def add_to_ap(self, parser, **kw):
		"""
		Add this argument to the parser.

		This method adds:

			- long flags that store `True` into the destination;
			- long flags with `--no-` prefix that store `False` into the destination;
			- short flags that:
				- store `True` into the destination if `'True'` or `'Yes'` is passed as an argument,
				- store `False` into the destination if `'False'` or `'No'` is passed as an argument,
				- toggle the default value if no argument is passed.
		"""
		kw = self.kw | kw
		group = parser.add_mutually_exclusive_group()
		result = group.add_argument(*self.short_flags, dest=self.dest, nargs='?', default=self.default, const=not self.default, type=self._str_to_bool, help=self.short_help, **kw)
		group.add_argument(*self.long_flags, dest=self.dest, action='store_true', help=self.yes_help, **kw)
		group.add_argument(*map(self._no_f, self.long_flags), dest=self.dest, action='store_false', help=self.no_help, **kw)
		return result

	@staticmethod
	def _no_f(arg):
		return '--no-' + arg.strip('-')

	@staticmethod
	def _str_to_bool(s):
		return s.lower() in {'true', 'yes', 't', 'y', '1'}


#TODO: Make it possible to pass the choice descriptions as values too?
class ChoiceArg(Arg):
	""" Choice argument. """
	def __init__(self, choices, *flags, choice_descriptions=(), type=None, help="", **kw):
		"""
		Initialise the argument.

		Parameters
		----------
		choices : Collection[Union[int, float, str]]
			The possible choices.
		choice_descriptions : Collection[str], optional
			A list of descriptions for the choices. If passed, should have the same length as `choices`.
		type : type, optional
			The type of the choices. If not provided, it is inferred from `choices` (`int` => `float` => `str`).
		help : str, default=""
			Help string for the argument. Extra information about the choices will be added to it automatically.
			If `choice_descriptions` is not passed, this class should be used with a parser that uses the
			:class:`HelpfulFormatter` as its help formatter, such as :class:`ArgParser`. Otherwise, the auto-generated
			help will contain unformatted default value information.

		For other parameters, see the documentation of :meth:`Arg.__init__`.
		"""
		super().__init__(*flags, **kw)
		if type is None:
			try:
				type = int if all(int(x) == x for x in choices) else float
			except ValueError as e:
				if all(isinstance(x, str) for x in choices):
					type = str
				else:
					raise TypeError("Could not infer the type of the choices. Please pass the `type` argument.") from e
		if choice_descriptions:
			longest = max(len(str(choice)) for choice in choices)
			help += "\n"
			for choice, description in zip(choices, choice_descriptions):
				help += f"\t{choice:>{longest}}: {description}"
				if 'default' in kw and choice == kw['default']:
					help += " <default>"
				help += "\n"
		else:
			help += "{default}"
		self.kw['choices'] = choices
		self.kw['type'] = type
		self.kw['help'] = help


class NumberArg(Arg):
	""" Number argument. """
	def __init__(self, *flags, min=None, max=None, range=None, type=None, help="", **kw):
		"""
		Initialise the argument.

		The argument can receive multiple values (in which case it will be stored as a list). This can be explicitly restricted by passing `nargs=1` to this method.

		Parameters
		----------
		action : str or :class:`argparse.Action`, default=ListOrSingleAction
			The action to use for the argument. Should most likely be left as default but can be overridden if necessary.
		nargs : int or str, default='+'
			The number of arguments to parse. See the documentation of :meth:`argparse.ArgumentParser.add_argument` for more information.
		min : Union[int, float], optional
			The minimum value the argument can have.
		max : Union[int, float], optional
			The maximum value the argument can have.
		range : Tuple[Union[int, float], Union[int, float]], optional
			A tuple of the minimum and maximum values the argument can have (alternative to `min` and `max`).
		type : type, optional
			The type of the argument. If not provided, it is inferred from the `min` and `max` values (`int` => `float`).
		help : str, default=""
			Help string for the argument. Extra information about the minimum and maximum values will be added to it automatically.
			This class should be used with a parser that uses the :class:`HelpfulFormatter` as its help formatter, such as :class:`ArgParser`.
			Otherwise, the auto-generated help will contain unformatted range information.
		"""
		kw.setdefault('action', ListOrSingleAction)
		kw.setdefault('nargs', '+')
		super().__init__(*flags, **kw)

		if range is not None:
			min, max = range

		if type is None:
			type = int if min is not None and isinstance(min, int) and (max is None or isinstance(max, int)) or max is not None and isinstance(max, int) and min is None else float

		def _type(x):
			x = type(x)
			if min is not None and x < min:
				raise argparse.ArgumentTypeError(f"{flags[0]} should be least {min}")
			if max is not None and x > max:
				raise argparse.ArgumentTypeError(f"{flags[0]} should be at most {max}")
			return x

		if min is None and max is not None:
			help += f" [{{metavar}} <= {max}]"
		elif min is not None and max is None:
			help += f" [{{metavar}} >= {min}]"
		elif min is not None:
			help += f" [{min} <= {{metavar}} <= {max}]"

		self.kw['type'] = _type
		self.kw['help'] = help


class HelpfulFormatter(argparse.RawTextHelpFormatter):
	""" Custom formatter that allows the use of certain action properties and respects \n in help messages. """
	def _get_help_string(self, action):
		help = super()._get_help_string(action)
		format_dict = {
			'default': f" <default: {action.default}>" if action.default else "",
			'metavar': action.metavar
		}
		if not action.metavar:
			formatter = self._get_default_metavar_for_optional if action.option_strings else self._get_default_metavar_for_positional
			format_dict['metavar'] = formatter(action)
		return help.format(**format_dict)

	def _split_lines(self, text, width):
		text = super()._split_lines(text, width)
		new_text = []

		# loop through all the lines to create the correct wrapping for each line segment.
		for line in text:
			if not line:
				# this would be a new line.
				new_text.append(line)
				continue

			# wrap the line's help segment which preserves new lines but ensures line lengths are honored
			new_text.extend(textwrap.wrap(line, width))

		return new_text


class StoreDictPairsAction(argparse.Action):
	""" Custom action to store key-value pairs in a dictionary. """
	def __call__(self, parser, namespace, values, option_string=None):
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


class ListOrSingleAction(argparse.Action):
	""" Custom action that converts a list of length 1 into a single value for arguments that can receive multiple values. """
	def __call__(self, parser, namespace, values, option_string=None):
		values = ensure_iterable(values, str)
		if len(values) == 1:
			values = values[0]
		setattr(namespace, self.dest, values)


if __name__ == '__main__':
	ap = ArgParser()

	# Path args
	ap.add_path_arg('-p', '--path-arg', default='', help="first path arg")
	ap.add_path_arg(dest='second_path_arg', default='', help="second path arg")
	assert ap.parse_args(['asdf']).second_path_arg == Path('asdf')
	assert ap.parse_args(['-p', 'qwer']).path_arg == Path('qwer')
	_namespace = ap.parse_args(['asdf', '-p', 'qwer'])
	assert _namespace.path_arg == Path('qwer')
	assert _namespace.second_path_arg == Path('asdf')

	# Bool args
	ap.add_bool_arg('-t', '--true-arg', default=True, help="default true bool arg")
	ap.add_bool_arg('-f', '--false-arg', default=False, help="default false bool arg")
	assert ap.parse_args(['-t', 'True']).true_arg is True
	assert ap.parse_args(['-t', 'False']).true_arg is False
	assert ap.parse_args(['-t']).true_arg is False
	assert ap.parse_args(['--true-arg']).true_arg is True
	assert ap.parse_args(['--no-true-arg']).true_arg is False
	assert ap.parse_args(['-f', 'False']).false_arg is False
	assert ap.parse_args(['-f', 'True']).false_arg is True
	assert ap.parse_args(['-f']).false_arg is True
	assert ap.parse_args(['--false-arg']).false_arg is True
	assert ap.parse_args(['--no-false-arg']).false_arg is False
	# _namespace = ap.parse_args(['-tf'])  # This one doesn't work
	# assert _namespace.true_arg is False
	# assert _namespace.false_arg is True

	# Choice args
	ap.add_choice_arg((1, 2, 3), '-c', '--choice-arg', default=1, help="default 1 choice arg")
	ap.add_choice_arg(('b2t', 't2b'), '--method', choice_descriptions=("Bottom-to-top", "Top-to-bottom"), help="no default choice arg")
	ap.add_choice_arg(('df', 'bf'), '--search', default='df', choice_descriptions=("Depth-first", "Breadth-first"), help="default depth-first choice arg")
	assert ap.parse_args([]).choice_arg == 1
	assert ap.parse_args(['-c', '2']).choice_arg == 2
	# ap.parse_args(['-c', '4'])  # should raise error
	assert ap.parse_args(['--method', 't2b']).method == 't2b'
	assert ap.parse_args([]).method is None

	# Number args
	ap.add_number_arg('-m', '--number-arg', range=(0, 100.), nargs='+', help="number arg")
	ap.add_number_arg('-n', '--number-arg2', min=0, default=40, help="default 40 number arg")
	_namespace = ap.parse_args([])
	assert _namespace.number_arg is None
	assert _namespace.number_arg2 == 40
	assert ap.parse_args(['-m', '50']).number_arg == 50.
	assert ap.parse_args(['-n', '610']).number_arg2 == 610
	assert ap.parse_args(['-m', '50.5', '60', '70']).number_arg == [50.5, 60., 70.]
	# ap.parse_args(['-m', '101'])  # should raise error
	# ap.parse_args(['-m', '50', '101'])  # should raise error
	# ap.parse_args(['-n', '-1'])  # should raise error

	# Print help
	ap.parse_args(['-h'])