from klein import Klein

from controllers import VoteApi
from database import Database

class Application(object):

    router = Klein()

    def __init__(self, dbpool):
        self.database = Database(dbpool)
        self.vote_api = VoteApi(self.database)

    def run(self, *args, **kwargs):
        self.router.run(*args, **kwargs)

    @router.route('/api', branch=True)
    def home(self, request):
        return self.vote_api.resource()
