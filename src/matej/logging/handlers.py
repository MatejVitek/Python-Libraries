import logging
import sys
from .filters import MaxLevelFilter
from .formatters import BasicFormatter, ISOFormatter


class _Handler(logging.Handler):
	""" Base class for custom handlers. """
	def __init__(self, level=logging.NOTSET, max_level=None, formatter=BasicFormatter(), *filters, **kw):
		super().__init__(level, **kw)
		self.setLevel(level)
		self.setFormatter(formatter)
		if max_level is not None:
			self.addFilter(MaxLevelFilter(max_level))
		for filter in filters:
			self.addFilter(filter)


class StdoutHandler(logging.StreamHandler, _Handler):
	""" A `logging.StreamHandler` that logs to `stdout`. """
	def __init__(self, *args, **kw):
		logging.StreamHandler.__init__(self, sys.stdout)
		_Handler.__init__(self, *args, **kw)


class StderrHandler(logging.StreamHandler, _Handler):
	""" A `logging.StreamHandler` that logs to `stderr`. """
	def __init__(self, *args, **kw):
		logging.StreamHandler.__init__(self, sys.stderr)
		_Handler.__init__(self, *args, **kw)


class FileHandler(logging.FileHandler, _Handler):
	""" A `logging.Handler` that logs to a file. """
	def __init__(self, filename, *args, **kw):
		logging.FileHandler.__init__(self, filename)
		_Handler.__init__(self, *args, **kw)


def console_handler_combo(stdout_cfg=None, stderr_cfg=None):
	"""
	A `logging.Handler` combination that enables console logging.

	The levels that are logged to `stdout` and `stderr` can be set independently via `level` and `filters`.
	If a level is set to `None`, the corresponding stream will not be used.
	By default, the this will log warnings and errors to `stderr` and everything else to `stdout`.
	"""
	default_stderr_cfg = {
		'level': logging.WARNING,
		'formatter': BasicFormatter(),
	}
	stderr_cfg = default_stderr_cfg if stderr_cfg is None else default_stderr_cfg | stderr_cfg
	default_stdout_cfg = {
		'level': logging.DEBUG,
		'formatter': BasicFormatter(),
		'max_level': stderr_cfg['level'],
	}
	stdout_cfg = default_stdout_cfg if stdout_cfg is None else default_stdout_cfg | stdout_cfg

	handlers = []
	if stdout_cfg['level'] is not None:
		handlers.append(StdoutHandler(**stdout_cfg))
	if stderr_cfg['level'] is not None:
		handlers.append(StderrHandler(**stderr_cfg))
	return handlers


def tee_handler_combo(file=None, file_cfg=None, *args, **kw):
	"""
	A `logging.Handler` combination that enables simultaneous console and file logging.

	The levels that are logged to `stdout`, `stderr` and the file can be set independently.
	If a level is set to `None`, the corresponding stream will not be used.
	By default, the logger will log everything to the file and only warnings and errors to `stderr`.
	"""
	if file is None:
		import inspect
		file = f'{inspect.getmodule(inspect.stack()[1][0]).__name__}.log'
	default_file_cfg = {
		'level': logging.DEBUG,
		'formatter': ISOFormatter(),
	}
	if args:
		stdout_cfg = args[0]
		args = args[1:]
	else:
		stdout_cfg = kw.pop('stdout_cfg', {'level': None})
	file_cfg = default_file_cfg if file_cfg is None else default_file_cfg | file_cfg

	handlers = console_handler_combo(stdout_cfg, **kw)
	if file_cfg['level'] is not None:
		handlers.append(FileHandler(file, **file_cfg))
	return handlers
