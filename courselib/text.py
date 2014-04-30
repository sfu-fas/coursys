import re

# from http://code.activestate.com/recipes/435882-normalizing-newlines-between-windowsunixmacs/
_newlines_re = re.compile(r'(\r\n|\r|\r)')
def normalize_newlines(string):
    """
    Convert text to unix linebreaks
    """
    return _newlines_re.sub('\n', string)


many_newlines = re.compile(r'\n{3,}')

# collapse redundant linebreaks with:
# foo = many_newlines.sub('\n\n', foo)