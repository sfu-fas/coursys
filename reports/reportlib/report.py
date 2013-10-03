from title_and_description import TitleAndDescription
import schedule

class Report( TitleAndDescription ):
    """ The base class from which Report objects are derived. 
    
    Override 'title', 'description', 'users', schedule, 'run()' in children. """

    def __init__(self):
        self.artifacts = []
        pass

    def run(self):
        pass
    
