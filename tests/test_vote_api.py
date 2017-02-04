# -*- coding: utf-8 -*-

from __future__ import unicode_literals

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

try:
    from cookielib import CookieJar
except ImportError:
    from http.cookiejar import CookieJar

from io import BytesIO
import json
from sys import getdefaultencoding
from klein.resource import ensure_utf8_bytes
from treq.testing import RequestTraversalAgent
from twisted.internet import defer
from twisted.trial.unittest import TestCase
from twisted.web.client import CookieAgent, readBody
from controllers import VoteApi
from main import Application
from middleware import Jsonify

class KleinResourceTester(object):

    encoding = getdefaultencoding()
    cookiejar = CookieJar()
    content = None
    status_code = None
    headers = None

    def __init__(self, router, base_url='https://localhost'):
        self.base_url = base_url
        self.mem_agent = RequestTraversalAgent(router.resource())
        self.mem_agent._realAgent = CookieAgent(self.mem_agent._realAgent, self.cookiejar)

    @defer.inlineCallbacks
    def request(self, method, uri, headers=None, body_producer=None):
        method = ensure_utf8_bytes(method)
        uri = ensure_utf8_bytes('/'.join([self.base_url, uri.strip('/')]))
        response = yield self.mem_agent.request(method, uri, headers, body_producer)
        content = yield readBody(response)
        self.content = content.decode(self.encoding)
        self.status_code = response.code
        self.headers = response.headers
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
        self.candidates.all_candidates.return_value = d
        values = [(1, 'Batman'), (2, 'Superman')]
        d.callback(values)

        response = self.client.request('GET', '/api/candidates')
        @response.addCallback
        def verify(ignored):
            self.assertEquals(self.client.status_code, 200)
            content = self.client.content
            assert len(values) == len(json.loads(content)['candidates'])
            content_type = self.client.headers.getRawHeaders('Content-Type', [None])[0]

        return response
