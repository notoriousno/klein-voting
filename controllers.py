from klein import Klein
from twisted.internet import defer
from werkzeug.exceptions import NotFound

from database import Candidates, Votes
from middleware import Jsonify

class VoteApi(object):

    router = Klein()
    jsonify = Jsonify(router)

    def __init__(self, database):
        self.candidates = Candidates(database)
        self.votes = Votes(database, self.candidates)

    def resource(self):
        return self.router.resource()

    @router.handle_errors(NotFound)
    def page_not_found(self, request, failure):
        request.setResponseCode(404)
        request.setHeader('Content-Type', 'application/json')
        return {'status': 'Resource Not Available'}

    @jsonify.route('/candidates', methods=['GET'])
    def get_candidates(self, request):
        d = self.candidates.all_candidates()
        d.addErrback(self.database_failure, request)
        return d

    @jsonify.route('/candidate', methods=['POST'])
    def add_candidate(self, request):
        if b'candidate' not in request.args:
            request.setResponseCode(412)
            return {'status': 'Missing Prerequisite Input'}

        name = request.args[ b'candidate' ][0]
        d = self.candidates.add_candidate(name.decode('utf-8'))
        d.addErrback(self.database_failure, request)
        return d

    def database_failure(self, failure, request):
        request.setResponseCode(400)
        return {'status': 'Database Issue'}

    def extract_candidate(self, args):
        name = args[ b'candidate' ][0]
        return name.decode('utf-8')
