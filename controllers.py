import json

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
        response = {'status': 'Resource Not Available'}
        return json.dumps(response)

    @jsonify.route('/candidates', methods=['GET'])
    def get_candidates(self, request):
        """
        Get a list of candidates.

        :return: `{candidates: []}`
        """
        d = self.votes.all_vote_totals()
        @d.addCallback
        def db_to_json(results):
            """
            Encapsulate the db results to JSON.
            """
            candidates = []
            for record in results:
                record_id, name, votes = record
                if votes is None:
                    votes = 0
                candidates.append({
                    'id': record_id,
                    'name': name,
                    'votes': votes})
            return {'candidates': candidates}

        @d.addErrback
        def database_failure(failure, req=request):
            # database error, a good spot to log
            req.setResponseCode(400)
            return {'status': 'Database Issues'}

        return d

    @jsonify.route('/candidate', methods=['POST'])
    @defer.inlineCallbacks
    def add_candidate(self, request):
        """
        Add a candidate to the system.

        :param candidate: Name of a candidate.
        :type candidate: str
        :return: `{"status": "message"}`
        """
        if b'candidate' not in request.args:
            request.setResponseCode(412)
            return {'status': 'Missing Prerequisite Input'}

        name = request.args[b'candidate'][0]
        try:
            yield self.candidates.add_candidate(name.decode('utf-8'))
        except Exception as error:
            # database error, a good spot to log
            request.setResponseCode(400)
            defer.returnValue({'status': 'Database Issue'})

        # successfully created a record in the db
        request.setResponseCode(201)
        defer.returnValue({'status': 'Created'})

    @jsonify.route('/vote', methods=['POST'])
    @defer.inlineCallbacks
    def vote_for(self, request):
        """
        Vote for a candidate

        :param id: Candidate id
        :type id: int
        :return: `{"status": "message"}`
        """
        if b'id' not in request.args:
            request.setResponseCode(412)
            defer.returnValue({'status': 'Invalid User Input'})

        candidate_id = request.args[b'id']
        try:
            yield self.votes.vote_for(candidate_id)
        except IndexError:
            request.setResponseCode(416)
            defer.returnValue({'status': 'Invalid Candidate'})
        except Exception as error:
            # database error, a good spot to log
            request.setResponseCode(400)
            defer.returnValue({'status': 'Database Issue'})

        defer.returnValue({'status': 'Success'})
