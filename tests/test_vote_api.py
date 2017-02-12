# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from six import PY3

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

if PY3:
    from http.cookiejar import CookieJar
    from urllib.parse import urlencode
else:
    from cookielib import CookieJar
    from urllib import urlencode

from io import BytesIO
import json
from sys import getdefaultencoding
from klein.resource import ensure_utf8_bytes
from treq.testing import RequestTraversalAgent, _SynchronousProducer
from twisted.internet import defer
from twisted.trial.unittest import TestCase
from twisted.web.client import CookieAgent, readBody
from twisted.web.http_headers import Headers
from controllers import VoteApi
from main import Application
from middleware import Jsonify

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
        self.client = KleinResourceTester(self.app.router, 'https://example.com')
        self.candidates = self.app.vote_api.candidates = MagicMock()
        self.votes = self.app.vote_api.votes = MagicMock()

    def test_get_candidates(self):
        """
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

            candidates = json.loads(response.content)['candidates']
            assert len(values) == len(candidates)

        return request

    def test_get_candidates_no_votes(self):
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

    def test_add_candidate(self):
        """
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

    def test_page_not_found(self):
        """
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

    def test_vote_for(self):
        """
        """
        request = self.client.request(
            method = 'POST',
            uri = '/api/vote',
            headers = {'Content-Type': 'application/x-www-form-urlencoded'},
            params = {'id': 100})

        @request.addCallback
        def verify(response):
            self.assertEquals(response.code, 200)
            self.assertEquals(response.getHeaders('Content-Type')[0], 'application/json')

        return request
