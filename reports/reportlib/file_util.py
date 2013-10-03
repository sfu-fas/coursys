""" Utility functions for dealing with files & filenames. """

import re
import os
import shutil

def stubify( value ):
    """ Converts an arbitrary string into a valid filename. 
    
    >>> stubify("Hey there, awesome pants!")
    'hey-there-awesome-pants'
    
    """
    stub = re.sub( '[-\s]+', '-', str(value) ) 
    return re.sub('[^\w\w-]', '', stub).strip().lower()

def force_dir( path ):
    """ Forces an empty directory to exist at path (if possible.) """
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    return path

