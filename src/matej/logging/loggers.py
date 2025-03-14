import atexit
import logging
import logging.handlers
import sys
import warnings


class _LoggerMeta(type):
	def __call__(cls, name, *args, **kw):
		if name in logging.Logger.manager.loggerDict:
			logger = logging.getLogger(name)
			if isinstance(logger, cls) and not args and not kw:
				warnings.warn(f"Logger {name} already exists. The preferred method of accessing the existing logger is `logging.getLogger({name})`.", stacklevel=2)
				return logger
			warnings.warn(f"Logger {name} already exists but will be reinitialised. The preferred method is to use `logging.getLogger({name})` and reconfigure the existing instance.", stacklevel=2)
		# This is hacky but it's the best way I could figure out to properly instantiate and register the logger
		logger = cls.__new__(cls, name, *args, **kw)
		logger.__init__(name, *args, **kw)
		logger.manager = logging.Logger.manager
		logger.manager.loggerDict[name] = logger
		logger.manager._fixupParents(logger)
		return logger


class _StreamRedirector:
	def __init__(self, logger, level):
		self.logger = logger
		self.level = level
		self.buf = []

	#TODO: If messages are printed out with too many new lines or other strange stuff is happening, then I should
	#      do nothing in flush() and log stuff in write() instead.
	def write(self, msg):
		if msg.endswith("\n"):
			self.buf.append(msg.removesuffix("\n"))
			self.flush()
		else:
			self.buf.append(msg)

	def flush(self):
		if self.buf:
			self.logger.log(self.level, "".join(self.buf))
			self.buf = []


class Logger(logging.Logger, metaclass=_LoggerMeta):
	"""	A simple `logging.Logger` that can also be used as a base class for custom loggers. """

	def __init__(self, name=None, *handlers, redirect_stdout=False, redirect_stderr=False):
		"""
		Initialise the logger with the given name and handlers.

		Parameters:
		-----------
		name : str, optional
			The name of the logger. If not provided, the name of the module calling the logger will be used.
		handlers : Collection[logging.Handler], optional
			Handlers to add to the logger.
		redirect_stdout : bool or int, optional
			The level at which messages from stdout should be logged.
			If `False`, stdout will not be redirected.
			If `True`, stdout messages will be logged at the `logging.INFO` level.
		redirect_stderr : bool or int, optional
			The level at which messages from stderr should be logged.
			If `False`, stderr will not be redirected.
			If `True`, stderr messages will be logged at the `logging.ERROR` level.
		"""
		if name is None:
			import inspect
			name = inspect.getmodule(inspect.stack()[1][0]).__name__
			warnings.warn("Logger name not provided. Initialising with module name ('{name}'). Providing an explicit name is recommended.", stacklevel=2)
		super().__init__(name)
		for handler in handlers:
			self.addHandler(handler)

		self._old_stdout = None
		if redirect_stdout:
			if redirect_stdout is True:
				redirect_stdout = logging.INFO
			self._old_stdout = sys.stdout
			sys.stdout = _StreamRedirector(self, redirect_stdout)

		self._old_stderr = None
		if redirect_stderr:
			if redirect_stderr is True:
				redirect_stderr = logging.ERROR
			self._old_stderr = sys.stderr
			sys.stderr = _StreamRedirector(self, redirect_stderr)


	def restore_output_streams(self):
		""" Restore the original stdout and stderr streams. """
		if self._old_stdout is not None:
			sys.stdout = self._old_stdout
		if self._old_stderr is not None:
			sys.stderr = self._old_stderr

	def __del__(self):
		try:
			self.restore_output_streams()
		except AttributeError:
			sys.stdout = sys.__stdout__
			sys.stderr = sys.__stderr__
		return super().__del__()


class QueueLogger(Logger):
	""" A `logging.Logger` that utilises queue-based logging with an arbitrary number of handlers. """

	def __init__(self, name=None, *handlers, multiprocessing_=False, respect_handler_level=True, **kw):
		super().__init__(name, **kw)
		# Set up the queue and the queue handler
		if multiprocessing_:
			from multiprocessing import Queue
			self.queue = Queue()
		else:
			from queue import SimpleQueue
			self.queue = SimpleQueue()
		self.handlers = [logging.handlers.QueueHandler(self.queue)]

		# Set up level
		self._level = kw.pop('level', None)

		# Set up the handlers and the queue listener
		self.listener = logging.handlers.QueueListener(self.queue, *handlers, respect_handler_level=respect_handler_level)
		atexit.register(self.listener.stop)
		self.listener.start()

	def addHandler(self, handler):
		# Stop and restart the listener when adding handlers to avoid race conditions
		self.listener.stop()
		self.listener.handlers = (*self.listener.handlers, handler)
		self.listener.start()

	def removeHandler(self, handler):
		# Stop and restart the listener when removing handlers to avoid race conditions
		self.listener.stop()
		self.listener.handlers = tuple(h for h in self.listener.handlers if h is not handler)
		self.listener.start()

	@property
	def level(self):
		if self._level is None:
			# Level hasn't been explicitly set, so return the minimum level of all handlers (so we don't inherit the WARNING level of the root logger)
			try:
				return min(h.level for h in self.listener.handlers)
			except ValueError:
				# No handlers, so return NOTSET
				return logging.NOTSET
		return self._level

	@level.setter
	def level(self, level):
		self._level = level
