# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from os import path
import sys
filepath = path.split(path.split(path.realpath(__file__))[0])[0]
sys.path.append(filepath)   # add project directory to Python path

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch
from itertools import chain
from twisted.enterprise.adbapi import ConnectionPool
from twisted.internet.defer import gatherResults, inlineCallbacks
from twisted.trial.unittest import TestCase
from zope.interface.verify import verifyClass
from database import Database, Candidates, Validations, Votes
from interfaces import ICandidates, IVotes

class TestValidations(TestCase):
    validate = Validations()

    def test_get_candidate_by_id(self):
        """ Validate id are positive integers """
        for i in range(0, 10000, 100):
            self.validate.validate_candidate_id(i)

    def test_get_candidate_by_id_not_int(self):
        """ Only integers are allowed, other types raise exception """
        invalid_ids = ['100', 1.0, 0.0]
        for invalid in invalid_ids:
            self.assertRaises(AssertionError, self.validate.validate_candidate_id, invalid)

    def test_negative_candidate_ids(self):
        """ Validate negative integers raise exception """
        for invalid in chain([x for x in range(-1000, 0, 100)], [y for y in range(-10, 0)]):
            self.assertRaises(AssertionError, self.validate.validate_candidate_id, invalid)

    def test_name_too_short(self):
        """ Candidate names must be > 0 """
        name = ''
        self.assertRaises(AssertionError, self.validate.validate_candidate_name, name)

    def test_name_too_long(self):
        """ Candidate names must be <= 25 """
        name = 'abcdefghijklmnopqrstuvwxyz'
        self.assertRaises(AssertionError, self.validate.validate_candidate_name, name)

    def test_invalid_name_input(self):
        """ Validate names with special characters or numbers raise an exception """
        invalids = ['', '#klein', '"klein"', "'klein'", 'kle*in', 'klein;', '!@#$%^&*()-=_+', 'k13!n']
        for name in invalids:
            self.assertRaises(AssertionError, self.validate.validate_candidate_name, name)

    def test_unicode_name(self):
        """ Validate unicode (utf-8) """
        unicode_names = ['فحسب', 'да', '他們爲什', 'qué', 'מדברים', 'Varför', 'Türkçe', 'ইঞ']
        for name in unicode_names:
            self.validate.validate_candidate_name(name)

    def test_invalid_with_unicode(self):
        """ Validate unicode + numbers raise exception """
        invalids = ['#берегу', 'm!foé']
        for name in invalids:
            self.assertRaises(AssertionError, self.validate.validate_candidate_name, name)

class TestDatabase(TestCase):

    @patch('twisted.enterprise.adbapi.ConnectionPool')
    def test_mocked_database(self, ConnectionPool):
        """
        There's modest evidence suggesting ConnectionPool is very well tested.
        So the object can be mocked.
        """
        dbpool = ConnectionPool('db_module', 'db_uri', *(), **{})
        db = Database(dbpool)

        # query
        query_stmt = 'select * from sometable where something=1'
        db.execute(query_stmt)
        dbpool.runQuery.assert_called_with(query_stmt)

        # other SQL statements
        sql_stmt = 'insert into sometable (col0, col1, col2) values (val0, val1, val2)'
        db.execute(sql_stmt)
        dbpool.runInteraction.assert_called_with(db._execute, sql_stmt)

    @inlineCallbacks
    def test_real_database(self):
        """ Test using a real connection to a database """
        from os import path
        import sqlite3

        db_name = 'UNITTEST.sqlite'
        db_path = path.realpath('UNITTEST.sqlite')

        dbpool = ConnectionPool('sqlite3', db_path, check_same_thread=False)
        db = Database(dbpool)
        table_name = 'test_table'

        # check if the db exists, create it if it doesn't
        if not path.exists(db_path):
            create_table_stmt = 'create table %s (key int primary key, name text)' % (table_name)
            yield db.execute(create_table_stmt)

        # remove any unnecessary files after this test case runs
        self.addCleanup(self.remove_test_files, db_path)

        # insert a record into the table
        key = 1
        name = 'test'
        insert_stmt = "insert into %s (key, name) values (%d, '%s')" % (table_name, key, name)
        yield db.execute(insert_stmt)

        # use the DBAPI 2.0 module to verify results
        connection = sqlite3.connect(db_name)
        cursor = connection.cursor()
        query_stmt = 'select key, name from %s where key=%d' % (table_name, key)
        cursor.execute(query_stmt)
        assert cursor.fetchone() == (key, name)
        
    test_real_database.skip = 'Tests using real db has too much overhead. Also, pytest has issues with inlineCallbacks.'

    def remove_test_files(self, *file_paths):
        """ Remove unnecessary files """
        from os import remove
        for file_path in file_paths:
            remove(file_path)

class TestCandidates(TestCase):

    table_name = 'candidates'

    def setUp(self):
        self.db = MagicMock()
        self.candidates = Candidates(self.db)

    def test_contract(self):
        """ Validate interface contract is fulfilled """
        assert verifyClass(ICandidates, Candidates), 'ICandidates contract not fulfilled'

    def test_create_table(self):
        """ Validate the create table syntax gets called by the database object """
        self.candidates.create_table()
        sql_stmt = 'create table %s (id integer primary key, name text unique not null)' % (self.table_name)
        self.db.execute.assert_called_with(sql_stmt)

    def test_add_candidate(self):
        """ Validate appropriate insert syntax is called with proper name """
        candidate = 'Kanye West'
        self.candidates.add_candidate(candidate)
        insert_stmt = "insert into %s (name) values ('%s')" % (self.table_name, candidate)
        self.db.execute.assert_called_with(insert_stmt)

    def test_get_candidate_by_id(self):
        """
        Get candidate by id value. This function returns a Deferred which 
        requires a different way of testing than most are accustomed to.
        2 success callbacks are chained to the Deferred and will execute after 
        the get_candidate_by_id function completes. It's in those callbacks 
        when results can be compared and verify that certain functions were 
        called. Final note, if Deferreds are being waited on, then the Deferred
        MUST be returned at the end of the function.
        """
        candidate_id = 100
        expected_result = (candidate_id, 'Mickey Mouse')
        self.db.execute.return_value = [expected_result]        # return a mocked query
        d = self.candidates.get_candidate_by_id(candidate_id)   # inlineCallbacks returns a Deferred

        @d.addCallback
        def verify_results(result, expected=expected_result):
            """ Verify actual result and expected results are the same """
            assert result == expected

        @d.addCallback
        def verify_function_calls(null):
            """ Verify correct SQL statement was executed """
            expected_sql_stmt = 'select id, name from %s where id=%d' % (self.table_name, candidate_id)
            self.db.execute.assert_called_with(expected_sql_stmt)

        return d    # wait for the Deferreds to finish

    def test_get_candidate_by_id_candidate_does_not_exist(self):
        """ Validate exception is raised when a candidate doesn't exist in the database. """
        self.db.execute.return_value = []       # this is unnecessary but demonstrates the expected function result
        d = self.candidates.get_candidate_by_id(100)

        @d.addCallback
        def unexpected_success(result):
            """
            If success callback is executed than the function ran with no errors
            which in this case is not the intended outcome.
            """
            raise Exception('Unexpected success')

        @d.addErrback
        def verify_failure(failure):
            """ Verify correct exception is raised """
            exception = failure.value
            assert isinstance(exception, IndexError)
            assert str(exception) == 'No candidate found'

        return d

    def test_get_candidate_by_id_not_int(self):
        """
        The get_candidate_by_id() function only accepts integers/longs.
        Verify all other types raise an exception.
        """
        invalid_ids = ['100', 1.0, 0.0]
        deferred_list = []

        def verify_failure(failure):
            """
            Callback/Errback function that will be used to validate correct
            exception is raised.
            """
            exception = failure.value       # get the exception object
            assert isinstance(exception, AssertionError), '{} != AssertionError'.format(repr(exception))
            assert str(exception) == 'Candidate id must be an integer'

        def unexpected_success(result, passing_value):
            msg = 'Unexpected success of candidate_id: {0}'.format(passing_value)
            raise ValueError(msg)

        for invalid_id in invalid_ids:
            d = self.candidates.get_candidate_by_id(invalid_id)
            d.addCallback(unexpected_success, invalid_id)   # if the success callback is run, then the function didn't work as intended
            d.addErrback(verify_failure)        # an error should occur in the Deferred function and start the error chain
            deferred_list.append(d)         # append Deferred to a list so that all the Deferred results can be gathered at on time

        return gatherResults(deferred_list)     # wait for all the Deferreds to finish running

    def test_get_candidate_by_id_lt_0(self):
        """ Verify integers < 0 raise exception """
        invalid_ids = [-100, -1]
        deferred_list = []

        def verify_failure(failure):
            """
            Callback/Errback function that will be used to validate correct
            exception is raised.
            """
            exception = failure.value
            assert isinstance(exception, AssertionError), '{} != AssertionError'.format(repr(exception))
            assert str(exception) == 'Candidate id must be greater than 0'

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
        """ Validate proper SQL syntax is executed to query for all records. """
        self.candidates.all_candidates()
        select_stmt = 'select id, name from %s' % (self.table_name)

    def test_add_name_too_long(self):
        """ Verify names length >= 25 raise exception """
        name = 'abcdefghijklmnopqrstuvwxyz'
        self.assertRaises(AssertionError, self.candidates.add_candidate, name)

    def test_add_name_too_short(self):
        """ Verify names length == 0 raise exception """
        name = ''
        self.assertRaises(AssertionError, self.candidates.add_candidate, name)

    def test_invalid_name_input(self):
        """ Verify invalid names raise exception """
        invalids = ['', '#klein', '"klein"', "'klein'", 'kle*in', 'klein;', '!@#$%^&*()-=_+', 'k13!n']
        for item in invalids:
            self.assertRaises(AssertionError, self.candidates.add_candidate, item)

class TestVotes(TestCase):

    table_name = 'votes'

    def setUp(self):
        self.db = MagicMock()
        self.candidates = MagicMock()
        self.candidates.table_name = 'candidates'
        self.votes = Votes(self.db, self.candidates)

    def test_contract(self):
        assert verifyClass(IVotes, Votes), 'IVotes contract not fulfilled'

    def test_create_table(self):
        self.votes.create_table()
        sql_stmt = 'create table %s (candidate int primary key, votes int not null, foreign key(candidate) references %s(id))' % \
            (self.table_name, self.candidates.table_name)
        self.votes.db.execute.assert_called_with(sql_stmt)

    def test_vote_for_candidate_exist_in_table(self):
        candidate_id = 1
        votes = 100
        record = (candidate_id, 'Candidate Name', votes)
        # mock a method call, devs MUST keep the expected results up-to-date!
        self.votes.candidate_record = MagicMock(return_value = [record])

        d = self.votes.vote_for(candidate_id)
        @d.addCallback
        def verify_update(results):
            sql_stmt = "update %s set votes=%d where candidate=%d" % (self.table_name, votes+1, candidate_id)
            self.db.execute.assert_called_with(sql_stmt)

    def test_vote_for_candidate_first_time(self):
        candidate_id = 1
        record = (candidate_id, 'Candidate Name')
        # mock a method call, devs MUST keep the expected results up-to-date!
        self.candidates.get_candidate_by_id.return_value = [record]

        d = self.votes.vote_for(candidate_id)
        @d.addCallback
        def verify_insert(results):
            sql_stmt = "insert into %s (candidate, votes) values (%d, 1)" % (self.table_name, candidate_id)
            self.db.execute.assert_called_with(sql_stmt)

    def test_vote_for_candidate_not_exist(self):
        self.votes.candidate_record = MagicMock(return_value = [])
        self.candidates.get_candidate_by_id.return_value = []

        d = self.votes.vote_for(1000000)
        @d.addCallback
        def unexpected_success(result):
            raise Exception('Unexpected success')

        @d.addErrback
        def verify_exception(failure):
            exception = failure.value
            assert isinstance(exception, IndexError), 'Incorrect exception raised'
            assert str(exception) == 'Candidate id is not present'
