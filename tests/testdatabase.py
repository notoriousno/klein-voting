from __future__ import unicode_literals
from os import path
import sys
filepath = path.split(path.split(path.realpath(__file__))[0])[0]
sys.path.append(filepath)   # add project directory to Python path

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock
from twisted.internet.defer import gatherResults
from twisted.trial.unittest import TestCase
from zope.interface.verify import verifyClass
from database import Database, Candidates, Votes
from interfaces import ICandidates, IVotes

class TestDatabase(TestCase):
    pass

class TestCandidates(TestCase):

    table_name = 'candidates'

    def setUp(self):
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

    def test_get_candidate_by_id(self):
        expected_result = (1, 'Mickey Mouse')
        self.db.execute.return_value = [expected_result]        # return a mocked query
        self.candidates = Candidates(self.db)

        candidate_id = 100
        d = self.candidates.get_candidate_by_id(candidate_id)   # inlineCallbacks returns a Deferred

        @d.addCallback
        def verify_results(result, expected=expected_result):
            assert result == expected
            return None

        @d.addCallback
        def verify_function_calls(prev_results):
            expected_sql_stmt = 'select id, name from %s where id=%d' % (self.table_name, candidate_id)
            self.db.execute.assert_called_with(expected_sql_stmt)

        return d    # wait for the Deferreds to finish

    def test_get_candidate_by_id_empty_query(self):
        self.db.execute.return_value = []       # this is unnecessary but demonstrates the expected function result
        self.candidates = Candidates(self.db)
        d = self.candidates.get_candidate_by_id(100)

        @d.addCallback
        def unexpected_success(result):
            raise Exception()

        @d.addErrback
        def verify_failure(failure):
            exception = failure.value
            assert isinstance(exception, IndexError)
            assert str(exception) == 'No result found.'

        return d

    def test_get_candidate_by_id_not_int(self):
        invalid_ids = ['100', 1.0, 0.0]
        deferred_list = []

        def verify_failure(failure):
            """
            Callback/Errback function that will be used to validate correct
            exception is raised.
            """
            exception = failure.value       # get the exception object
            assert isinstance(exception, AssertionError), '{} != AssertionError'.format(repr(exception))
            assert str(exception) == 'Candidate id must be an integer.'

        def unexpected_success(result, passing_value):
            msg = 'Unexpected success of candidate_id: {0}'.format(passing_value)
            raise ValueError(msg)

        for invalid_id in invalid_ids:
            d = self.candidates.get_candidate_by_id(invalid_id)
            d.addCallback(unexpected_success, invalid_id)
            d.addErrback(verify_failure)
            deferred_list.append(d)

        return gatherResults(deferred_list)

    def test_get_candidate_by_id_lt_0(self):
        invalid_ids = [-100, -1]
        deferred_list = []

        def verify_failure(failure):
            """
            Callback/Errback function that will be used to validate correct
            exception is raised.
            """
            exception = failure.value
            assert isinstance(exception, AssertionError), '{} != AssertionError'.format(repr(exception))
            assert str(exception) == 'Candidate id must be greater than 0.'

        def unexpected_success(result, passing_value):
            msg = 'Unexpected success of candidate_id: {0}'.format(passing_value)
            raise ValueError(msg)

        for invalid_id in invalid_ids:
            d = self.candidates.get_candidate_by_id(invalid_id)
            d.addCallback(unexpected_success, invalid_id)
            d.addErrback(verify_failure)
            deferred_list.append(d)

        return gatherResults(deferred_list)

    def test_all_candidates(self):
        self.candidates.all_candidates()
        select_stmt = 'select id, name from %s' % (self.table_name)

    def test_add_name_too_long(self):
        name = 'abcdefghijklmnopqrstuvwxyz'
        self.assertRaises(AssertionError, self.candidates.add_candidate, name)

    def test_add_name_too_short(self):
        name = ''
        self.assertRaises(AssertionError, self.candidates.add_candidate, name)

    def test_invalid_name_input(self):
        invalids = ['', '#klein', '"klein"', "'klein'", 'kle*in', 'klein;', '!@#$%^&*()-=_+', 'k13!n']
        for item in invalids:
            self.assertRaises(AssertionError, self.candidates.add_candidate, item)

class TestVotes(TestCase):
    def test_contract(self):
        assert verifyClass(IVotes, Votes)
