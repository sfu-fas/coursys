from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Spacer, Frame, KeepTogether, Flowable, NextPageTemplate, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import textobject
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont  
from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_JUSTIFY
import os

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
            if line == '':
                p = Spacer(1, font_size)
            else:
                #print dir(doc)
                line = unicode(line).translate(doc.digit_trans)
                p = Paragraph(line, style)
            _,h = p.wrap(width, 1*inch)
            p.drawOn(canvas, x, ypos-h)
            ypos -= h + leading

    def beforeDrawPage(self, c, doc):
        "Draw the letterhead before anything else"
        # non-first pages only get the footer, not the header
        self._draw_footer(c, doc)

    def _draw_header(self, c, doc):
        """
        Draw the top-of-page part of the letterhead (used only on first page of letter)
        """
        # SFU logo
        c.drawImage(doc.logofile, x=self.lr_margin + 6, y=self.pg_h-self.top_margin-0.5*inch, width=1*inch, height=0.5*inch)

        # unit text
        c.setFont('BemboMTPro', 12)
        c.setFillColor(doc.sfu_blue)
        self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.375*inch, u'School of Computing Science'.translate(doc.sc_trans_bembo), charspace=1.2)

        # address blocks
        addr_style = ParagraphStyle(name='Normal',
                                      fontName='BemboMTPro',
                                      fontSize=10,
                                      leading=10,
                                      textColor=doc.sfu_grey)
        lines = ['9971 Applied Sciences Building', '8888 University Drive, Burnaby, BC', 'Canada V5A 1S6']
        self._put_lines(doc, c, lines, 2*inch, self.pg_h - self.top_margin - 0.75*inch, 2.25*inch, addr_style, 8, 1.5)
        lines = [u'Tel'.translate(doc.sc_trans_bembo) + ': 778-782-4277', u'Fax'.translate(doc.sc_trans_bembo) + ': 778-782-3045']
        self._put_lines(doc, c, lines, 4.5*inch, self.pg_h - self.top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)
        lines = ['csdept@cs.sfu.ca', 'www.cs.sfu.ca']
        self._put_lines(doc, c, lines, 6.25*inch, self.pg_h - self.top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)
        
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
    def beforeDrawPage(self, c, doc):
        "Draw the letterhead before anything else"
        self._draw_header(c, doc)
        self._draw_footer(c, doc)

    def _create_frame(self, pagesize):
        frame = Frame(self.lr_margin, inch, self.para_width, self.pg_h-3*inch)
        return frame

class UseLetterhead(Flowable):
    def draw(self):
        x = self._frame
        print x
        print dir(x)


class OfficialLetter(BaseDocTemplate):
    """
    Template for a letter on letterhead.
    
    Implements "2009" version of letterhead in SFU graphic design specs: http://www.sfu.ca/clf/downloads.html
    """
    def __init__(self, filename, pagesize=PAPER_SIZE, *args, **kwargs):
        self._media_setup()
        kwargs['pagesize'] = pagesize
        kwargs['pageTemplates'] = [LetterheadTemplate(pagesize=pagesize), LetterPageTemplate(pagesize=pagesize)]
        BaseDocTemplate.__init__(self, filename, *args, **kwargs)
    
    def build_contents(self):
        # contents for testing
        import datetime
        date = datetime.date.today()
        to_addr_lines = ['Some Person', '123 Fake St', 'Vancouver, BC, Canada']
        salutation = "Dear Mr. Person,"
        closing = "Sincerely,"
        from_name_lines = ['Greg Baker', 'Lecturer, School of Computing Science']
        import random
        lengths = [random.randint(10,80) for _ in range(random.randint(5,50))]
        paragraphs = ["Paragraph "*l for l in lengths]

        contents = []
        space_height = 12
                
        contents.append(Paragraph(date.strftime('%B %d, %Y'), self.content_style))
        contents.append(Spacer(1, space_height))
        contents.append(NextPageTemplate(1)) # switch to non-letterhead on next page
        
        for line in to_addr_lines:
            contents.append(Paragraph(line, self.content_style))
        contents.append(Spacer(1, 2*space_height))
        contents.append(Paragraph(salutation, self.content_style))
        contents.append(Spacer(1, space_height))
        
        for line in paragraphs[:-1]:
            # last paragraph is put in the KeepTogether below, to prevent bad page break
            contents.append(Paragraph(line, self.content_style))
            contents.append(Spacer(1, space_height))
        
        close = []
        close.append(Paragraph(paragraphs[-1], self.content_style))
        close.append(Spacer(1, 2*space_height))
        close.append(Paragraph(closing, self.content_style))
        close.append(Spacer(1, 36))
        for line in from_name_lines:
            close.append(Paragraph(line, self.content_style))
        
        contents.append(KeepTogether(close))
        contents.append(NextPageTemplate(0)) # next letter starts on letterhead again
        contents.append(PageBreak())
        
        return contents

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
        self.content_style = ParagraphStyle(name='Normal',
                                      fontName='BemboMTPro',
                                      fontSize=12,
                                      leading=12,
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

