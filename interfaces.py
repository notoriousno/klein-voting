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

    def get_candidate_by_id(candidate_id):
        """
        Retrieve a single candidate record via the candidate id number.
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

    def vote_total(candidate_id):
        """
        Get a record for a candidate, which will return id, candidate name, and number of votes.
        """

    def all_vote_totals():
        """
        Get all the candidate records.
        """
