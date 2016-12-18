from os import path, remove
import sys

from twisted.enterprise.adbapi import ConnectionPool
from twisted.python.usage import Options
from twisted.internet import defer, task

from database import Database, Candidates, Votes
from main import Application

class CLI(Options):

    optParameters = [
        ['db', 'D', 'votes.sqlite', 'Path to the sqlite database.'],
        ['host', 'H', '127.0.0.1', 'Hostname'],
        ['port', 'P', 8000, 'Port number'],
        ['logpath', 'L', None, 'File path to log'],
    ]

    optFlags = [
        ['runserver', 'R', 'Run the Klein application'],
        ['create', 'C', 'Create/Recreate the database'],
    ]

@defer.inlineCallbacks
def create_tables(reactor, *models):
    for model in models:
        yield model.create_table()
        print('[x] Created the "%s" table' % (model.table_name))

def create_database(dbpath):
    dbpool = ConnectionPool('sqlite3', dbpath, check_same_thread=False)

    if path.exists(dbpath):
        answer = input('%s already exists. Delete? [yes/no]: ' % (dbpath))
        if answer.lower() in ['yes','y']:
            remove(dbpath)  # delete old database
        else:
            print('Database will not be created')
            sys.exit()      # don't delete

    # Create tables then exit
    dbpool = ConnectionPool('sqlite3', dbpath, check_same_thread=False)
    db = Database(dbpool)
    candidates = Candidates(db)
    votes = Votes(db, candidates)
    task.react(create_tables, (candidates, votes))
    sys.exit()

def runserver(dbpath, host, port, logpath):
    dbpool = ConnectionPool('sqlite3', dbpath, check_same_thread=False)
    app = Application(dbpool)
    print('Database: %s' % (dbpath))

    if logpath:
        logfile = open(logpath, 'a')
        print('Log File: %s' % (logpath))
    else:
        logfile = None

    print('Host: %s\nPort: %d\n' % (host, port))
    app.run(host, port, logfile)


if __name__=='__main__':
    cli = CLI()
    cli.parseOptions()

    if cli['create']:
        create_database(cli['db'])

    if cli['runserver']:
        runserver(
            dbpath=cli['db'],
            host=cli['host'],
            port=cli['port'],
            logpath=cli['logpath'])

