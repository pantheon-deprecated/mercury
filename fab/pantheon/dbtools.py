import os
from contextlib import contextmanager

import MySQLdb
from fabric.api import local

def export_data(project, environment, destination):
    """Export the database for a particular project/environment to destination.

    Exported database will have a name in the form of:
        /destination/project_environment.sql

    """
    filepath = os.path.join(destination, '%s_%s.sql' % (project, environment))
    username, password, db_name = _get_database_vars(project, environment)
    local("mysqldump --single-transaction --user='%s' \
                                          --password='%s' \
                                            %s > %s" % (username,
                                                       password,
                                                       db_name,
                                                       filepath))
    return filepath

def import_data(project, environment, source):
    """Create database then import from source.

    """
    database = '%s_%s' % (project, environment)
    create_database(database)
    import_db_dump(source, database)

def create_database(database):
    """Drop database if it already exists, then create a new empty db.

    """
    with MySQLconn() as dbconn:
        dbconn.execute('DROP DATABASE IF EXISTS %s' % database)
        dbconn.execute('CREATE DATABASE %s' % database)

def set_database_grants(database, username, password):
    """Grant ALL on database using username/password.

    """
    with MySQLconn() as dbconn:
        dbconn.execute("GRANT ALL ON %s.* TO '%s'@'localhost' \
                        IDENTIFIED BY '%s';\"" % (database,
                                                  username,
                                                  password))

def prepare_db_dump(database_dump):
    """Convert MyISAM to InnoDb.

    """
    local("sed -i 's/^[)] ENGINE=MyISAM/) ENGINE=InnoDB/' %s" % database_dump)

def import_db_dump(database_dump, database_name):
    """Import database_dump into database_name.
    database_dump: full path to the database dump.
    database_name: name of existing database to import into.

    """
    local('mysql -u root %s < %s' % (database_name, database_dump))


@contextmanager
class MySQLConn(object):

    def __init__(self, username='root', password='', database=None):
        """Initialize generic MySQL connection object.
        If no database is specified, makes a connection with no default db.

        """
        self.connection = self._mysql_connect(database, username, password)
        self.cursor = self.connection.cursor(MySQLdb.cursors.DictCursor)

    def __enter__(self):
        return self

    def __exit__(self, type, value, trackback):
        self.close()

    def execute(self, query, warn_only=False):
        """Execute a command on the connection.
        query: SQL statement.

        """
        try:
            self.cursor.execute(query)
        except MySQL.Error, e:
            print "MySQL Error %d: %s" % (e.args[0], e.args[1])
            if not warn_only:
                raise
        except MySQL.Warning, w:
            print "MySQL Warning: %s" % (w)
        return self.cursor.fetchall()

    def close(self):
        """Close database connection.

        """
        self.connection.close()

    def _mysql_connect(self, database, username, password):
        """Return a MySQL connection object.

        """
        try:
            conn = {'host': 'localhost',
                    'user': username,
                    'passwd': password}

            if database:
                conn.update({'db': database})

            return MySQLdb.connect(**conn)

        except MySQLdb.Error, e:
            print "MySQL Error %d: %s" % (e.args[0], e.args[1])
            raise

