import logging
import logging.handlers
import logging.config

with open('/opt/pantheon/fab/pantheon/logging.conf', 'r') as f:
    logging.config.fileConfig(f)

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

