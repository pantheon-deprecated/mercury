import logging
import logging.handlers
import logging.config
import ygg
import ConfigParser
import jenkinstools

log = logging.getLogger("pantheon.logger")

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class DrushHandler(logging.Handler):
    def emit(self, record):
        source = record.name.split('.')[0]
        details = {"message": record.msg,
                   "type": record.type,
                   "timestamp": record.timestamp,
                   "memory": record.memory,
                   "error": record.error,
                   "project": record.project,
                   "environment": record.environment,
                   "command": record.command}
        labels = ['source-%s' % source, 'inbox', 'all']
        ygg.send_event(record.thread, details, labels, source=source)

class ServiceHandler(logging.Handler):
    def emit(self, record):
        service = record.name.split('.')[-1]
        status_file = '/etc/pantheon/services.status'
        status = ''

        if record.levelname in ['ERROR']:
            status = 'ERR'
        if record.levelname in ['WARNING']:
            status = 'WARN'
        if record.levelname in ['INFO']:
            status = 'OK'

        cfg = ConfigParser.ConfigParser()
        try:
            cfg.readfp(open(status_file))
        except IOError as (errno, strerror):
            if errno == 2:
                log.debug('Status file not found. Writing to new file.')
            else:
                log.exception('FATAL: Uncaught exception in logging handler')
        except:
            log.exception('FATAL: Uncaught exception in logging handler')

        if not cfg.has_section(service):
            cfg.add_section(service)
        if not cfg.has_option(service, 'status'):
            saved_status = None
        else:
            saved_status = cfg.get(service, 'status')

        if status != saved_status:
            cfg.set(service, 'status', status)
            # Write configuration to file
            with open(status_file, 'wb') as cf:
                cfg.write(cf)
            send = {"status": status,
                    "message": record.msg,
                    "type" : record.levelname,
                    "timestamp": record.created}
            # Set service status in ygg 
            ygg.set_service(service, send)

class EventHandler(logging.Handler):
    def emit(self, record):
        source = record.name.split('.')[0]
        thread = record.taskid if hasattr(record, 'taskid') else record.thread
        
        details = {"message": record.msg,
                   "type" : record.levelname,
                   "timestamp": record.created}
        labels = ['source-%s' % source, 'inbox', 'all']
        if hasattr(record, 'labels'):
            labels = list(set(labels).union(set(record.labels)))
        if hasattr(record, 'project'):
            details['project'] = record.project
        if hasattr(record, 'environment'):
            details['environment'] = record.environment
        if hasattr(record, 'command'):
            details['command'] = record.command
        ygg.send_event(thread, details, labels, source=source)

class JunitHandler(logging.Handler):
    def emit(self, record):
        ts = record.name.split('.')[-1].capitalize()
        tc = record.funcName.capitalize()
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
logging.handlers.JunitHandler = JunitHandler
logging.handlers.NullHandler = NullHandler

with open('/opt/pantheon/fab/pantheon/logging.conf', 'r') as f:
    logging.config.fileConfig(f)

