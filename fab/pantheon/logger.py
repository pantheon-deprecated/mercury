import logging
import logging.handlers
import logging.config

logging.config.fileConfig("logging.conf")

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

