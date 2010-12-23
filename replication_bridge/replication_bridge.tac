from twisted.application import strports
import twisted
import sys
from replication_bridge import factory
application = twisted.application.service.Application('ReplicationBridge')
#logfile = twisted.python.logfile.DailyLogFile('alpha.log', '/var/log')
#application.setComponent(twisted.python.log.ILogObserver, twisted.python.log.FileLogObserver(logfile).emit)
server = strports.service('tcp:9999', factory)
server.setServiceParent(application)
