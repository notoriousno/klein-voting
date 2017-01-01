from __future__ import unicode_literals
from numbers import Integral
import re
from twisted.internet import defer
from twisted.enterprise.adbapi import ConnectionPool
from zope.interface import implementer
from interfaces import ICandidates, IVotes

class Validations(object):
    def validate_candidate_id(self, candidate_id):
        assert isinstance(candidate_id, Integral), 'Candidate id must be an integer'
        assert candidate_id >= 0, 'Candidate id must be greater than 0'

    def validate_candidate_name(self, name):
        for substr in name.split(' '):
            assert substr.isalpha(), "Only UTF-8 compliant text permitted in a candidate's name"
        name_length = len(name)
        assert name_length > 0 and name_length <= 25, 'Candidate length must be between 1-25'

class Database(object):
    def __init__(self, dbpool):
        self.dbpool = dbpool

    def execute(self, sql_stmt):
        sql_stmt = self.sanitize(sql_stmt)
        if sql_stmt.lower().find('select') == 0:
            return self.dbpool.runQuery(sql_stmt)
        return self.dbpool.runInteraction(self._execute, sql_stmt)

    def _execute(self, cursor, sql_stmt):
        cursor.execute(sql_stmt)

    def sanitize(self, sql_stmt):
        replace = re.compile(r'(\\|#)')
        return replace.sub('', sql_stmt)

@implementer(ICandidates)
class Candidates(object):

    table_name = 'candidates'
    validate = Validations()

    def __init__(self, db):
        self.db = db

    def create_table(self):
        stmt = "create table %s (" \
            "id integer primary key, " \
            "name text unique not null)" % (self.table_name)
        return self.db.execute(stmt)

    def add_candidate(self, candidate_name):
        self.validate.validate_candidate_name(candidate_name)
        stmt = "insert into %s (name) values ('%s')" % (self.table_name, candidate_name)
        return self.db.execute(stmt)

    @defer.inlineCallbacks
    def get_candidate_by_id(self, candidate_id):
        self.validate.validate_candidate_id(candidate_id)
        query_stmt = 'select id, name from %s where id=%d' % (self.table_name, candidate_id)
        query = yield self.db.execute(query_stmt)
        if len(query) == 0:
            raise IndexError('No candidate found')
        defer.returnValue(query[0])

    def all_candidates(self):
        return self.db.execute('select id, name from %s' % (self.table_name))

@implementer(IVotes)
class Votes(object):

    table_name = 'votes'
    validate = Validations()

    def __init__(self, db, candidates):
        self.db = db
        self.candidates = candidates

    def create_table(self):
        stmt = "create table %s (" \
            "candidate int primary key, " \
            "votes int not null, " \
            "foreign key(candidate) references %s(id))" % (self.table_name, self.candidates.table_name)
        return self.db.execute(stmt)

    @defer.inlineCallbacks
    def vote_for(self, candidate_id):
        query = yield self.vote_total(candidate_id)     # query for the candidate

        # verify candidate exists or insert
        if len(query) == 0:
            query_candidates = yield self.candidates.get_candidate_by_id(candidate_id)
            if len(query_candidates) == 0:
                raise IndexError('Candidate id is not present')     # candidate doesn't exist

            # insert candidate id into votes table
            insert_stmt = "insert into %s (candidate, votes) values (%d, 1)" % (self.table_name, candidate_id)
            yield self.db.execute(insert_stmt)
            defer.returnValue(None)     # exit function

        # add a vote to existing record
        votes = query[0][2] + 1
        update_stmt = "update %s set votes=%d where candidate=%d" % (self.table_name, votes, candidate_id)
        yield self.db.execute(update_stmt)

    def vote_total(self, candidate_id):
        stmt = "select c.id, c.name, v.votes " \
            "from %s as v join %s as c on v.candidate=c.id "\
            "where c.id=%d" % (self.table_name, self.candidates.table_name, candidate_id)
        return self.db.execute(stmt)

    def all_vote_totals(self):
        stmt = "select c.id, c.name, v.votes " \
            "from %s as v join %s as c on v.candidate=c.id" % (self.table_name, self.candidates.table_name)
        return self.db.execute(stmt)
