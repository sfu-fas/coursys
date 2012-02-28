from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import textobject
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont  
from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_JUSTIFY

PAPER_SIZE = letter

import os

# media
folder = './external/sfu/'
logofile = os.path.join(folder, 'logo.png')
ttfFile = os.path.join(folder, 'BemboMTPro-Regular.ttf')
pdfmetrics.registerFont(TTFont("BemboMTPro", ttfFile))  
ttfFile = os.path.join(folder, 'DINPro-Regular.ttf')
pdfmetrics.registerFont(TTFont("DINPro", ttfFile))  

sfu_red = CMYKColor(0, 1, 0.79, 0.2)
sfu_grey = CMYKColor(0, 0, 0.15, 0.82)
sfu_blue = CMYKColor(1, 0.68, 0, 0.12)
black = CMYKColor(0, 0, 0, 1)

# translate digits to old-style numerals (in their Bembo character positions)
digit_trans = {}
for d in range(10):
    digit_trans[48+d] = unichr(0xF643 + d)

sc_trans_bembo = {}
# translate letters to smallcaps characters (in their [strange] Bembo character positions)
for d in range(26):
    if d<3: # A-C
        offset = d
    elif d<4: # D
        offset = d+2
    elif d<21: # E-U
        offset = d+3
    else: # V-Z
        offset = d+4
    sc_trans_bembo[65+d] = unichr(0xE004 + offset)
    sc_trans_bembo[97+d] = unichr(0xE004 + offset)

def drawStringLeading(canvas, x, y, text, charspace=0, mode=None):
    """
    Draws a string in the current text styles.
    
    Duplicate of Canvas.drawString, but passing charspace in when the string is drawn.
    """
    t = textobject.PDFTextObject(canvas, x, y)
    t.setCharSpace(charspace)
    if mode is not None: t.setTextRenderMode(mode)
    t.textLine(text)
    t.setCharSpace(0)
    canvas.drawText(t)

def put_lines(canvas, lines, x, y, width, style, font_size, leading):
    """
    Place these lines, with given leading
    """
    ypos = y
    for line in lines:
        if line == '':
            p = Spacer(1, font_size)
        else:
            line = unicode(line).translate(digit_trans)
            p = Paragraph(line, style)
        _,h = p.wrap(width, 1*inch)
        p.drawOn(canvas, x, ypos-h)
        ypos -= h + leading

def on_letterhead(contents, paper_size=PAPER_SIZE):
    """
    Put the provided contents on SFU letterhead and return ReportLab canvas object.
    
    Implements "2009" version of letterhead in SFU graphic design specs: http://www.sfu.ca/clf/downloads.html
    """
    pg_w, pg_h = paper_size
    lr_margin = 0.75*inch
    top_margin = 0.5*inch
    para_width = pg_w - 2*lr_margin
    
    c = canvas.Canvas("letter.pdf", pagesize=paper_size)
    
    # SFU logo
    c.drawImage(logofile, x=lr_margin, y=pg_h-top_margin-0.5*inch, width=1*inch, height=0.5*inch)
    
    # unit text
    c.setFont('BemboMTPro', 12)
    c.setFillColor(sfu_blue)
    drawStringLeading(c, 2*inch, pg_h - top_margin - 0.375*inch, u'School of Computing Science'.translate(sc_trans_bembo), charspace=1.2)
    
    # footer
    c.setFont('BemboMTPro', 12)
    c.setFillColor(sfu_red)
    drawStringLeading(c, lr_margin, 0.5*inch, u'Simon Fraser University'.translate(sc_trans_bembo), charspace=1.4)
    c.setFont('DINPro', 6)
    c.setFillColor(sfu_grey)
    drawStringLeading(c, 3.15*inch, 0.5*inch, u'Engaging the World'.upper(), charspace=2)
    
    # address blocks
    addr_style = ParagraphStyle(name='Normal',
                                  fontName='BemboMTPro',
                                  fontSize=10,
                                  leading=10,
                                  textColor=sfu_grey)
    lines = ['9971 Applied Sciences Building', '8888 University Drive, Burnaby, BC', 'Canada V5A 1S6']
    put_lines(c,lines, 2*inch, pg_h - top_margin - 0.75*inch, 2.25*inch, addr_style, 8, 1.5)
    lines = [u'Tel'.translate(sc_trans_bembo) + ': 778-782-4277', u'Fax'.translate(sc_trans_bembo) + ': 778-782-3045']
    put_lines(c, lines, 4.5*inch, pg_h - top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)
    lines = ['csdept@cs.sfu.ca', 'www.cs.sfu.ca']
    put_lines(c, lines, 6.25*inch, pg_h - top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)

    # content

    content_style = ParagraphStyle(name='Normal',
                                  fontName='BemboMTPro',
                                  fontSize=12,
                                  leading=12,
                                  alignment=TA_JUSTIFY,
                                  textColor=black)
    frame_contents = []
    frame_contents.append(Paragraph(contents, content_style))
    frame_contents.append(Spacer(1, 12))
    frame_contents.append(Paragraph(contents, content_style))
    frame_contents.append(Spacer(1, 12))
    frame_contents.append(Paragraph(contents, content_style))

    frame = Frame(lr_margin, inch, para_width, pg_h-3*inch)
    frame.addFromList(frame_contents, c)

    return c