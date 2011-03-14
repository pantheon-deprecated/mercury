import logging
import logging.handlers
import logging.config
import ygg
import ConfigParser

from pantheon import jenkinstools

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class DrushHandler(logging.Handler):
    def emit(self, record):
        send = {"drush": {"type": record.type,
                          "log_message": record.msg,
                          "drush_message": record.drush_message,
                          "memory": record.memory,
                          "timestamp": record.timestamp,
                          "error": record.error},
                "source": 'drush',
                "command": record.command}
        ygg.send_event(record.name, send, ['source-drush', 'inbox', 'all'])

class ServiceHandler(logging.Handler):
    def emit(self, record):
        conf_file = '/etc/pantheon/monitoring.conf'
        try:
            cfg = ConfigParser.ConfigParser()
            cfg.readfp(open(conf_file))
        except IOError:
            log.exception('Configuration file could not be loaded.')
        except:
            log.exception('FATAL: Uncaught exception in logging handler')

        service = record.name.split('.')[-1]
        status = saved_status = cfg.get(service, 'status')

        if record.levelname in ['ERROR']:
            status = 'ERR'
        if record.levelname in ['WARNING']:
            status = 'WARN'
        if record.levelname in ['INFO']:
            status = 'OK'

        if status != saved_status:
            cfg.set(service, 'status', status)
            # Write our configuration to file if the status has changed
            with open('/etc/pantheon/monitoring.conf', 'wb') as cf:
                cfg.write(cf)
            send = {"status": status,
                    "message": record.msg,
                    "type" : record.levelname}
            # Set service status in ygg 
            ygg.set_service(service, send)

class EventHandler(logging.Handler):
    def emit(self, record):
        source = record.name.split('.')[0]
        send = {source: {"message": record.msg,
                         "type" : record.levelname,
                         "created": record.created,
                         "asctime": record.asctime},
                "source": source}
        labels = ['source-%s' % source, 'inbox', 'all']
        if hasattr(record, 'labels'):
            labels = list(set(labels).union(set(record.labels)))
        ygg.send_event(record.name, send, labels)

class JunitHandler(logging.Handler):
    def emit(self, record):
        ts = record.name.split('.')[0].capitalize()
        tc = record.name.split('.')[-1].capitalize()
        if ts == tc:
            tc=None

        if record.levelname in ['ERROR', 'CRITICAL']:
            jenkinstools.junit_error(record.msg, ts, tc)
        if record.levelname in ['WARNING']:
            jenkinstools.junit_fail(record.msg, ts, tc)
        if record.levelname in ['INFO']:
            jenkinstools.junit_pass(record.msg, ts, tc)

# register our custom handlers so they can be used by the config file
logging.handlers.DrushHandler = DrushHandler
logging.handlers.ServiceHandler = ServiceHandler
logging.handlers.EventHandler = EventHandler
logging.handlers.NullHandler = NullHandler

with open('/opt/pantheon/fab/pantheon/logging.conf', 'r') as f:
    logging.config.fileConfig(f)

