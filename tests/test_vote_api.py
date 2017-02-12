# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from six import PY3

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

if PY3:
    from http.cookiejar import CookieJar
    from urllib.parse import urlencode
else:
    from cookielib import CookieJar
    from urllib import urlencode

import json
from sys import getdefaultencoding

from klein.resource import ensure_utf8_bytes
from treq.testing import RequestTraversalAgent, _SynchronousProducer
from twisted.internet import defer
from twisted.trial.unittest import TestCase
from twisted.web.client import CookieAgent, readBody
from twisted.web.http_headers import Headers

from main import Application

class KleinResourceTester(object):

    encoding = getdefaultencoding()
    cookiejar = CookieJar()

    def __init__(self, router, base_url='https://example.com'):
        self.base_url = base_url
        self.mem_agent = RequestTraversalAgent(router.resource())
        self.mem_agent._realAgent = CookieAgent(self.mem_agent._realAgent, self.cookiejar)

    def _create_headers(self, headers_dict):
        headers = Headers()
        for key, value in headers_dict.items():
            if isinstance(value, list):
                headers.setRawHeaders(key, value)
            else:
                headers.addRawHeader(key, value)
        return headers

    @defer.inlineCallbacks
    def request(self, method, uri, headers=None, params=None, body=None):
        """
        """
        if headers is not None:
            headers = self._create_headers(headers)

        body_producer = None
        if params is not None:
            body_producer = _SynchronousProducer(urlencode(params))
        if body is not None:
            body_producer = _SynchronousProducer(body)

        method = ensure_utf8_bytes(method)
        uri = ensure_utf8_bytes('/'.join([self.base_url, uri.strip('/')]))
        response = yield self.mem_agent.request(method, uri, headers, body_producer)
        content = yield readBody(response)
        response.content = content.decode(self.encoding)
        response.getHeaders = response.headers.getRawHeaders
        defer.returnValue(response)

class TestVoteAPI(TestCase):

    database = MagicMock()
    app = Application(database)

    def setUp(self):
        self.client = KleinResourceTester(
            router = self.app.router,
            base_url = 'https://example.com')
        self.candidates = self.app.vote_api.candidates = MagicMock()
        self.votes = self.app.vote_api.votes = MagicMock()

    def test_get_candidates(self):
        """
        Get a list of all the candidates
        """
        d = defer.Deferred()
        self.votes.all_vote_totals.return_value = d
        values = [
            (1, 'Batman', None),
            (2, 'Spiderman', 1),
            (3, 'Superman', 100)]
        d.callback(values)

        request = self.client.request('GET', '/api/candidates')
        @request.addCallback
        def verify(response):
            self.assertEquals(response.code, 200)
            content_type = response.getHeaders('Content-Type')[0]
            self.assertEquals(content_type, 'application/json')

            candidates = json.loads(response.content)['candidates']
            assert len(values) == len(candidates)

        return request

    def test_get_candidates_no_votes(self):
        """
        Candidates that have no votes returns 0
        """
        d = defer.Deferred()
        self.votes.all_vote_totals.return_value = d
        value = [(1, 'Lex Luther', None)]
        d.callback(value)

        request = self.client.request('GET', '/api/candidates')
        @request.addCallback
        def verify(response):
            candidates = candidates = json.loads(response.content)['candidates'][0]
            for _id, name, votes in value:
                self.assertEquals(candidates['id'], _id)
                self.assertEquals(candidates['name'], name)
                self.assertEquals(candidates['votes'], 0)

        return request

    def test_add_candidate(self):
        """
        Add a candidate
        """
        form_data = {'candidate': 'Kal El'}
        request = self.client.request(
            method = 'POST',
            uri = '/api/candidate',
            headers = {'Content-Type': 'application/x-www-form-urlencoded'},
            params = form_data)

        @request.addCallback
        def verify(response):
            self.assertEquals(response.code, 201)
            self.assertEquals(response.getHeaders('Content-Type')[0], 'application/json')
            content = json.loads(response.content)
            self.assertEquals(content['status'], 'Created')

        return request

    def test_add_candidate_no_name(self):
        """
        Error when no candidate name is passed when adding a candidate
        """
        request = self.client.request(
            method = 'POST',
            uri = '/api/candidate')

        @request.addCallback
        def verify(response):
            self.assertEquals(response.code, 412)
            self.assertEquals(response.getHeaders('Content-Type')[0], 'application/json')
            content = json.loads(response.content)
            self.assertEquals(content['status'], 'Missing Prerequisite Input')

        return request

    def test_page_not_found(self):
        """
        Return a particular output when a page/endpoint isn't available.
        """
        request = self.client.request(
            method = 'GET',
            uri = '/api/doesnt_exist')

        @request.addCallback
        def verify(response):
            self.assertEquals(response.code, 404)
            self.assertEquals(response.getHeaders('Content-Type')[0], 'application/json')
            content = json.loads(response.content)
            self.assertEquals(content['status'], 'Resource Not Available')

        return request

    def test_vote_for(self):
        """
        Vote for a particular candidate
        """
        form_data = {'id': 100}
        request = self.client.request(
            method = 'POST',
            uri = '/api/vote',
            headers = {'Content-Type': 'application/x-www-form-urlencoded'},
            params = form_data)

        @request.addCallback
        def verify(response):
            self.assertEquals(response.code, 200)
            self.assertEquals(response.getHeaders('Content-Type')[0], 'application/json')
            content = json.loads(response.content)
            self.assertEquals(content['status'], 'Success')

            # verify form data is converting into int
            # and db functions are properly called
            args, kwargs = self.votes.vote_for.call_args
            self.assertIsInstance(args[0], int)
            self.votes.vote_for.assert_called_with(form_data['id'])
            self.assertEquals(args[0], form_data['id'])

        return request

    def test_vote_for_id_not_int(self):
        """
        Status code 412 returned when id is not an int
        """
        def invalid_vote(candidate_id):
            """
            :return: `Deferred`/`Response`
            """
            form_data = {'id': candidate_id}
            request = self.client.request(
                method = 'POST',
                uri = '/api/vote',
                headers = {'Content-Type': 'application/x-www-form-urlencoded'},
                params = form_data)

            request.addCallback(verify)
            return request

        def verify(response):
            """
            Verification callback
            """
            self.assertEquals(response.code, 412)
            self.assertEquals(response.getHeaders('Content-Type')[0], 'application/json')
            content = json.loads(response.content)
            self.assertEquals(content['status'], 'Invalid User Input')

        invalid_ids = ['one', '1 hundred', '']
        deferred_list = []
        for invalid in invalid_ids:
            d = invalid_vote(invalid)
            deferred_list.append(d)

        return defer.gatherResults(deferred_list)
