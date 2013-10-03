import file_util

class TitleAndDescription(object):
    """ Object with a title and a description. 

    """
    title = ""
    description = "" 
    
    @property
    def filename(self):
        """ Return a reasonable filename for the object.  
        
        >>> t = TitleAndDescription()
        >>> t.title = "How are you"
        >>> print t.filename + ".txt"
        how-are-you.txt

        """
        
        try:
            return file_util.stubify(self.title) 
        except AttributeError:
            return file_util.stubify(datetime.datetime.now())


