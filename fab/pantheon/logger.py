import logging
import logging.handlers
import logging.config
import ygg
import ConfigParser
import jenkinstools

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class DrushHandler(logging.Handler):
    def emit(self, record):
        send = {"drush": {"type": record.type,
                          "log_message": record.msg,
                          "message": record.drush_message,
                          "memory": record.memory,
                          "timestamp": record.timestamp,
                          "error": record.error,
                          "command": record.command},
                "source": 'drush'}
        ygg.send_event(record.name, send, ['source-drush', 'inbox', 'all'])

class ServiceHandler(logging.Handler):
    def emit(self, record):
        service = record.name.split('.')[-1]
        status_file = '/etc/pantheon/services.status'
        status = None

        if record.levelname in ['ERROR']:
            status = 'ERR'
        if record.levelname in ['WARNING']:
            status = 'WARN'
        if record.levelname in ['INFO']:
            status = 'OK'

        cfg = ConfigParser.ConfigParser()
        try:
            cfg.readfp(open(status_file))
            if not cfg.has_section(service):
                cfg.add_section(service)
            if not cfg.has_option(service, 'status'):
                cfg.set(service, 'status', status)
                saved_status = status
            else:
                saved_status = cfg.get(service, 'status')

            if status not in [None, saved_status]:
                cfg.set(service, 'status', status)
                # Write our configuration to file if the status has changed
                with open(status_file, 'wb') as cf:
                    cfg.write(cf)
                send = {"status": status,
                        "message": record.msg,
                        "type" : record.levelname}
                # Set service status in ygg 
                ygg.set_service(service, send)

        except IOError as (errno, strerror):
            # If file doesn't exist create it
            if errno == 2:
                if not cfg.has_section(service):
                    cfg.add_section(service)
                cfg.set(service, 'status', status)
                with open(status_file, 'wb') as cf:
                    cfg.write(cf)
            else:
                log.exception('FATAL: Uncaught exception in logging handler')
        except:
            log.exception('FATAL: Uncaught exception in logging handler')


class EventHandler(logging.Handler):
    def emit(self, record):
        source = record.name.split('.')[0]
        send = {source: {"message": record.msg,
                         "type" : record.levelname,
                         "created": record.created},
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

