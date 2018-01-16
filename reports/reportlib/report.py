from .db2_query import DB2_Query

class Report():
    """ The base class from which Report objects are derived. 
    
    Override 'run()' in children. """

    def __init__(self, logger):
        self.artifacts = []
        self.logger = logger
        DB2_Query.set_logger(logger)
        DB2_Query.connect()
        DB2_Query.clear_expired_members_from_cache()
        pass

    def run(self):
        pass
    
