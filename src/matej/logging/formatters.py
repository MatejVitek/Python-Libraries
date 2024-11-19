import logging


class BasicFormatter(logging.Formatter):
	""" A `logging.Formatter` that only prints the level name and message. """
	def __init__(self, fmt=None, *args, **kw):
		super().__init__(fmt or '[%(levelname)s] %(message)s', *args, **kw)


class ISOFormatter(logging.Formatter):
	""" A `logging.Formatter` that prints the ISO timestamp and detailed information about the message. """
	def __init__(self, fmt=None, datefmt=None, *args, **kw):
		super().__init__(
			fmt or '%(asctime)s [%(levelname)s] (%(module)s:%(lineno)d) %(message)s',
			datefmt or '%Y-%m-%d %H:%M:%S (UTC%z)',
			*args, **kw
		)