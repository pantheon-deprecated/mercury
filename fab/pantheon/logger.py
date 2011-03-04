import logging
import logging.handlers
import logging.config
import ygg

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class DrushHandler(logging.Handler):
    def emit(self, record):
        send = {"drush": {"type": record.type,
                          "log_message": record.message,
                          "drush_message": record.drush_message,
                          "memory": record.memory,
                          "timestamp": record.timestamp,
                          "error": record.error},
                "source": 'drush',
                "command": record.command}
        r = ygg.send_event(record.name, send, ['source-drush', 'inbox', 'all'])

# register our custom handler so it can be used by the config file
logging.handlers.DrushHandler = DrushHandler

with open('/opt/pantheon/fab/pantheon/logging.conf', 'r') as f:
    logging.config.fileConfig(f)

