import os

import MySQLdb
import pantheon
from fabric.api import local

def export_data(project, environment, destination):
    """Export the database for a particular project/environment to destination.

    Exported database will have a name in the form of:
        /destination/project_environment.sql

    """
    filepath = os.path.join(destination, '%s_%s.sql' % (project, environment))
    username, password, db_name = pantheon.get_database_vars(project, environment)
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
    db = MySQLConn()
    db.execute('DROP DATABASE IF EXISTS %s' % database)
    db.execute('CREATE DATABASE %s' % database)
    db.close()

def set_database_grants(database, username, password):
    """Grant ALL on database using username/password.

    """
    db = MySQLConn()
    db.execute("GRANT ALL ON %s.* TO '%s'@'localhost' \
                IDENTIFIED BY '%s';" % (database,
                                        username,
                                        password))
    db.close()

def import_db_dump(database_dump, database_name):
    """Import database_dump into database_name.
    database_dump: full path to the database dump.
    database_name: name of existing database to import into.

    """
    local('mysql -u root %s < %s' % (database_name, database_dump))

def convert_to_innodb(database):
    """Convert all table engines to InnoDB (if possible).

    """
    db = MySQLConn()
    tables = db.execute("SELECT TABLE_NAME AS name, ENGINE AS engine " + \
                        "FROM information_schema.TABLES "+ \
                        "WHERE TABLE_SCHEMA = '%s'" % database)
    for table in tables:
        if table.get('engine') == 'InnoDB':
            print '%s already uses InnoDB' % table.get('name')
        else:
            db.execute("ALTER TABLE %s.%s ENGINE='InnoDB'" % (database,
                                                    table.get('name')),
                                                        warn_only=True)
    db.close()

def clear_cache_tables(database):
    """Clear Drupal cache tables.

    """
    db = MySQLConn()
    # tuple of strings to match agains table_name.startswith()
    caches = ('cache_')
    # Other exact matches to look for and clear.
    other = ['ctools_object_cache',
             'accesslog',
             'watchdog']
    tables = db.execute("SELECT TABLE_NAME AS name " + \
                        "FROM information_schema.TABLES " + \
                        "WHERE TABLE_SCHEMA = '%s'" % database)
    for table in tables:
        table_name = table.get('name')
        if (table_name.startswith(caches)) or (table_name in other):
            db.execute('TRUNCATE %s.%s' % (database, table_name))
    db.close()


class MySQLConn(object):

    def __init__(self, username='root', password='', database=None):
        """Initialize generic MySQL connection object.
        If no database is specified, makes a connection with no default db.

        """
        self.connection = self._mysql_connect(database, username, password)
        self.cursor = self.connection.cursor(MySQLdb.cursors.DictCursor)

    def execute(self, query, warn_only=False):
        """Execute a command on the connection.
        query: SQL statement.

        """
        try:
            self.cursor.execute(query)
        except MySQLdb.Error, e:
            print "MySQL Error %d: %s" % (e.args[0], e.args[1])
            if not warn_only:
                raise
        except MySQLdb.Warning, w:
            print "MySQL Warning: %s" % (w)
        return self.cursor.fetchall()

    def close(self):
        """Close database connection.

        """
        self.cursor.close()
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

