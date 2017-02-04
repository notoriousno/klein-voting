# -*- coding: utf-8 -*-

from __future__ import unicode_literals
#from os import path
#import sys
#filepath = path.split(path.split(path.realpath(__file__))[0])[0]
#sys.path.append(filepath)   # add project directory to Python path

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

import json
from twisted.internet import defer
from twisted.trial.unittest import TestCase
from main import Application

class TestVoteAPI(TestCase):

    app = Application(MagicMock())

    def test_json_welcome(self):
        request = MagicMock()
        request.requestHeaders.getRawHeaders.return_value = 'application/json'
        response = self.app.welcome(request)

        request.setHeader.assert_called_with('Content-Type', 'application/json')
        self.assertEquals(
            json.loads(response)['message'],
            'Welcome to the Vote App')

    def test_html_welcome(self):
        request = MagicMock()
        request.requestHeaders.getRawHeaders.return_value = 'text/html'
        response = self.app.welcome(request)

        request.setHeader.assert_called_with('Content-Type', 'text/html')
        self.assertEquals(response, '<h1>Welcome to the Vote App</h1>')

