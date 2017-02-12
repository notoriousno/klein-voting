from functools import wraps
import json

from twisted.internet import defer

class Jsonify(object):

    def __init__(self, router):
        self.router = router

    def jsonify(self, f):
        @wraps(f)
        def deco(*args, **kwargs):
            request = args[1]
            result = defer.maybeDeferred(f, *args, **kwargs)
            result.addCallback(self.stringify, request)
            result.addErrback(self.stringify_failure, request)
            return result
        return deco

    def stringify(self, value, request):
        request.setHeader('Content-Type', 'application/json')
        if value != None:
            result = json.dumps(value)
            return result

    def stringify_failure(self, failure, request):
        request.setResponseCode(500)
        request.setHeader('Content-Type', 'application/json')
        return json.dumps({'status': 'Internal Issues'})

    def route(self, url, *args, **kwargs):
        def deco(f):
            f = self.jsonify(f)
            self.router.route(url, *args, **kwargs)(f)
        return deco
