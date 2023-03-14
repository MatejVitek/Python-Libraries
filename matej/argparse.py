import argparse
from ast import literal_eval
from pathlib import Path
import textwrap

from matej.collections import ensure_iterable


# Auxiliary stuff
#pylint: disable = redefined-builtin  # Disable this warning since argparse also redefines a bunch of builtins in its methods
QUERY = object()  #TODO: Use this for the default parameter in add_argument to query the user for the argument's value if the argument is not provided. Can also add an optional query parameter that determines the query string (default should probably be dest.title().replace('_', ' '))


class ArgParser(argparse.ArgumentParser):
	""" An :class:`argparse.ArgumentParser` subclass with methods for adding common argument types. """

	def __init__(self, *args, **kw):
		"""
		Initialise the parser.

		By default this parser uses :class:`HelpfulFormatter` as its formatter class.
		"""

		if 'formatter_class' not in kw:
			kw['formatter_class'] = HelpfulFormatter
		super().__init__(*args, **kw)
		self.register('action', 'store_dict', StoreDictPairsAction)

	def add_path_arg(self, *flags, **kw):
		"""
		Add a path argument to the parser.

		Examples
		--------
		>>> ap.add_path_arg(default=Path(), dest='file', help="Path to a file")
		>>> ap.add_path_arg('-p', '--path', help="Path to a file")
		"""

		if not flags and 'dest' not in kw:
			raise ValueError("You must provide a destination name for flagless arguments")
		return self.add_argument(*flags, type=Path, nargs='?', **kw)

	def add_bool_arg(self, *flags, default=False, help="", negative_help=None, **kw):
		"""
		Add a boolean argument to the parser.

		This method adds:

			- long flags that store `True` into the destination
			- long flags with `--no-` prefix that store `False` into the destination
			- short flags that:
				- store `True` into the destination if `'True'` or `'Yes'` is passed as an argument;
				- store `False` into the destination if `'False'` or `'No'` is passed as an argument;
				- toggle the default value if no argument is passed.

		If `dest` is not explicitly provided, it is inferred from the first long flag, or from the first short flag if no long flags are passed.

		Examples
		--------
		>>> ap.add_bool_arg('-v', '--verbose', default=True, help="Print verbose output")
		"""

		short_flags = [flag for flag in flags if flag[0] == '-' and flag[1] != '-']
		long_flags = [flag for flag in flags if flag[:2] == '--']
		dest = kw.get('dest', (long_flags[0] if long_flags else flags[0]).strip('-').replace('-', '_'))

		no_f = lambda arg: '--no-' + arg.strip('-')
		str_to_bool = lambda s: s.lower() in {'true', 'yes', 't', 'y', '1'}

		short_help = help + " (this toggles the default if no value is passed)" if help else help
		yes_help = help
		no_help = negative_help if negative_help is not None else "Do not " + help[0].lower() + help[1:] if help else help
		if default:
			yes_help += " <default>"
		else:
			no_help += " <default>"

		group = self.add_mutually_exclusive_group()
		result = group.add_argument(*short_flags, dest=dest, nargs='?', default=default, const=not default, type=str_to_bool, help=short_help, **kw)
		group.add_argument(*long_flags, dest=dest, action='store_true', help=yes_help, **kw)
		group.add_argument(*map(no_f, long_flags), dest=dest, action='store_false', help=no_help, **kw)
		return result

	#TODO: Make it possible to pass the choice descriptions as values too?
	def add_choice_arg(self, choices, *flags, choice_descriptions=(), type=None, help="", **kw):
		"""
		Add a choice argument to the parser.

		Parameters
		----------
		choices : Collection[Union[int, float, str]]
			The possible choices.
		choice_descriptions : Collection[str], optional
			A list of descriptions for the choices.
		type : type, optional
			The type of the choices. If not provided, it is inferred from `choices` (`int` => `float` => `str`).

		Examples
		--------
		>>> ap.add_choice_arg((1, 2, 3), '-c', '--choice', default=1, type=float, help="Choose one of the options")
		>>> ap.add_choice_arg(('t2b', 'b2t'), '-m', '--method', choice_descriptions=("Top-to-bottom", "Bottom-to-top"), help="Method to use")
		"""

		if type is None:
			try:
				type = int if all(int(x) == x for x in choices) else float
			except ValueError:
				if all(isinstance(x, str) for x in choices):
					type = str
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
		return self.add_argument(*flags, type=type, choices=choices, help=help, **kw)

	def add_number_arg(self, *flags, min=None, max=None, range=None, nargs='+', type=None, help="", **kw):
		"""
		Add a number argument to the parser.

		The argument can receive multiple values (in which case it will be stored as a list). This can be explicitly restricted by passing `nargs=1` to this method.

		Parameters
		----------
		min : Union[int, float], optional
			The minimum value the argument can have.
		max : Union[int, float], optional
			The maximum value the argument can have.
		range : Tuple[Union[int, float], Union[int, float]], optional
			A tuple of the minimum and maximum values the argument can have (alternative to `min` and `max`).
		type : type, optional
			The type of the argument. If not provided, it is inferred from the `min` and `max` values (`int` => `float`).

		Examples
		--------
		>>> ap.add_number_arg('-n', '--number', min=0, max=1, nargs=1, type=float, help="A number between 0 and 1")
		>>> ap.add_number_arg('-l', '--list', min=0, nargs='+', type=int, help="A list of non-negative numbers")
		>>> ap.add_number_arg('-c', '--color', range=(0, 255), nargs=3, metavar=("R", "G", "B"), help="A color in RGB format")
		"""

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

		return self.add_argument(*flags, type=_type, action=ListOrSingleAction, nargs=nargs, help=help, **kw)


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
	assert _namespace.path_arg == Path('qwer') and _namespace.second_path_arg == Path('asdf')

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
	# assert _namespace.true_arg is False and _namespace.false_arg is True

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
	assert _namespace.number_arg is None and _namespace.number_arg2 == 40
	assert ap.parse_args(['-m', '50']).number_arg == 50.
	assert ap.parse_args(['-n', '610']).number_arg2 == 610
	assert ap.parse_args(['-m', '50.5', '60', '70']).number_arg == [50.5, 60., 70.]
	# ap.parse_args(['-m', '101'])  # should raise error
	# ap.parse_args(['-m', '50', '101'])  # should raise error
	# ap.parse_args(['-n', '-1'])  # should raise error

	# Print help
	ap.parse_args(['-h'])