from zope.interface import Interface

class ICandidates(Interface):
    def create_table():
        """
        Create the candidates table.
        """

    def add_candidate(candidate):
        """
        Insert a candidate into the candidates table.
        """

    def all_candidates():
        """
        Get all candidate records.
        """

class IVotes(Interface):
    def create_table():
        """
        Create a table that holds the votes for each candidate.
        """

    def vote_for(candidate_id):
        """
        Add a single vote for a candidate.
        """

    def candidate_record(candidate_id):
        """
        Get a record for a candidate, which will return id, candidate name, and number of votes.
        """

    def vote_totals():
        """
        Get all the candidate records.
        """
