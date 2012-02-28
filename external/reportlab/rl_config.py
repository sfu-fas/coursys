#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/rl_config.py
__version__=''' $Id: rl_config.py 3793 2010-09-30 11:27:09Z rgbecker $ '''
__doc__='''Configuration file.  You may edit this if you wish.'''

allowTableBoundsErrors =    1 # set to 0 to die on too large elements in tables in debug (recommend 1 for production use)
shapeChecking =             1
defaultEncoding =           'WinAnsiEncoding'       # 'WinAnsi' or 'MacRoman'
defaultGraphicsFontName=    'Times-Roman'           #initializer for STATE_DEFAULTS in shapes.py
pageCompression =           1                       # default page compression mode
useA85 =                    1                       #set to 0 to disable Ascii Base 85 stream filters
defaultPageSize =           'A4'                    #default page size
defaultImageCaching =       0                       #set to zero to remove those annoying cached images
ZLIB_WARNINGS =             1
warnOnMissingFontGlyphs =   0                       #if 1, warns of each missing glyph
verbose =                   0
showBoundary =              0                       # turns on and off boundary behaviour in Drawing
emptyTableAction=           'error'                 # one of 'error', 'indicate', 'ignore'
invariant=                  0                       #produces repeatable,identical PDFs with same timestamp info (for regression testing)
eps_preview_transparent=    None                    #set to white etc
eps_preview=                1                       #set to False to disable
eps_ttf_embed=              1                       #set to False to disable
eps_ttf_embed_uid=          0                       #set to 1 to enable
overlapAttachedSpace=       1                       #if set non false then adajacent flowable space after
                                                    #and space before are merged (max space is used).
longTableOptimize =         1                       #default don't use Henning von Bargen's long table optimizations
autoConvertEncoding  =      0                       #convert internally as needed (experimental)
_FUZZ=                      1e-6                    #fuzz for layout arithmetic
wrapA85=                    0                       #set to 1 to get old wrapped line behaviour
fsEncodings=('utf8','cp1252','cp430')               #encodings to attempt utf8 conversion with
odbc_driver=                'odbc'                  #default odbc driver
platypus_link_underline=    0                       #paragraph links etc underlined if true
canvas_basefontname=        'Helvetica'             #this is used to initialize the canvas; if you override to make
                                                    #something else you are responsible for ensuring the font is registered etc etc
                                                    #this will be used everywhere and the font family connections will be made
                                                    #if the bold/italic/bold italic fonts are also registered and defined as a family.

allowShortTableRows=1                               #allows some rows in a table to be short
imageReaderFlags=0                                  #attempt to convert images into internal memory files to reduce
                                                    #the number of open files (see lib.utils.ImageReader)
                                                    #if imageReaderFlags&2 then attempt autoclosing of those files
                                                    #if imageReaderFlags&4 then cache data 
                                                    #if imageReaderFlags==-1 then use Ralf Schmitt's re-opening approach
paraFontSizeHeightOffset=   1                       #if true paragraphs start at height-fontSize
canvas_baseColor=           None                    #initialize the canvas fill and stroke colors if this is set
ignoreContainerActions=     1                       #if true then action flowables in flowable _Containers will be ignored
ttfAsciiReadable=           1                       #smaller subsets when set to 0

import glob, os

# places to look for T1Font information
T1SearchPath = ['/usr/share/fonts/type1']
for d in glob.glob('/usr/share/fonts/type1/*'):
    if os.path.isdir(d):
        T1SearchPath.append(d)
T1SearchPath.extend([
                '/usr/share/fonts/X11/Type1', 
                '%(REPORTLAB_DIR)s/fonts',              #special
                '%(REPORTLAB_DIR)s/../fonts',           #special
                '%(REPORTLAB_DIR)s/../../fonts',        #special
                '%(HOME)s/fonts',                       #special
                ])

# places to look for TT Font information
TTFSearchPath = ['/usr/share/fonts/truetype']
for d in glob.glob('/usr/share/fonts/truetype/*'):
    if os.path.isdir(d):
        TTFSearchPath.append(d)
TTFSearchPath.extend([
                '/usr/lib/X11/fonts/TrueType/',
                '%(REPORTLAB_DIR)s/fonts',      #special
                '%(REPORTLAB_DIR)s/../fonts',   #special
                '%(REPORTLAB_DIR)s/../../fonts',#special
                '%(HOME)s/fonts',               #special
                ])

# places to look for CMap files - should ideally merge with above
CMapSearchPath = (
                  '/usr/share/ghostscript/8.71/Resource/CMap',
                  '%(REPORTLAB_DIR)s/fonts/CMap',       #special
                  '%(REPORTLAB_DIR)s/../fonts/CMap',    #special
                  '%(REPORTLAB_DIR)s/../../fonts/CMap', #special
                  '%(HOME)s/fonts/CMap',                #special
                  )

#### Normally don't need to edit below here ####
try:
    from local_rl_config import *
except:
    pass

_SAVED = {}
sys_version=None

#this is used to set the options from
def _setOpt(name, value, conv=None):
    '''set a module level value from environ/default'''
    from os import environ
    ename = 'RL_'+name
    if ename in environ:
        value = environ[ename]
    if conv: value = conv(value)
    globals()[name] = value

def _startUp():
    '''This function allows easy resetting to the global defaults
    If the environment contains 'RL_xxx' then we use the value
    else we use the given default'''
    V='''T1SearchPath
CMapSearchPath
TTFSearchPath
allowTableBoundsErrors
shapeChecking
defaultEncoding 
defaultGraphicsFontName
pageCompression 
defaultPageSize 
defaultImageCaching 
ZLIB_WARNINGS 
warnOnMissingFontGlyphs 
verbose 
showBoundary 
emptyTableAction
invariant
eps_preview_transparent
eps_preview
eps_ttf_embed
eps_ttf_embed_uid
overlapAttachedSpace
longTableOptimize 
autoConvertEncoding  
_FUZZ
wrapA85
fsEncodings
odbc_driver
platypus_link_underline
canvas_basefontname
allowShortTableRows
imageReaderFlags
paraFontSizeHeightOffset
canvas_baseColor
ignoreContainerActions
ttfAsciiReadable'''.split()
    import os, sys
    global sys_version, _unset_
    sys_version = sys.version.split()[0]        #strip off the other garbage
    from reportlab.lib import pagesizes
    from reportlab.lib.utils import rl_isdir

    if _SAVED=={}:
        _unset_ = getattr(sys,'_rl_config__unset_',None)
        if _unset_ is None:
            class _unset_: pass
            sys._rl_config__unset_ = _unset_ = _unset_()
        for k in V:
            _SAVED[k] = globals()[k]

    #places to search for Type 1 Font files
    import reportlab
    D = {'REPORTLAB_DIR': os.path.abspath(os.path.dirname(reportlab.__file__)),
        'HOME': os.environ.get('HOME',os.getcwd()),
        'disk': os.getcwd().split(':')[0],
        'sys_version': sys_version,
        }

    for name in ('T1SearchPath','TTFSearchPath','CMapSearchPath'):
        P=[]
        for p in _SAVED[name]:
            d = (p % D).replace('/',os.sep)
            if rl_isdir(d): P.append(d)
        _setOpt(name,P)

    for k in V[3:]:
        v = _SAVED[k]
        if isinstance(v,(int,float)): conv = type(v)
        elif k=='defaultPageSize': conv = lambda v,M=pagesizes: getattr(M,v)
        else: conv = None
        _setOpt(k,v,conv)

_registered_resets=[]
def register_reset(func):
    _registered_resets[:] = [x for x in _registered_resets if x()]
    L = [x for x in _registered_resets if x() is func]
    if L: return
    from weakref import ref
    _registered_resets.append(ref(func))

def _reset():
    #attempt to reset reportlab and friends
    _startUp()  #our reset
    for f in _registered_resets[:]:
        c = f()
        if c:
            c()
        else:
            _registered_resets.remove(f)

_startUp()
