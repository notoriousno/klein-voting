import json

from klein import Klein
from twisted.web.static import File

from controllers import VoteApi
from database import Database

class Application(object):

    router = Klein()

    def __init__(self, dbpool):
        self.database = Database(dbpool)
        self.vote_api = VoteApi(self.database)

    def run(self, *args, **kwargs):
        self.router.run(*args, **kwargs)

    @router.route('/')
    def welcome(self, request):
        message = 'Welcome to the Vote App'
        content_type = request.requestHeaders.getRawHeaders('Content-Type')
        if content_type == 'application/json':
            request.setHeader('Content-Type', 'application/json')
            return json.dumps({'message': message})
        request.setHeader('Content-Type', 'text/html')
        return '<h1>%s</h1>' % (message)

    @router.route('/public/', branch=True)
    def static_files(self, request):
        return File('./public')

    @router.route('/api', branch=True)
    def vote_rsrc(self, request):
        return self.vote_api.resource()
