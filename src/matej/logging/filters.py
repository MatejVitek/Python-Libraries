import logging


class MaxLevelFilter(logging.Filter):
	"""
	A `logging.Filter` that only lets messages under the specified level through.

	By default, the filter lets through messages below `logging.WARNING`.
	"""
	def __init__(self, level=logging.WARNING, *args, **kw):
		super().__init__(*args, **kw)
		self.level = level

	def filter(self, record):
		return record.levelno < self.level