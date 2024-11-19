import logging
from .loggers import *
from .handlers import *


def setup(cfg=None, **kw):
	if cfg is None:
		cfg = {}
	cfg = basic_cfg() | cfg | kw
	logging.config.dictConfig(cfg)


def basic_cfg(version=1, disable_existing=False):
	return {
		'version': version,
		'disable_existing_loggers': disable_existing,
	}


if __name__ == '__main__':
	logger = QueueLogger(None, *tee_handler_combo())
	print(logger.name)
	logger.debug('debug')
	logger.info('info')
	logger.warning('warning')
	logger.error('error')
	logger.critical('critical')

	logger = QueueLogger(__name__, *tee_handler_combo('test.log'))
	logger.debug('debug')
	logger.info('info')
	logger.warning('warning')
	logger.error('error')
	logger.critical('critical')

	logger = QueueLogger(__name__)
	logger.debug('debug')
	logger.info('info')
	logger.warning('warning')
	logger.error('error')
	logger.critical('critical')

	logger = logging.getLogger(__name__)
	logger.debug('debug')
	logger.info('info')
	logger.warning('warning')
	logger.error('error')
	logger.critical('critical')
