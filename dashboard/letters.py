from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Spacer, Frame, KeepTogether, Flowable, NextPageTemplate, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import textobject
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont  
from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_JUSTIFY
import os, datetime

PAPER_SIZE = letter
media_path = os.path.join('external', 'sfu')

from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate

class LetterPageTemplate(PageTemplate):
    def __init__(self, pagesize, *args, **kwargs):
        self._set_margins(pagesize)
        kwargs['frames'] = [self._create_frame(pagesize)]
        kwargs['pagesize'] = pagesize
        PageTemplate.__init__(self, *args, **kwargs)
    
    def _set_margins(self, pagesize):
        self.pg_w, self.pg_h = pagesize
        self.lr_margin = 0.75*inch
        self.top_margin = 0.5*inch
        self.para_width = self.pg_w - 2*self.lr_margin

    def _create_frame(self, pagesize):
        frame = Frame(self.lr_margin, inch, self.para_width, self.pg_h-2*inch)
        return frame

    def _drawStringLeading(self, canvas, x, y, text, charspace=0, mode=None):
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

    def _put_lines(self, doc, canvas, lines, x, y, width, style, font_size, leading):
        """
        Place these lines, with given leading
        """
        ypos = y
        for line in lines:
            line = unicode(line).translate(doc.digit_trans)
            p = Paragraph(line, style)
            _,h = p.wrap(width, 1*inch)
            p.drawOn(canvas, x, ypos-h)
            ypos -= h + leading

    def beforeDrawPage(self, c, doc):
        "Draw the letterhead before anything else"
        # non-first pages only get the footer, not the header
        self._draw_footer(c, doc)

    def _draw_footer(self, c, doc):
        """
        Draw the bottom-of-page part of the letterhead (used on all pages)
        """
        c.setFont('BemboMTPro', 12)
        c.setFillColor(doc.sfu_red)
        self._drawStringLeading(c, self.lr_margin + 6, 0.5*inch, u'Simon Fraser University'.translate(doc.sc_trans_bembo), charspace=1.4)
        c.setFont('DINPro', 6)
        c.setFillColor(doc.sfu_grey)
        self._drawStringLeading(c, 3.15*inch, 0.5*inch, u'Engaging the World'.upper(), charspace=2)
        

class LetterheadTemplate(LetterPageTemplate):
    def __init__(self, unit, *args, **kwargs):
        LetterPageTemplate.__init__(self, *args, **kwargs)
        self.unit = unit
    
    def beforeDrawPage(self, c, doc):
        "Draw the letterhead before anything else"
        self._draw_header(c, doc)
        self._draw_footer(c, doc)

    def _create_frame(self, pagesize):
        frame = Frame(self.lr_margin, inch, self.para_width, self.pg_h-3*inch)
        return frame

    def _draw_header(self, c, doc):
        """
        Draw the top-of-page part of the letterhead (used only on first page of letter)
        """
        # SFU logo
        c.drawImage(doc.logofile, x=self.lr_margin + 6, y=self.pg_h-self.top_margin-0.5*inch, width=1*inch, height=0.5*inch)

        # unit text
        c.setFont('BemboMTPro', 12)
        c.setFillColor(doc.sfu_blue)
        self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.375*inch, self.unit.name.translate(doc.sc_trans_bembo), charspace=1.2)

        # address/contact blocks
        addr_style = ParagraphStyle(name='Normal',
                                      fontName='BemboMTPro',
                                      fontSize=10,
                                      leading=10,
                                      textColor=doc.sfu_grey)
        self._put_lines(doc, c, self.unit.address(), 2*inch, self.pg_h - self.top_margin - 0.75*inch, 2.25*inch, addr_style, 8, 1.5)

        lines = [u'Tel'.translate(doc.sc_trans_bembo) + ' ' + self.unit.tel()]
        if self.unit.fax():
            lines.append(u'Fax'.translate(doc.sc_trans_bembo) + ' ' + self.unit.fax())
        self._put_lines(doc, c, lines, 4.5*inch, self.pg_h - self.top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)

        lines = []
        if self.unit.email():
            lines.append(self.unit.email())
        web = self.unit.web()
        if web.startswith("http://"):
            web = web[7:]
        if web.endswith("/"):
            web = web[:-1]
        lines.append(web)
        self._put_lines(doc, c, lines, 6.25*inch, self.pg_h - self.top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)
        


class OfficialLetter(BaseDocTemplate):
    """
    Template for a letter on letterhead.
    
    Implements "2009" version of letterhead in SFU graphic design specs: http://www.sfu.ca/clf/downloads.html
    """
    def __init__(self, filename, unit, pagesize=PAPER_SIZE, *args, **kwargs):
        self._media_setup()
        kwargs['pagesize'] = pagesize
        kwargs['pageTemplates'] = [LetterheadTemplate(pagesize=pagesize, unit=unit), LetterPageTemplate(pagesize=pagesize)]
        BaseDocTemplate.__init__(self, filename, *args, **kwargs)
        self.contents = [] # to be a list of Flowables
    
    def add_letter(self, letter):
        "Add the given LetterContents object to this document"
        self.contents.extend(letter._contents(self))
    
    def write(self):
        "Write the PDF contents out"
        self.build(self.contents)

    def _media_setup(self):
        "Get all of the media needed for the letterhead"
        # fonts and logo
        ttfFile = os.path.join(media_path, 'BemboMTPro-Regular.ttf')
        pdfmetrics.registerFont(TTFont("BemboMTPro", ttfFile))  
        ttfFile = os.path.join(media_path, 'DINPro-Regular.ttf')
        pdfmetrics.registerFont(TTFont("DINPro", ttfFile))  
        self.logofile = os.path.join(media_path, 'logo.png')
        
        # graphic standards colours
        self.sfu_red = CMYKColor(0, 1, 0.79, 0.2)
        self.sfu_grey = CMYKColor(0, 0, 0.15, 0.82)
        self.sfu_blue = CMYKColor(1, 0.68, 0, 0.12)
        self.black = CMYKColor(0, 0, 0, 1)
        
        # styles
        self.line_height = 12
        self.content_style = ParagraphStyle(name='Normal',
                                      fontName='BemboMTPro',
                                      fontSize=12,
                                      leading=self.line_height,
                                      allowWidows=0,
                                      allowOrphans=0,
                                      alignment=TA_JUSTIFY,
                                      textColor=self.black)

        # translate digits to old-style numerals (in their Bembo character positions)
        self.digit_trans = {}
        for d in range(10):
            self.digit_trans[48+d] = unichr(0xF643 + d)
        
        self.sc_trans_bembo = {}
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
            self.sc_trans_bembo[65+d] = unichr(0xE004 + offset)
            self.sc_trans_bembo[97+d] = unichr(0xE004 + offset)


class LetterContents(object):
    """
    Contents of a single letter.
    """
    def __init__(self, to_addr_lines, from_name_lines, date=None, salutation="To whom it may concern", closing="Sincerely"):
        self.date = date or datetime.date.today()
        self.salutation = salutation
        self.closing = closing
        self.paragraphs = []
        self.to_addr_lines = to_addr_lines
        self.from_name_lines = from_name_lines
        
    def add_paragraph(self, text):
        "Add a paragraph (represented as a string) to the letter: used by OfficialLetter.add_letter"
        self.paragraphs.append(text)

    def add_paragraphs(self, paragraphs):
        "Add a list of paragraphs (strings) to the letter"
        self.paragraphs.extend(paragraphs)
    
    def _contents(self, letter):
        "Builds of contents that can be added to a letter"
        contents = []
        space_height = letter.line_height
        style = letter.content_style

        contents.append(Paragraph(self.date.strftime('%B %d, %Y').replace(' 0', ' '), style))
        contents.append(Spacer(1, space_height))
        contents.append(NextPageTemplate(1)) # switch to non-letterhead on next page
        
        for line in self.to_addr_lines:
            contents.append(Paragraph(line, style))
        contents.append(Spacer(1, 2*space_height))
        contents.append(Paragraph(self.salutation+",", style))
        contents.append(Spacer(1, space_height))
        
        for line in self.paragraphs[:-1]:
            # last paragraph is put in the KeepTogether below, to prevent bad page break
            contents.append(Paragraph(line, style))
            contents.append(Spacer(1, space_height))
        
        close = []
        close.append(Paragraph(self.paragraphs[-1], style))
        close.append(Spacer(1, 2*space_height))
        close.append(Paragraph(self.closing+",", style))
        close.append(Spacer(1, 36))
        for line in self.from_name_lines:
            close.append(Paragraph(line, style))
        
        contents.append(KeepTogether(close))
        contents.append(NextPageTemplate(0)) # next letter starts on letterhead again
        contents.append(PageBreak())
        
        return contents
