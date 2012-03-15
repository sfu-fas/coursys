from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Spacer, Frame, KeepTogether, Flowable, NextPageTemplate, PageBreak, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import textobject
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont  
from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_JUSTIFY
import os, datetime
from dashboard.models import Signature

PAPER_SIZE = letter
black = CMYKColor(0, 0, 0, 1)
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
        c.setFont('Helvetica', 12)
        c.setFillColor(doc.sfu_red)
        self._drawStringLeading(c, self.lr_margin + 6, 0.5*inch, u'Simon Fraser University'.translate(doc.sc_trans_bembo), charspace=1.4)
        c.setFont('Helvetica', 6)
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
        c.setFont('Helvetica', 12)
        c.setFillColor(doc.sfu_blue)
        parent = self.unit.parent
        if parent.label == 'UNIV':
            # faculty-level unit: just the unit name
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.375*inch, self.unit.name.translate(doc.sc_trans_bembo), charspace=1.2)
        else:
            # department with faculty above it: display both
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.325*inch, self.unit.name.translate(doc.sc_trans_bembo), charspace=1.2)
            c.setFillColor(doc.sfu_grey)
            c.setFont('Helvetica', 8.5)
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.48*inch, parent.name, charspace=0.3)

        # address block
        addr_style = ParagraphStyle(name='Normal',
                                      fontName='Helvetica',
                                      fontSize=10,
                                      leading=10,
                                      textColor=doc.sfu_grey)
        self._put_lines(doc, c, self.unit.address(), 2*inch, self.pg_h - self.top_margin - 0.75*inch, 2.25*inch, addr_style, 8, 1.5)

        # phone numbers block
        lines = [u'Tel'.translate(doc.sc_trans_bembo) + ' ' + self.unit.tel().replace('-', '.')]
        if self.unit.fax():
            lines.append(u'Fax'.translate(doc.sc_trans_bembo) + ' ' + self.unit.fax().replace('-', '.'))
        self._put_lines(doc, c, lines, 4.5*inch, self.pg_h - self.top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)

        # web and email block
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
        ttfFile = os.path.join(media_path, 'Helvetica.ttf')
        #pdfmetrics.registerFont(TTFont("Helvetica", ttfFile))  
        ttfFile = os.path.join(media_path, 'Helvetica.ttf')
        #pdfmetrics.registerFont(TTFont("Helvetica", ttfFile))  
        self.logofile = os.path.join(media_path, 'logo.png')
        
        # graphic standards colours
        self.sfu_red = CMYKColor(0, 1, 0.79, 0.2)
        self.sfu_grey = CMYKColor(0, 0, 0.15, 0.82)
        self.sfu_blue = CMYKColor(1, 0.68, 0, 0.12)
        
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
    
    to_addr_lines: the lines of the recipient's address (list of strings)
    from_name_lines: the sender's name (and title, etc) (list of strings)
    date: sending date of the letter (datetime.date object)
    saluations: letter's salutation (string)
    closing: letter's closing (string)
    signer: person signing the letter, if knows (a coredata.models.Person)
    """
    def __init__(self, to_addr_lines, from_name_lines, date=None, salutation="To whom it may concern",
                 closing="Yours truly", signer=None, paragraphs=None):
        self.date = date or datetime.date.today()
        self.salutation = salutation
        self.closing = closing
        self.flowables = []
        self.to_addr_lines = to_addr_lines
        self.from_name_lines = from_name_lines
        self.signer = signer
        if paragraphs:
            self.add_paragraphs(paragraphs)
        
        # styles
        self.line_height = 13
        self.content_style = ParagraphStyle(name='Normal',
                                      fontName='BemboMTPro',
                                      fontSize=12,
                                      leading=self.line_height,
                                      allowWidows=0,
                                      allowOrphans=0,
                                      alignment=TA_JUSTIFY,
                                      textColor=black)
        
    def add_paragraph(self, text):
        "Add a paragraph (represented as a string) to the letter: used by OfficialLetter.add_letter"
        self.flowables.append(Paragraph(text, self.content_style))

    def add_paragraphs(self, paragraphs):
        "Add a list of paragraphs (strings) to the letter"
        self.flowables.extend([Paragraph(text, self.content_style) for text in paragraphs])
    
    def _contents(self, letter):
        "Builds of contents that can be added to a letter"
        contents = []
        space_height = self.line_height
        style = self.content_style

        contents.append(Paragraph(self.date.strftime('%B %d, %Y').replace(' 0', ' '), style))
        contents.append(Spacer(1, space_height))
        contents.append(NextPageTemplate(1)) # switch to non-letterhead on next page
        
        for line in self.to_addr_lines:
            contents.append(Paragraph(line, style))
        contents.append(Spacer(1, 2*space_height))
        contents.append(Paragraph(self.salutation+",", style))
        contents.append(Spacer(1, space_height))
        
        for f in self.flowables[:-1]:
            # last paragraph is put in the KeepTogether below, to prevent bad page break
            contents.append(f)
            contents.append(Spacer(1, space_height))
        
        # closing block (kept together on one page)
        close = []
        close.append(self.flowables[-1])
        close.append(Spacer(1, 2*space_height))
        close.append(Paragraph(self.closing+",", style))
        # signature
        if self.signer:
            import PIL
            try:
                sig = Signature.objects.get(user=self.signer)
                sig.sig.open()
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                wid = width / float(sig.resolution) * inch
                hei = height / float(sig.resolution) * inch
                sig.sig.open()
                img = Image(sig.sig, width=wid, height=hei)
                img.hAlign = 'LEFT'
                close.append(Spacer(1, space_height))
                close.append(img)
            except Signature.DoesNotExist:
                close.append(Spacer(1, 4*space_height))
        else:
            close.append(Spacer(1, 4*space_height))
        
        for line in self.from_name_lines:
            close.append(Paragraph(line, style))
        
        contents.append(KeepTogether(close))
        contents.append(NextPageTemplate(0)) # next letter starts on letterhead again
        contents.append(PageBreak())
        
        return contents
