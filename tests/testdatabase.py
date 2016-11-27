from __future__ import unicode_literals
from os import path
import sys
filepath = path.split(path.split(path.realpath(__file__))[0])[0]
sys.path.append(filepath)   # add project directory to Python path

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock
from twisted.trial.unittest import TestCase
from zope.interface.verify import verifyClass
from database import Database, Candidates, Votes
from interfaces import ICandidates, IVotes

class TestDatabase(TestCase):
    pass

class TestCandidates(TestCase):
    def setUp(self):
        self.table_name = 'candidates'
        self.db = MagicMock()
        self.candidates = Candidates(self.db)

    def test_contract(self):
        assert verifyClass(ICandidates, Candidates)

    def test_create_table(self):
        self.candidates.create_table()
        sql_stmt = 'create table %s (id integer primary key, name text unique not null)' % (self.table_name)
        self.db.execute.assert_called_with(sql_stmt)

    def test_add_candidate(self):
        candidate = 'Kanye West'
        self.candidates.add_candidate(candidate)
        insert_stmt = "insert into %s (name) values ('%s')" % (self.table_name, candidate)
        self.db.execute.assert_called_with(insert_stmt)

    def test_all_candidates(self):
        self.candidates.all_candidates()
        select_stmt = 'select id, name from %s' % (self.table_name)

    def test_add_name_lt25(self):
        name = 'abcdefghijklmnopqrstuvwxyz'
        self.assertRaises(AssertionError, self.candidates.add_candidate, name)

    def test_invalid_name_input(self):
        invalids = ['', '#klein', '"klein"', "'klein'", 'kle*in', 'klein;', '!@#$%^&*()-=_+']
        for item in invalids:
            self.assertRaises(AssertionError, self.candidates.add_candidate, item)

class TestVotes(TestCase):
    def test_contract(self):
        assert verifyClass(IVotes, Votes)
