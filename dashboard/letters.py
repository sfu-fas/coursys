"""
All of the system's PDF generation lives here.

It's just easier that way: so many imports and commonalities between these chunks of code,
even though they serve very different parts of the overall system.
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import Flowable, Paragraph, Spacer, Frame, KeepTogether, NextPageTemplate, PageBreak, Image, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import textobject, canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from coredata.models import Role
from django.conf import settings
import os
import datetime, decimal
from dashboard.models import Signature
from coredata.models import Semester, Person
from grad.models import STATUS_APPLICANT
from courselib.branding import product_name
from ra.forms import CS_CONTACT, ENSC_CONTACT, SEE_CONTACT, MSE_CONTACT, FAS_CONTACT
import iso8601;
from textwrap import wrap

PAPER_SIZE = letter
black = CMYKColor(0, 0, 0, 1)
white = CMYKColor(0, 0, 0, 0)
media_path = os.path.join(settings.BASE_DIR, 'external', 'sfu')
logofile = os.path.join(media_path, 'logo.png')

from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate

class SFUMediaMixin():
    def _media_setup(self):
        "Get all of the media needed for the letterhead"
        # fonts and logo
        ttfFile = os.path.join(media_path, 'BemboMTPro-Regular.ttf')
        pdfmetrics.registerFont(TTFont("BemboMTPro", ttfFile))
        ttfFile = os.path.join(media_path, 'BemboMTPro-Bold.ttf')
        pdfmetrics.registerFont(TTFont("BemboMTPro-Bold", ttfFile))
        ttfFile = os.path.join(media_path, 'DINPro-Regular.ttf')
        pdfmetrics.registerFont(TTFont("DINPro", ttfFile))
        ttfFile = os.path.join(media_path, 'DINPro-Bold.ttf')
        pdfmetrics.registerFont(TTFont("DINPro-Bold", ttfFile))

        # graphic standards colours
        self.sfu_red = CMYKColor(0, 1, 0.79, 0.2)
        self.sfu_grey = CMYKColor(0, 0, 0.15, 0.82)
        self.sfu_blue = CMYKColor(1, 0.68, 0, 0.12)

        # translate digits to old-style numerals (in their Bembo character positions)
        self.digit_trans = {}
        for d in range(10):
            self.digit_trans[48+d] = chr(0xF643 + d)

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
            self.sc_trans_bembo[65+d] = chr(0xE004 + offset)
            self.sc_trans_bembo[97+d] = chr(0xE004 + offset)

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


class LetterPageTemplate(PageTemplate, SFUMediaMixin):
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

    def _put_lines(self, doc, canvas, lines, x, y, width, style, font_size, leading):
        """
        Place these lines, with given leading
        """
        ypos = y
        for line in lines:
            line = str(line).translate(doc.digit_trans)
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
        self._drawStringLeading(c, self.lr_margin + 6, 0.5*inch, 'Simon Fraser University'.translate(doc.sc_trans_bembo), charspace=1.4)
        c.setFont('DINPro', 6)
        c.setFillColor(doc.sfu_grey)
        self._drawStringLeading(c, 3.15*inch, 0.5*inch, 'Engaging the World'.upper(), charspace=2)


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
        c.drawImage(logofile, x=self.lr_margin + 6, y=self.pg_h-self.top_margin-0.5*inch, width=1*inch, height=0.5*inch)

        # unit text
        c.setFont('BemboMTPro', 12)
        c.setFillColor(doc.sfu_blue)
        parent = self.unit.parent
        if not parent or parent.label == 'UNIV':
            # faculty-level unit: just the unit name
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.375*inch, self.unit.name.translate(doc.sc_trans_bembo), charspace=1.2)
        else:
            # department with faculty above it: display both
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.325*inch, self.unit.name.translate(doc.sc_trans_bembo), charspace=1.2)
            c.setFillColor(doc.sfu_grey)
            c.setFont('BemboMTPro', 8.5)
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.48*inch, parent.name, charspace=0.3)

        # address block
        addr_style = ParagraphStyle(name='Normal',
                                      fontName='BemboMTPro',
                                      fontSize=10,
                                      leading=10,
                                      textColor=doc.sfu_grey)
        self._put_lines(doc, c, self.unit.address(), 2*inch, self.pg_h - self.top_margin - 0.75*inch, 2.25*inch, addr_style, 8, 1.5)

        # phone numbers block
        lines = ['Tel'.translate(doc.sc_trans_bembo) + ' ' + self.unit.tel().replace('-', '.')]
        if self.unit.fax():
            lines.append('Fax'.translate(doc.sc_trans_bembo) + ' ' + self.unit.fax().replace('-', '.'))
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


class OfficialLetter(BaseDocTemplate, SFUMediaMixin):
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



class LetterContents(object):
    """
    Contents of a single letter.

    to_addr_lines: the lines of the recipient's address (list of strings)
    from_name_lines: the sender's name (and title, etc) (list of strings)
    date: sending date of the letter (datetime.date object)
    closing: letter's closing (string)
    signer: person signing the letter, if knows (a coredata.models.Person)
    """
    def __init__(self, to_addr_lines, from_name_lines, extra_from_name_lines=None, extra_signature_prompt=None, date=None,
                 closing="Yours truly", signer=None, paragraphs=None, cosigner_lines=None, use_sig=True,
                 body_font_size=None, cc_lines=None):
        self.date = date or datetime.date.today()
        self.closing = closing
        self.flowables = []
        self.to_addr_lines = to_addr_lines
        self.from_name_lines = from_name_lines
        self.extra_from_name_lines = extra_from_name_lines
        self.extra_signature_prompt = extra_signature_prompt
        self.cosigner_lines = cosigner_lines
        self.signer = signer
        self.use_sig = use_sig
        if cc_lines:
            self.cc_lines = [cc for cc in cc_lines if cc.strip()]
        else:
            self.cc_lines = None
        if paragraphs:
            self.add_paragraphs(paragraphs)

        # styles
        self.line_height = (body_font_size or 12) + 1
        self.content_style = ParagraphStyle(name='Normal',
                                            fontName='BemboMTPro',
                                            fontSize=body_font_size or 12,
                                            leading=self.line_height,
                                            allowWidows=0,
                                            allowOrphans=0,
                                            alignment=TA_JUSTIFY,
                                            textColor=black)
        self.table_style = TableStyle([
                    ('FONT', (0,0), (-1,-1), 'BemboMTPro', 12, self.line_height),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ])

    def add_paragraph(self, text):
        "Add a paragraph (represented as a string) to the letter: used by OfficialLetter.add_letter"
        if text.startswith('||'):
            # it's our table microformat
            lines = text.split('\n')
            cells = [line.split('|')[2:] for line in lines] # [2:] effectively strips the leading '||'
            self.flowables.append(Table(cells, style=self.table_style))
        else:
            [self.flowables.append(Paragraph(line, self.content_style)) for line in text.split("\n")]
        self.flowables.append(Spacer(1, self.line_height))

    def add_paragraphs(self, paragraphs):
        "Add a list of paragraphs (strings) to the letter"
        [self.add_paragraph(paragraph) for paragraph in paragraphs]

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
        contents.append(Spacer(1, space_height))

        for f in self.flowables[:-2]:
            # last paragraph is put in the KeepTogether below, to prevent bad page break
            contents.append(f)

        # closing block (kept together on one page)
        close = []
        close.append(self.flowables[-2])
        close.append(Spacer(1, 2*space_height))
        # signature
        signature = [Paragraph(self.closing+",", style)]
        img = None
        if self.signer and self.use_sig:
            import PIL
            try:
                sig = Signature.objects.get(user=self.signer)
                sig.sig.open('rb')
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                wid = width / float(sig.resolution) * inch
                hei = height / float(sig.resolution) * inch
                sig.sig.open('rb')
                img = Image(sig.sig, width=wid, height=hei)
                img.hAlign = 'LEFT'
                signature.append(Spacer(1, space_height))
                signature.append(img)
            except Signature.DoesNotExist:
                signature.append(Spacer(1, 4*space_height))
        else:
            signature.append(Spacer(1, 4*space_height))

        for line in self.from_name_lines:
            signature.append(Paragraph(line, style))

        if self.extra_from_name_lines:
            signature.append(Spacer(1, 4*space_height))
            for line in self.extra_from_name_lines:
                signature.append(Paragraph(line, style))

        if self.cosigner_lines:
            # we have two signatures to display: rebuild the signature part in a table with both
            data = []
            data.append([Paragraph(self.closing+",", style), Paragraph(self.cosigner_lines[0]+",", style)])
            if self.extra_signature_prompt:
                data.append(["", Paragraph(self.extra_signature_prompt, style)])
            if img:
                data.append([img, Spacer(1, 4*space_height)])
            else:
                data.append([Spacer(1, 4*space_height), Spacer(1, 4*space_height)])
            
            extra = [''] * (len(self.from_name_lines) + len(self.cosigner_lines[1:]))

            for l1,l2 in zip(self.from_name_lines+extra, self.cosigner_lines[1:]+extra):
                if l1 or l2:
                    data.append([Paragraph(l1, style), Paragraph(l2, style)])

            if self.extra_from_name_lines:
                data.append([Spacer(1, 4*space_height), Spacer(1, 4*space_height)])
                for line in self.extra_from_name_lines:
                    data.append([Paragraph(line, style), ''])

            sig_table = Table(data)
            sig_table.setStyle(TableStyle(
                    [('LEFTPADDING', (0,0), (-1,-1), 0),
                     ('RIGHTPADDING', (0,0), (-1,-1), 0),
                     ('TOPPADDING', (0,0), (-1,-1), 0),
                     ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))

            close.append(sig_table)
        else:
            close.extend(signature)

        # the CC lines
        if self.cc_lines:
            close.append(Spacer(1, space_height))
            data = []
            for cc in self.cc_lines:
                data.append(['', Paragraph(cc, self.content_style)])

            cc = Paragraph('cc:', self.content_style)
            data[0][0] = cc

            cc_table = Table(data, colWidths=[0.3 * inch, 5 * inch])
            cc_table.hAlign = "LEFT"
            cc_table.setStyle(TableStyle(
                [('LEFTPADDING', (0, 0), (-1, -1), 0),
                 ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                 ('TOPPADDING', (0, 0), (-1, -1), 0),
                 ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))

            close.append(cc_table)

        contents.append(KeepTogether(close))
        contents.append(NextPageTemplate(0)) # next letter starts on letterhead again
        contents.append(PageBreak())

        return contents

class MemoHead(Flowable, SFUMediaMixin):
    """
    A flowable styled like a SFU memo header line
    """
    def __init__(self, xoffset=0, width=None, key='', value='', bold=False, keywidth=1*inch):
        self.key = key
        self.value = value
        self.keyfont = 'DINPro-Bold' if bold else 'DINPro'
        self.xoffset = xoffset
        self.keywidth = keywidth
        self.width = width
        self.height = 24
        self._media_setup()

    def wrap(self, availWidth, availHeight):
        if not self.width:
            self.width = availWidth - self.xoffset - 1*inch
        return (self.xoffset, self.height)

    def draw(self):
        c = self.canv
        c.setLineWidth(0.5)
        c.setStrokeColor(black)
        p = c.beginPath()
        p.moveTo(self.xoffset, 11)
        p.lineTo(self.xoffset, 0)
        p.lineTo(self.xoffset + self.width, 0)
        c.drawPath(p)

        c.setFont(self.keyfont, 8)
        self._drawStringLeading(c, self.xoffset + 5, 4, self.key.upper(), charspace=1 )
        c.setFont('BemboMTPro', 12)
        c.drawString(self.xoffset + self.keywidth, 4, self.value)

class MemoContents(LetterContents):
    def __init__(self, subject, **kwargs):
        self.subject = subject
        super(MemoContents, self).__init__(**kwargs)

    def _contents(self, memo):
        """
        Produce a list of Flowables to form the body of the memo
        """
        contents = []
        space_height = self.line_height
        # the header block
        contents.append(MemoHead(key='Attention', value=', '.join(self.to_addr_lines), bold=True))
        contents.append(MemoHead(key='From', value=', '.join(self.from_name_lines)))
        contents.append(MemoHead(key='Re', value=self.subject[0]))
        for subjectline in self.subject[1:]:
            contents.append(MemoHead(key='', value=subjectline))
        contents.append(MemoHead(key='Date', value=self.date.strftime('%B %d, %Y').replace(' 0', ' ')))
        contents.append(Spacer(1, 2*space_height))

        # insert each paragraph
        for f in self.flowables:
            contents.append(f)
            #contents.append(Spacer(1, space_height))

        # the CC lines
        if self.cc_lines:
            data = []
            for cc in self.cc_lines:
                data.append(['', Paragraph(cc, self.content_style)])

            cc = Paragraph('cc:', self.content_style)
            data[0][0] = cc

            cc_table = Table(data, colWidths=[0.3 * inch, 5 * inch])
            cc_table.hAlign = "LEFT"
            cc_table.setStyle(TableStyle(
                [('LEFTPADDING', (0, 0), (-1, -1), 0),
                 ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                 ('TOPPADDING', (0, 0), (-1, -1), 0),
                 ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))

            contents.append(cc_table)
        return contents


class FASLetterPageTemplate(PageTemplate, SFUMediaMixin):
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

    def _put_lines(self, doc, canvas, lines, x, y, width, style, font_size, leading):
        """
        Place these lines, with given leading
        """
        ypos = y
        for line in lines:
            line = str(line).translate(doc.digit_trans)
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
        c.setFont('DINPro-Bold', 8)
        c.setFillColor(doc.sfu_red)
        self._drawStringLeading(c, 2*inch, 0.5*inch, "Canada's Engaged University".upper(), charspace=0)


class FASLetterheadTemplate(FASLetterPageTemplate):
    def __init__(self, *args, **kwargs):
        FASLetterPageTemplate.__init__(self, *args, **kwargs)
        self.faculty = "FACULTY OF APPLIED SCIENCES"
        self.address = ['Applied Science Building 9861', '8888 University Drive', 'Burnaby, B.C. Canada V5A 1S6']
        self.tel = "+1 778 782 4724"
        self.fax = "+1 778 782 5802"
        self.web = "www.sfu.ca/fas"

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
        c.drawImage(logofile, x=self.lr_margin + 6, y=self.pg_h-self.top_margin-0.5*inch, width=1*inch, height=0.5*inch)

        # unit text
        c.setFont('BemboMTPro', 12)
        c.setFillColor(doc.sfu_grey)
        # department with faculty above it: display both
        self._drawStringLeading(c, 1.9*inch, self.pg_h - self.top_margin - 0.325*inch, "Simon Fraser".translate(doc.sc_trans_bembo), charspace=1.2)
        self._drawStringLeading(c, 1.9*inch, self.pg_h - self.top_margin - 0.465*inch, "University".translate(doc.sc_trans_bembo), charspace=1.2)

        # address block
        addr_style = ParagraphStyle(name='Normal',
                                      fontName='BemboMTPro',
                                      fontSize=10,
                                      leading=10,
                                      textColor=doc.sfu_grey)

        # faculty and web
        lines = [self.faculty, self.web]
        self._put_lines(doc, c, lines, 6*inch, self.pg_h - self.top_margin, 2.25*inch, addr_style, 8, 1.5)

        # address
        self._put_lines(doc, c, self.address, 6*inch, self.pg_h - self.top_margin - 0.5*inch, 2.25*inch, addr_style, 8, 1.5)

        # phone numbers
        lines = ['Tel'.translate(doc.sc_trans_bembo) + ' ' + self.tel]
        lines.append('Fax'.translate(doc.sc_trans_bembo) + ' ' + self.fax.replace('-', '.'))
        self._put_lines(doc, c, lines, 6*inch, self.pg_h - self.top_margin - 1.125*inch, 1.5*inch, addr_style, 8, 1.5)


class FASOfficialLetter(BaseDocTemplate, SFUMediaMixin):
    """
    Template for a letter on letterhead.

    Implements "2009" version of letterhead in SFU graphic design specs: http://www.sfu.ca/clf/downloads.html
    """
    def __init__(self, filename, pagesize=PAPER_SIZE, *args, **kwargs):
        self._media_setup()
        kwargs['pagesize'] = pagesize
        kwargs['pageTemplates'] = [FASLetterheadTemplate(pagesize=pagesize), FASLetterPageTemplate(pagesize=pagesize)]
        BaseDocTemplate.__init__(self, filename, *args, **kwargs)
        self.contents = [] # to be a list of Flowables

    def add_letter(self, letter):
        "Add the given LetterContents object to this document"
        self.contents.extend(letter._contents(self))

    def write(self):
        "Write the PDF contents out"
        self.build(self.contents)
        

class RARequestForm(SFUMediaMixin):
    MAIN_WIDTH = 8*inch # size of the main box
    ENTRY_FONT = "Helvetica-Bold"
    NOTE_STYLE = ParagraphStyle(name='Normal',
                                fontName=ENTRY_FONT,
                                fontSize=9,
                                leading=11,
                                alignment=TA_LEFT,
                                textColor=black)

    def __init__(self, ra, config):
        self.ra = ra
        self.config = config
        self._media_setup()

    def _circle_checkbox(self, x, y, text="", filled=0, leading=0):
        self.c.circle(x+1.5*mm, y+1.5*mm, 2.5*mm, stroke=1, fill=filled)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(x+5*mm, y+0.5*mm+leading, text)

    def _checkbox(self, x, y, text="", filled=0, leading=0):
        self.c.rect(x+1*mm, y+0.5*mm, 2.5*mm, 2.5*mm, fill=filled)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(x+5*mm, y+0.5*mm+leading, text)

    def _large_checkbox(self, x, y, text="", filled=0, leading=0):
        self.c.rect(x+1*mm, y+0.5*mm, 5*mm, 5*mm, fill=filled)
        self.c.setFont("Helvetica", 10)
        self.c.drawString(x+7*mm, y+1.5*mm+leading, text)

    def _box_entry(self, x, y, width, height, content=None):
        self.c.setLineWidth(1)
        self.c.rect(x, y, width, height)
        if content:
            self.c.setFont(self.ENTRY_FONT, 9)
            self.c.drawString(x+2*mm, y+height-3.5*mm, content)

    def _small_box_entry(self, x, y, width, height, content=None):
        self.c.setLineWidth(1)
        self.c.rect(x, y, width, height)
        if content:
            self.c.setFont(self.ENTRY_FONT, 6)
            self.c.drawString(x+1.5*mm, y+height-3*mm, content)

    def draw_pdf(self, outfile):
        """
        Generates PDF in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)
        self.c.setStrokeColor(black)

        self.c.translate(6*mm, 16*mm) # origin = bottom-left of the content
        self.c.setStrokeColor(black)
        self.c.setLineWidth(1)

        # Top right box
        self.c.setFillColor(self.sfu_red)
        self.c.rect(x=170*mm, y=247*mm, width=26*mm, height=7*mm, stroke=1, fill=1)

        # SFU logo
        self.c.setStrokeColor(black)
        self.c.drawImage(logofile, x=0, y=247*mm, width=20*mm, height=10*mm)
        self.c.setFont('BemboMTPro', 10)
        self.c.setFillColor(self.sfu_red)
        self._drawStringLeading(self.c, 23*mm, 250*mm, 'Simon Fraser University'.translate(self.sc_trans_bembo), charspace=1.4)
        self.c.setFont('DINPro', 5)
        self.c.setFillColor(self.sfu_grey)
        self._drawStringLeading(self.c, 23*mm, 247.5*mm, 'Engaging the World'.upper(), charspace=2)
        self.c.setFillColor(black)

        # form header
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawCentredString(self.MAIN_WIDTH/2, 243*mm, "Payroll Appointment Form (PAF): For Non-Affiliated Temporary Appointments")
        self.c.drawString(55.5*mm, 239*mm, "***ONLY")
        self.c.setFillColor(self.sfu_red)
        self.c.drawString(69*mm, 239*mm, " COMPLETED ")
        self.c.setFillColor(black)
        self.c.drawString(93*mm, 239*mm, "FORMS WILL BE PROCESSED***")
        self.c.setFont("Helvetica-Bold", 8)
        self.c.setFillColor(CMYKColor(0.86, 0.86, 0, 0)) # blue text
        self.c.drawCentredString(self.MAIN_WIDTH/2, 234.5*mm, "***For research employees, see How to complete the PAF and complete page 2 of this form***")
        self.c.drawCentredString(self.MAIN_WIDTH/2, 231*mm, "For all other appointments, please see payroll guide for the completion of Payroll Appointment Form (pp4)")
        self.c.setFillColor(black)

        # type of change
        self.c.setFont("Helvetica-Bold", 10)
        appointment_type = self.config['appointment_type']
        self._circle_checkbox(1*mm, 222*mm, text="Appointment/Re-appointment", filled=(appointment_type=='AP'))
        self._circle_checkbox(48*mm, 222*mm, text="Extension", filled=(appointment_type=='EX'))
        self._circle_checkbox(74*mm, 222*mm, text="Early End", filled=(appointment_type=='EE'))
        self._circle_checkbox(100*mm, 222*mm, text="Funding Change Only", filled=(appointment_type=='FC'))
        self._circle_checkbox(139*mm, 222*mm, text="Correction/Update", filled=(appointment_type=='CO'))
        self._circle_checkbox(175*mm, 222*mm, text="Lump Sum", filled=(appointment_type=='LS'))

        # type of employee checkboxes
        self.c.rect(0, 197*mm, 145*mm, 20*mm)
        self.c.rect(145*mm, 197*mm, 57*mm, 20*mm)

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(2*mm, 212*mm, "EMPLOYMENT")
        self.c.drawString(150*mm, 212*mm, "SCHOLARSHIP")

        cat = self.ra.hiring_category
        research_assistant = (cat=="RA")
        non_continuing = (cat=="NC")
        graduate_research_assistant = (cat=="GRAS")
        self.c.setFont("Helvetica", 7)
        self._checkbox(1.5*mm, 206*mm, text="Research Assistant", filled=research_assistant)
        self._checkbox(1.5*mm, 201*mm, text="Research Support", filled=False)
        self._checkbox(100*mm, 206*mm, text="Other Non-Continuing", filled=non_continuing)
        self._checkbox(50*mm, 201*mm, text="Lump Sum: Postdoctoral Fellow", filled=False)
        self._checkbox(50*mm, 206*mm, text="Recreation Services Staff", filled=False)

        self._checkbox(150*mm, 206*mm, text="Graduate Scholarship", filled=graduate_research_assistant)
        self._checkbox(150*mm, 201*mm, text="National Scholarship", filled=False)

        # bc employment 
        self.c.setLineWidth(0.3)
        self.c.linkURL('https://www2.gov.bc.ca/gov/content/employment-business/employment-standards-advice/employment-standards/forms-resources/igm', (2*mm, 200.5*mm, 24*mm, 200*mm), relative=1)
        self.c.line(1*mm, 198.8*mm, 25.5*mm, 198.8*mm)
        self.c.linkURL('http://www.sfu.ca/policies.html', (2*mm, 200*mm, 22.5*mm, 199*mm), relative=1)
        self.c.line(1*mm, 198.8*mm - 4, 21*mm, 198.8*mm - 4)
        self.c.setFont("Helvetica", 3.25)
        self.c.drawString(1*mm, 199*mm, "BC’S EMPLOYMENT STANDARDS ACT (ESA) PROVIDES EMPLOYERS AND EMPLOYEES WITH GUIDELINES TO ENSURE THE CONSISTENT AND LEGAL APPLICATION OF EMPLOYMENT PRACTICES AND EMPLOYEE RIGHTS. REFER TO THE ESA WEBSITE AND ")
        self.c.drawString(1*mm, 199*mm - 4, "SFU’S POLICIES AND PROCEDURES FOR FACTS AND PROCEDURAL INFORMATION. NOTE THAT CERTAIN CLAUSES IN COLLECTIVE AGREEMENTS WILL SUPERSEDE LANGUAGE IN THE ESA AND VICE VERSA.")
        self.c.setLineWidth(1)
        
        self.c.setFont("Helvetica-Bold", 10)
        self.c.setFillColor(self.sfu_red)
        self.c.drawString(1*mm, 192*mm, "APPOINTMENT DETAILS")


        self.c.setFillColor(black)
        mi = ''
        email_address = str(self.ra.get_email_address())
        last_name = str(self.ra.get_last_name())
        first_name = str(self.ra.get_first_name())

        if self.ra.nonstudent:
            emplid = 'No ID'
        else:
            emplid = str(self.ra.person.emplid)
            if self.ra.person.middle_name:
                mi = self.ra.person.middle_name[0]

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, 185*mm, "SFU ID")
        self._box_entry(14*mm, 183*mm, 52*mm, 6*mm, content=emplid)
        self.c.drawString(80*mm, 185*mm, "Employee's email address")
        self._box_entry(122*mm, 183*mm, 80*mm, 6*mm, content=email_address)

        # personal/position details
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, 177*mm, "Last Name")
        self.c.drawString(89*mm, 177*mm, "First Name")
        self.c.drawString(180*mm, 177*mm, "Initial")
        self._box_entry(18*mm, 175*mm, 69*mm, 6*mm, content=last_name)
        self._box_entry(106*mm, 175*mm, 71*mm, 6*mm, content=first_name)
        self._box_entry(190*mm, 175*mm, 12*mm, 6*mm, content=mi)

        if self.ra.position_no != None:
            position_no = str(self.ra.position_no)
        else:
            position_no = ''
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, 169*mm, "Department")
        self.c.drawString(75*mm, 169*mm, "Position Title")
        self.c.drawString(153*mm, 169*mm, "Position #")
        self._box_entry(19*mm, 167*mm, 54*mm, 6*mm, content=str(self.ra.unit.informal_name()))
        if len(self.ra.position) > 30:
            self._small_box_entry(95*mm, 167*mm, 56*mm, 6*mm, content=str(self.ra.position))
        else:
            self._box_entry(95*mm, 167*mm, 56*mm, 6*mm, content=str(self.ra.position))
        self._box_entry(168*mm, 167*mm, 34*mm, 6*mm, content=position_no)

        # dates
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, 161*mm, "Effective Date")
        self.c.drawString(77*mm, 161*mm, "End Date")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(7*mm, 159*mm, "YYYY/MM/DD")
        self.c.drawString(79*mm, 159*mm, "YYYY/MM/DD")
        self._box_entry(23*mm, 159*mm, 51*mm, 6*mm, content=str(self.ra.start_date).replace('-', '/'))
        self._box_entry(93*mm, 159*mm, 53*mm, 6*mm, content=str(self.ra.end_date).replace('-', '/'))

        # money
        gras_ls = graduate_research_assistant and (self.ra.gras_payment_method=="LE" or self.ra.gras_payment_method=="LS")
        gras_bw = graduate_research_assistant and self.ra.gras_payment_method=="BW"
        ra_hourly = research_assistant and self.ra.ra_payment_method=="H"
        ra_bw = research_assistant and self.ra.ra_payment_method=="BW"
        nc_hourly = non_continuing and self.ra.nc_payment_method=="H"
        nc_bw = non_continuing and self.ra.nc_payment_method=="BW"
        backdated = self.ra.backdated

        if gras_ls:
            hourly = ''
            biweekly = ''
            biweekhours_hourly = ''
            biweekhours_bw = ''
            lumpsum = "$%.2f" % (self.ra.total_gross)
            lumphours = ''
        elif gras_bw:
            hourly = ''
            biweekly = "$%.2f" % (self.ra.biweekly_salary)
            biweekhours_hourly = ''
            biweekhours_bw = ''
            lumpsum = ''
            lumphours = ''
        elif ra_hourly:
            hourly = "$%.2f" % (self.ra.gross_hourly)
            biweekly = ''
            biweekhours_hourly = "%.2f" % self.ra.biweekly_hours
            biweekhours_bw = ''
            lumpsum = ''
            lumphours = ''
        elif ra_bw:
            hourly = ''
            biweekly = "$%.2f" % (self.ra.biweekly_salary)
            biweekhours_bw = "%.2f" % self.ra.biweekly_hours
            biweekhours_hourly = ''
            lumpsum = ''
            lumphours = ''
        elif nc_hourly:
            hourly = "$%.2f" % (self.ra.gross_hourly)
            biweekly = ''
            biweekhours_bw = ''
            biweekhours_hourly = "%.2f" % self.ra.biweekly_hours
            lumpsum = ''
            lumphours = ''
        elif nc_bw:
            hourly = ''
            biweekly = "$%.2f" % (self.ra.biweekly_salary)
            biweekhours_hourly = ''
            biweekhours_bw = "%.2f" % self.ra.biweekly_hours
            lumpsum = ''
            lumphours = ''
        elif backdated:
            hourly = ''
            biweekly = ''
            biweekhours_hourly = ''
            biweekhours_bw = ''
            lumpsum = "$%.2f" % (self.ra.backdate_lump_sum)
            lumphours =  "%.2f" % self.ra.backdate_hours
        
        # override if lump sum is selected, if not check if hourly
        if appointment_type == "LS":
            hourly = ''
            biweekly = ''
            biweekhours = ''
            lumpsum = "$%.2f" % (self.ra.total_pay)
   

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, 153*mm, "Hourly Rate")
        self.c.drawString(54*mm, 153*mm, "Bi-Weekly Payment Amount")
        self.c.drawString(99*mm, 153*mm, "Lump Sum Adjustment")
        self._box_entry(1.5*mm, 145*mm, 40*mm, 6.5*mm, content=hourly)
        self._box_entry(54.5*mm, 145*mm, 40*mm, 6.5*mm, content=biweekly)
        self._box_entry(99*mm, 145*mm, 40*mm, 6.5*mm, content=lumpsum)

        self.c.drawString(44.5*mm, 153*mm, "OR")

        # hours
        self.c.setFont("Helvetica-Bold", 6)
        self.c.drawString(44*mm, 150*mm, "Do not")
        self.c.drawString(44.5*mm, 148*mm, "enter")
        self.c.drawString(44.5*mm, 146*mm, "both")
        self.c.drawString(140*mm, 149*mm, "Provide reason")
        self.c.drawString(140*mm, 147*mm, "in Comments")

        self.c.drawString(99*mm, 142*mm, "Lump sum hours:")
        self.c.drawString(54*mm, 142*mm, "Hours and minutes (biweekly):")
        self.c.drawString(1*mm, 142*mm, "Hours and minutes (biweekly):")


        self._box_entry(1.5*mm, 134*mm, 40*mm, 6.5*mm, content=biweekhours_hourly)
        self._box_entry(54.5*mm, 134*mm, 40*mm, 6.5*mm, content=biweekhours_bw)
        self._box_entry(99*mm, 134*mm, 40*mm, 6.5*mm, content=lumphours)

        health_benefits = [0,1]       
        if research_assistant and self.ra.ra_benefits == "Y":
            health_benefits = [1,0]

        # health benefits
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(158*mm, 161*mm, "Health Benefits")
        self._checkbox(158*mm, 155*mm, text="Apply eligible benefits", filled=health_benefits[0])
        self._checkbox(158*mm, 151*mm, text="Do not apply eligible benefits", filled=health_benefits[1])

        # employed by sfu
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(158*mm, 145*mm, "Employed by SFU?")
        self._checkbox(158*mm, 139*mm, text="Yes", filled=0)
        self._checkbox(158*mm, 135*mm, text="No, state legal name of employer", filled=0)
        self.c.drawString(163*mm, 132*mm, "and contact details in Comments")

        # comments
        self.c.setFont("Helvetica", 5)
        self._box_entry(1*mm, 113*mm, 201.5*mm, 17.5*mm)
        f = Frame(2*mm, 112.5*mm, 200*mm, 17*mm, 0, 0, 0, 0)

        comments = []
        if backdated or appointment_type == "LS":
            init_comment = "Lump sum amount $" + str(self.ra.total_pay) + ". "
        elif gras_ls:
            init_comment = "Lump sum funding amount $" + str(self.ra.total_pay) + ". "
        elif gras_bw:
            init_comment = "Total funding amount $" + str(self.ra.total_pay) + " over " + str(self.ra.pay_periods) + " pay periods. "
        elif ra_hourly or nc_hourly:
            init_comment = "Expected " + str(self.ra.biweekly_hours) + " hours bi-weekly over " + str(self.ra.pay_periods) + " pay periods plus " + str(self.ra.vacation_pay) + "% vacation pay, total pay $" + str(self.ra.total_pay) + ". "
        elif ra_bw or nc_bw:
            init_comment = "Salary amount $" + str(self.ra.total_pay) + " over " + str(self.ra.pay_periods) + " pay periods. "
        else:
            init_comment = ""
        
        post_comment = ""
        if non_continuing:
            post_comment += "Supervisor: " + str(self.ra.supervisor.name()) + " / Grant signing authority:" 
        comments.append(Paragraph("COMMENTS: " + init_comment + self.ra.paf_comments, style=self.NOTE_STYLE))
        comments.append(Paragraph(post_comment, style=self.NOTE_STYLE))
        f.addFromList(comments, self.c)
        
        self.c.setFillColor(self.sfu_red)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.setStrokeColor(self.sfu_red)
        self.c.line(0, 110.5*mm, self.MAIN_WIDTH, 110.5*mm)
        self.c.drawString(1*mm, 106*mm, "FUNDING DETAILS")
        
        self.c.setStrokeColor(black)
        self.c.setFillColor(black)


        # encumbered hours
        self.c.setFont("Helvetica", 8)
        if graduate_research_assistant:
            encumbered_hours = ''
        elif self.ra.encumbered_hours:
            encumbered_hours = str(self.ra.encumbered_hours)
        else:
            hours = self.ra.get_encumbered_hours()
            if hours == 0:
                encumbered_hours = ''
            else:
                encumbered_hours = str(self.ra.get_encumbered_hours())


        self.c.drawString(1*mm, 102.5*mm, "Estimated total bi-weekly hours to be encumbered for hourly employees:")
        self._box_entry(93*mm, 101.5*mm, 15*mm, 6*mm, content=encumbered_hours)


        # funding sources
        # only three funding sources needed for now, even though there are four spots.
        fs1_project = self.ra.fs1_project
        fs1_fund = str(self.ra.fs1_fund)
        fs1_unit = str(self.ra.fs1_unit)
        fs1_percentage = str(self.ra.fs1_percentage)

        if self.ra.fs1_program != None:
            fs1_program = str(self.ra.fs1_program)
            if fs1_program == "0":
                fs1_program = "00000"
        else:
            fs1_program = ''

        if self.ra.fs1_biweekly_rate != None:
            fs1_biweekly_rate = str(self.ra.fs1_biweekly_rate)
        else:
            fs1_biweekly_rate = ''
        
        if self.ra.object_code != None:
            object_code = str(self.ra.object_code)
        else:
            object_code = ''
        
        
        fs1_object = object_code

        fs2 = self.ra.fs2_option
        fs2_project = ''
        fs2_fund = ''
        fs2_unit = ''
        fs2_percentage = ''
        fs2_biweekly_rate = ''
        fs2_start_date = ''
        fs2_end_date = ''
        fs2_program = ''
        fs2_object = ''

        fs3 = self.ra.fs3_option
        fs3_project = ''
        fs3_fund = ''
        fs3_unit = ''
        fs3_percentage = ''
        fs3_biweekly_rate = ''
        fs3_start_date = ''
        fs3_end_date = ''
        fs3_program = ''
        fs3_object = ''


        if not (fs2 or fs3):
            fs1_start_date = str(self.ra.start_date)
            fs1_end_date = str(self.ra.end_date)
        else:
            fs1_start_date = str(self.ra.fs1_start_date)
            fs1_end_date = str(self.ra.fs1_end_date)

        if fs2:
            fs2_project = self.ra.fs2_project
            fs2_fund = str(self.ra.fs2_fund)
            fs2_unit = str(self.ra.fs2_unit)
            fs2_percentage = str(self.ra.fs2_percentage)
            fs2_biweekly_rate = str(self.ra.fs2_biweekly_rate)
            fs2_start_date = str(self.ra.fs2_start_date)
            fs2_end_date = str(self.ra.fs2_end_date)
            fs2_object = object_code
            if self.ra.fs2_program != None:
                fs2_program = str(self.ra.fs2_program)
                if fs2_program == "0":
                    fs2_program = "00000"
            
        if fs3:
            fs3_project = self.ra.fs3_project
            fs3_fund = str(self.ra.fs3_fund)
            fs3_unit = str(self.ra.fs3_unit)
            fs3_percentage = str(self.ra.fs3_percentage)
            fs3_biweekly_rate = str(self.ra.fs3_biweekly_rate)
            fs3_start_date = str(self.ra.fs3_start_date)
            fs3_end_date = str(self.ra.fs3_end_date)
            fs3_object = object_code
            if self.ra.fs3_program != None:
                fs3_program = str(self.ra.fs3_program)
                if fs3_program == "0":
                    fs3_program = "00000"


        # funding source table

        self._small_box_entry(1*mm, 95*mm, 35*mm, 6*mm, content="Project (6-8 digits, if applicable)")
        self._box_entry(1*mm, 90*mm, 35*mm, 5*mm, content=fs1_project)
        self._box_entry(1*mm, 85*mm, 35*mm, 5*mm, content=fs2_project)
        self._box_entry(1*mm, 80*mm, 35*mm, 5*mm, content=fs3_project)

        self._small_box_entry(36*mm, 95*mm, 20*mm, 6*mm, content="Object (4 digits)")
        self._box_entry(36*mm, 90*mm, 20*mm, 5*mm, content=fs1_object)
        self._box_entry(36*mm, 85*mm, 20*mm, 5*mm, content=fs2_object)
        self._box_entry(36*mm, 80*mm, 20*mm, 5*mm, content=fs3_object)

        self._small_box_entry(56*mm, 95*mm, 19*mm, 6*mm, content="Fund (2 digits)")
        self._box_entry(56*mm, 90*mm, 19*mm, 5*mm, content=fs1_fund)
        self._box_entry(56*mm, 85*mm, 19*mm, 5*mm, content=fs2_fund)
        self._box_entry(56*mm, 80*mm, 19*mm, 5*mm, content=fs3_fund)

        self._small_box_entry(75*mm, 95*mm, 26*mm, 6*mm, content="Department (4 digits)")
        self._box_entry(75*mm, 90*mm, 26*mm, 5*mm, content=fs1_unit)
        self._box_entry(75*mm, 85*mm, 26*mm, 5*mm, content=fs2_unit)
        self._box_entry(75*mm, 80*mm, 26*mm, 5*mm, content=fs3_unit)

        self._small_box_entry(101*mm, 95*mm, 36*mm, 6*mm, content="Program")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(102.5*mm, 96*mm, "(5 digits or use 00000)")
        self._box_entry(101*mm, 90*mm, 36*mm, 5*mm, content=fs1_program)
        self._box_entry(101*mm, 85*mm, 36*mm, 5*mm, content=fs2_program)
        self._box_entry(101*mm, 80*mm, 36*mm, 5*mm, content=fs3_program)

        self._small_box_entry(137*mm, 95*mm, 14*mm, 6*mm, content="% Split")
        self._box_entry(137*mm, 90*mm, 14*mm, 5*mm, content=fs1_percentage)
        self._box_entry(137*mm, 85*mm, 14*mm, 5*mm, content=fs2_percentage)
        self._box_entry(137*mm, 80*mm, 14*mm, 5*mm, content=fs3_percentage)

        self._small_box_entry(151*mm, 95*mm, 17*mm, 6*mm, content="Bi-weekly Rate")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(155*mm, 96*mm, "(if %Split)")
        self._box_entry(151*mm, 90*mm, 17*mm, 5*mm, content=fs1_biweekly_rate)
        self._box_entry(151*mm, 85*mm, 17*mm, 5*mm, content=fs2_biweekly_rate)
        self._box_entry(151*mm, 80*mm, 17*mm, 5*mm, content=fs3_biweekly_rate)

        self._small_box_entry(168*mm, 95*mm, 17*mm, 6*mm, content="Start Date")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(169.5*mm, 96*mm, "(YYYY-MM-DD)")
        self._small_box_entry(168*mm, 90*mm, 17*mm, 5*mm, content=fs1_start_date)
        self._small_box_entry(168*mm, 85*mm, 17*mm, 5*mm, content=fs2_start_date)
        self._small_box_entry(168*mm, 80*mm, 17*mm, 5*mm, content=fs3_start_date)

        self._small_box_entry(185*mm, 95*mm, 17*mm, 6*mm, content="End Date")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(187.5*mm, 96*mm, "(YYYY-MM-DD)")
        self._small_box_entry(185*mm, 90*mm, 17*mm, 5*mm, content=fs1_end_date)
        self._small_box_entry(185*mm, 85*mm, 17*mm, 5*mm, content=fs2_end_date)
        self._small_box_entry(185*mm, 80*mm, 17*mm, 5*mm, content=fs3_end_date)


        # funding change table
        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(1*mm, 77*mm, "If FUNDING CHANGE ONLY, enter current funding information")
        self.c.setFont("Helvetica", 7)
        self._checkbox(3*mm, 71.5*mm, text="Check if requesting transfer of Payroll Actuals, enter the Total Salary Amount to Transfer, and attach the", filled=False)
        self.c.setFont("Helvetica-Bold", 8)
        self.c.setFillColor(CMYKColor(0.7, 0.7, 0, 0)) # blue text
        self.c.drawString(139*mm, 72*mm, "DA Query:")
        self.c.setFillColor(black)
        self._box_entry(154*mm, 71.5*mm, 20*mm, 6*mm, content='')

        self._small_box_entry(1*mm, 65*mm, 35*mm, 6*mm, content="Project (6-8 digits, if applicable)")
        self._box_entry(1*mm, 60*mm, 35*mm, 5*mm, content='')
        self._box_entry(1*mm, 55*mm, 35*mm, 5*mm, content='')
        self._box_entry(1*mm, 50*mm, 35*mm, 5*mm, content='')

        self._small_box_entry(36*mm, 65*mm, 20*mm, 6*mm, content="Object (4 digits)")
        self._box_entry(36*mm, 60*mm, 20*mm, 5*mm, content='')
        self._box_entry(36*mm, 55*mm, 20*mm, 5*mm, content='')
        self._box_entry(36*mm, 50*mm, 20*mm, 5*mm, content='')

        self._small_box_entry(56*mm, 65*mm, 19*mm, 6*mm, content="Fund (2 digits)")
        self._box_entry(56*mm, 60*mm, 19*mm, 5*mm, content='')
        self._box_entry(56*mm, 55*mm, 19*mm, 5*mm, content='')
        self._box_entry(56*mm, 50*mm, 19*mm, 5*mm, content='')

        self._small_box_entry(75*mm, 65*mm, 26*mm, 6*mm, content="Department (4 digits)")
        self._box_entry(75*mm, 60*mm, 26*mm, 5*mm, content='')
        self._box_entry(75*mm, 55*mm, 26*mm, 5*mm, content='')
        self._box_entry(75*mm, 50*mm, 26*mm, 5*mm, content='')

        self._small_box_entry(101*mm, 65*mm, 36*mm, 6*mm, content="Program")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(102.5*mm, 66*mm, "(5 digits or use 00000)")
        self._box_entry(101*mm, 60*mm, 36*mm, 5*mm, content='')
        self._box_entry(101*mm, 55*mm, 36*mm, 5*mm, content='')
        self._box_entry(101*mm, 50*mm, 36*mm, 5*mm, content='')

        self._small_box_entry(137*mm, 65*mm, 14*mm, 6*mm, content="% Split")
        self._box_entry(137*mm, 60*mm, 14*mm, 5*mm, content='')
        self._box_entry(137*mm, 55*mm, 14*mm, 5*mm, content='')
        self._box_entry(137*mm, 50*mm, 14*mm, 5*mm, content='')

        self._small_box_entry(151*mm, 65*mm, 17*mm, 6*mm, content="Bi-weekly Rate")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(155*mm, 66*mm, "(if %Split)")
        self._box_entry(151*mm, 60*mm, 17*mm, 5*mm, content='')
        self._box_entry(151*mm, 55*mm, 17*mm, 5*mm, content='')
        self._box_entry(151*mm, 50*mm, 17*mm, 5*mm, content='')

        self._small_box_entry(168*mm, 65*mm, 17*mm, 6*mm, content="Start Date")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(169.5*mm, 66*mm, "(YYYY-MM-DD)")
        self._small_box_entry(168*mm, 60*mm, 17*mm, 5*mm, content='')
        self._small_box_entry(168*mm, 55*mm, 17*mm, 5*mm, content='')
        self._small_box_entry(168*mm, 50*mm, 17*mm, 5*mm, content='')

        self._small_box_entry(185*mm, 65*mm, 17*mm, 6*mm, content="End Date")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(187.5*mm, 66*mm, "(YYYY-MM-DD)")
        self._small_box_entry(185*mm, 60*mm, 17*mm, 5*mm, content='')
        self._small_box_entry(185*mm, 55*mm, 17*mm, 5*mm, content='')
        self._small_box_entry(185*mm, 50*mm, 17*mm, 5*mm, content='')


        # as signing authority text

        self.c.setFillColor(CMYKColor(0, 0, 1, 0)) # yellow highlight
        self.c.rect(x=0*mm, y=33.5*mm, width=203*mm, height=15.5*mm, stroke=0, fill=1)


        self.c.setFillColor(black)
        self.c.setFont("Helvetica", 6.7)
        self.c.drawString(1*mm, 46.5*mm, "As signing authority, I certify that the appointment and its applicable benefits are eligible and for the purpose of the funding. I will also be responsible for any over-expenditure incurred on the")
        self.c.drawString(1*mm, 43.5*mm, "funding source(s) as result of the appointment and will arrange to clear it. In accordance with the Tri-Agency Financial Administration Guide, this appointment is not for any part of compensation:")
        self.c.drawString(1*mm, 40.5*mm, "to a grantee or to other persons who status would make them eligible to apply for grants related to the Tri-Agency (NSERC, SSHRC, or CIHR); or for any co-applicants and collaborators of the")
        self.c.drawString(1*mm, 37.5*mm, "grant regardless of their eligibility to apply for grants. Furthermore, the appointment is NOT for a family member of the account holder or signing authority. If a family member relationship exists")
        self.c.drawString(1*mm, 34.5*mm, "then additional approvals must be attached in accordance with policies GP37 and R10.01. Please see the procedures contained in GP37 for more information.")

        # signatures
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, 30*mm, "HIRING DEPARTMENT")
        self.c.drawString(107*mm, 30*mm, "REVIEWED BY")

        self.c.setFont("Helvetica-Bold", 6)
        self.c.drawString(107*mm, 10*mm, "**NOTE THAT SIGNATURES ON PAGE 1 REFLECT APPROVAL FOR INFORMATION")
        self.c.drawString(132*mm, 7*mm, "PROVIDED ON BOTH PAGES**")

        self.c.setFont("Helvetica", 7)
        self.c.drawString(78*mm, 7*mm, "(YYYY-MM-DD)")

        self.c.setFont("Helvetica", 8)

        self.c.drawString(5*mm, 24*mm, "Signature Authority:")
        self.c.drawString(14*mm, 16*mm, "Print Name:")
        self.c.drawString(21.5*mm, 8*mm, "Date:")
        self.c.drawString(10.4*mm, 0*mm, "Contact Name:")
        self.c.drawString(10.6*mm, -8*mm, "Contact Email:")

        email = None
        unit = self.ra.unit.label
        if graduate_research_assistant:
            if unit == "CMPT":
                email = CS_CONTACT
            elif unit == "MSE":
                email = MSE_CONTACT
            elif unit == "ENSC":
                email = ENSC_CONTACT
            elif unit == "SEE":
                email = SEE_CONTACT
            elif unit == "APSC":
                email = FAS_CONTACT
        elif research_assistant or non_continuing:
            email = FAS_CONTACT

        self._box_entry(32*mm, 22*mm, 60*mm, 6*mm, content='')
        self._box_entry(32*mm, 14*mm, 60*mm, 6*mm, content='')
        self._box_entry(32*mm, 6*mm, 40*mm, 6*mm, content='')
        self._box_entry(32*mm, -2*mm, 60*mm, 6*mm, content=email)
        self._box_entry(32*mm, -10*mm, 60*mm, 6*mm, content=email)

        self.c.setFont("Helvetica", 8)

        self.c.drawString(117*mm, 24*mm, "Signature:")

        self._box_entry(132*mm, 22*mm, 60*mm, 6*mm, content='')


        self.c.setFont("Helvetica", 5)
        self.c.drawString(-2*mm, -14*mm, "REV 2021-12-09")

        self.c.showPage()

        if research_assistant:
        # PAGE TWO

            self.c.setStrokeColor(black)
            self.c.translate(6*mm, 16*mm) # origin = bottom-left of the content

            self.c.setFont("Helvetica-Bold", 10)
            self.c.setFillColor(self.sfu_red)
            self.c.drawCentredString(self.MAIN_WIDTH/2, 250*mm, "ADDITIONAL INFORMATION REQUIRED FOR RESEARCH ASSISTANTS")

            self.c.setFillColor(black)
            self.c.setFont("Helvetica", 7)
            self.c.drawCentredString(self.MAIN_WIDTH/2, 247*mm, "The following information to produce Offers of Employment and process payroll records. This form is not required for scholarship income.")

            # SECTION 1

            self.c.line(0, 245*mm, self.MAIN_WIDTH, 245*mm)
            self.c.setFont("Helvetica-Bold", 10)
            self.c.setFillColor(self.sfu_red)
            self.c.drawString(1*mm, 241*mm, "SECTION 1: NEW APPOINTMENT OR RE-APPOINTMENT")
            self.c.setFillColor(black)

            self._checkbox(1*mm, 235*mm, text="Check if this is a Fixed Term appointment. NOTE: Will result in full payout to the employee should the appointment end early.", filled=False)

            self.c.setFont("Helvetica-Bold", 8)
            self.c.drawString(1*mm, 231*mm, "REPORTS TO")

            self.c.drawString(1*mm, 225*mm, "Name:")
            self.c.drawString(1*mm, 219*mm, "Position/SFU ID:")
            self.c.drawString(1*mm, 213*mm, "Email:")
            self._box_entry(11*mm, 223*mm, 80*mm, 6*mm, content=str(self.ra.supervisor.name()))
            self._box_entry(24*mm, 217*mm, 67*mm, 6*mm, content=str(self.ra.supervisor.emplid))
            self._box_entry(11*mm, 211*mm, 80*mm, 6*mm, content=str(self.ra.supervisor.email()))

            vacation = [0, 0]
            weeks_vacation = ''
            vacation_pay = ''
            if ra_bw or nc_bw:
                vacation = [1,0]
                weeks_vacation = "%s days" % str(self.ra.weeks_vacation * 5)
            if ra_hourly or nc_hourly:
                vacation = [0,1]
                vacation_pay = "%s %%" % str(self.ra.vacation_pay)

            self.c.drawString(120*mm, 231*mm, "VACATION")
            self.c.setFont("Helvetica-Oblique", 7)
            self.c.drawString(142*mm, 231*mm, "(If left blank, the minimum will be applied)")
            self._checkbox(120*mm, 225*mm, text="Time (min. 10 days/2 weeks) per year:", filled=vacation[0])
            self._checkbox(120*mm, 219*mm, text="Pay % in lieu (min. 4%)", filled=vacation[1])
            self._box_entry(175*mm, 224*mm, 18*mm, 5*mm, content=weeks_vacation)
            self._box_entry(156*mm, 218*mm, 18*mm, 5*mm, content=vacation_pay)

            self.c.setFont("Helvetica-Bold", 8.5)
            self.c.setFillColor(self.sfu_red)
            self.c.drawString(1*mm, 140*mm, "DOCUMENT CHECKLIST")
            self.c.setFillColor(black)
            self.c.setFont("Helvetica-Oblique", 7)
            self.c.drawString(37*mm, 140*mm, "Indicate which forms accompany this PAF for all new appointments:")

            self._checkbox(1*mm, 134*mm, text="Personal Data Form", filled=False)
            self._checkbox(1*mm, 129*mm, text="Copy of Permanent Resident Card (front and back)", filled=False)
            self._checkbox(1*mm, 124*mm, text="TD1 (Personal Tax Credits Return)", filled=False)
            self._checkbox(1*mm, 119*mm, text="TD1BC (BC Personal Tax Credits Return)", filled=False)

            self.c.setFont("Helvetica-Bold", 7)
            self.c.drawString(110*mm, 134*mm, "Temporary Foreign Worker")
            self._checkbox(110*mm, 129*mm, text="Work permit/Study permit", filled=False)
            self._checkbox(110*mm, 124*mm, text="SIN Confirmation Letter with SIN expiry date", filled=False)

            # SECTION 2
            self.c.line(0, 114*mm, self.MAIN_WIDTH, 114*mm)
            self.c.setFont("Helvetica-Bold", 10)
            self.c.setFillColor(self.sfu_red)
            self.c.drawString(1*mm, 110*mm, "SECTION 2: ENDING AN APPOINTMENT BEFORE CONTRACT END DATE")
            self.c.setFillColor(black)

            self.c.setFont("Helvetica", 7)
            self.c.drawString(1*mm, 106*mm, "For resignation and contracts being ended early. Not required if appointment is ending according to employment contract.")

            self.c.setFont("Helvetica-Bold", 8)
            self.c.drawString(1*mm, 98*mm, "Reason for appointment ending:")
            self._checkbox(1*mm, 92*mm, text="Resignation - please provide notice from employee", filled=False)
            self._checkbox(1*mm, 86*mm, text="Appointment ended by PI/Supervisor - please provide reason:", filled=False)
            self._box_entry(86*mm, 72*mm, 112*mm, 17*mm, content='')

            self.c.setFont("Helvetica-Bold", 8)
            self.c.drawString(96*mm, 98*mm, "Last Day Worked:")
            self._box_entry(122*mm, 96*mm, 52*mm, 6*mm, content='')

            self.c.setFont("Helvetica", 7)
            self.c.drawString(175*mm, 98*mm, "YYYY-MM-DD")

            self.c.setFont("Helvetica-Bold", 8)
            self.c.drawString(1*mm, 75*mm, "Will the employee:")
            self._checkbox(1*mm, 69*mm, text="Work their notice period", filled=False)
            self._checkbox(1*mm, 63*mm, text="Be paid out their notice period", filled=False)

            self.c.setFont("Helvetica", 8)
            self.c.drawString(1*mm, 56*mm, "If applicable, indicate the vacation payout amount (for salaried only): Total vacation payout $ ______ OR number of hours: ______")
            self.c.line(0, 51*mm, self.MAIN_WIDTH, 51*mm)
            

            self.c.setFont("Helvetica", 7.5)
            self.c.drawString(1*mm, 45*mm, "The information on this form is collected under the authority of the University Act (RSBC 1996, C. 468), the Income Tax Act, the Pension Plan Act, the Employment Insurance")
            self.c.drawString(1*mm, 42*mm, "Act, the Financial Information Act of BC, and the Workers Compensation Act of BC. The information on this form is used by the University for payroll and benefit plan")
            self.c.drawString(1*mm, 39*mm, "administration, statistical compilations, and operating programs and activities as required by University policies. The information on this form is disclosed to government")
            self.c.drawString(1*mm, 36*mm, "agencies as required by legislation. In accordance with the Financial Information Act of BC, your name, and Remuneration is public information and may be published. If you")
            self.c.drawString(1*mm, 33*mm, "have any questions about the collection and use of this information, please contact the Manager, Payroll.")
            self.c.drawString(1*mm, -9*mm, "PAYROLL APPOINTMENT FORM (formerly FPP4) - January 2022 (produced by %s RAForm)" % (product_name(hint='admin'),))
            self.c.setFont("Helvetica", 5)
            self.c.drawString(-2*mm, -14*mm, "REV 2021-12-09")
            
            # job duties 
            self.c.setFont("Helvetica-Bold", 7)
            self.c.drawString(1*mm, 207*mm, "JOB DUTIES:")
            self.c.setFont("Helvetica-Oblique", 7)
            self.c.drawString(20*mm, 207*mm, "Enter or copy/paste duties below, or attach a supplemental document")
            self._box_entry(1*mm, 145*mm, 195*mm, 60*mm)

            duties = []
            oversized = False
            if research_assistant or non_continuing:
                if research_assistant:
                    duties_list = self.ra.duties_list()
                    for duty in duties_list:
                        duties.append(Paragraph(duty, style=self.NOTE_STYLE))
                    duties.append(Paragraph(self.ra.ra_other_duties, style=self.NOTE_STYLE))
                    oversized = len(duties) > 10
                elif non_continuing:
                    duties.append(Paragraph(self.ra.nc_duties, style=self.NOTE_STYLE))
            f = Frame(2*mm, 145*mm, 194*mm, 60*mm, 0, 0, 0, 0)

            if oversized:
                # ADDITIONAL PAGE FOR DUTIES LIST, IF OVERSIZED
                f.addFromList([Paragraph("See next page.", style=self.NOTE_STYLE)], self.c)
                self.c.showPage()

                self.c.translate(6*mm, 16*mm) # origin = bottom-left of the content
                self.c.setFont("Helvetica-Bold", 10)
                self.c.setFillColor(self.sfu_red)
                self.c.drawCentredString(self.MAIN_WIDTH/2, 250*mm, "DUTIES LIST")

                f = Frame(2*mm, 2*mm, 194*mm, 239*mm, 0, 0, 0, 0)
                self._box_entry(1*mm, 1*mm, 194*mm, 240*mm)
                f.addFromList(duties, self.c)
            else:
                f.addFromList(duties, self.c)

        elif graduate_research_assistant and self.ra.get_scholarship_confirmation_complete():
        # PAGE TWO
            self.c.translate(6*mm, 16*mm) # origin = bottom-left of the content
            self.c.setFillColor(self.sfu_red)
            self.c.setStrokeColor(self.sfu_red)
            self._box_entry(159*mm, 245*mm, 32*mm, 9*mm, content='')
            self.c.drawString(163*mm, 248*mm, "Reset Form")
            self.c.setFont("Helvetica", 13)
            self.c.drawString(18*mm, 240*mm, "EMPLOYMENT VS SCHOLARSHIP QUESTIONNAIRE")
            self.c.setFont("Helvetica", 10)
            self.c.drawString(18*mm, 230*mm, "Principal Investigators are asked to provide information about those individuals receiving scholarship funds")
            self.c.drawString(18*mm, 225*mm, "from grants to help determine whether they are in an employment relationship or are true scholarship.")
            self.c.setFont("Helvetica-Bold", 10)
            self.c.setFillColor(black)
            self.c.setStrokeColor(black)

            self.c.drawString(18*mm, 215*mm, "Principal Investigator:")
            self.c.line(56*mm, 214*mm, 107*mm, 214*mm)
            self.c.drawString(110*mm, 215*mm, "Student Name:")
            self.c.line(136*mm, 214*mm, 190*mm, 214*mm)
            self.c.setFont("Helvetica", 10)
            self.c.drawString(56*mm, 215*mm, str(self.ra.supervisor.name()))
            self.c.drawString(136*mm, 215*mm, str(self.ra.get_name()))

            self.c.drawString(18*mm, 205*mm, "1.")
            self.c.setFont("Helvetica-Bold", 10)
            self.c.drawString(25*mm, 205*mm, "Based on the information provided on page 1, is the funding from your grant for this student:")
            
            self._circle_checkbox(28*mm, 198*mm, filled=False)
            self.c.setFont("Helvetica", 10)
            self.c.drawString(35*mm, 198*mm, "Employment > if this box is checked, there is no need to complete any further questions")
            self.c.line(58*mm, 197*mm, 172*mm, 197*mm)
            self._circle_checkbox(28*mm, 190*mm, filled=True)
            self.c.setFont("Helvetica", 10)
            self.c.drawString(35*mm, 190*mm, "Scholarship > if this box is checked, please answer the additional questions")
            self.c.line(57*mm, 189*mm, 153*mm, 189*mm)
            self._circle_checkbox(28*mm, 182*mm, filled=False)
            self.c.setFont("Helvetica", 10)
            self.c.drawString(35*mm, 182*mm, "Unsure > if this box is checked, please answer the additional questions")
            self.c.line(50*mm, 181*mm, 146*mm, 181*mm)

            self.c.drawString(18*mm, 173*mm, "2.")
            self.c.setFont("Helvetica-Bold", 10)
            self.c.drawString(25*mm, 173*mm, "Does/will the funding from your grant(s) result in research or research-related activities being")
            self.c.drawString(25*mm, 169*mm, "performed by the student that:")

            self.c.setFont("Helvetica", 10)
            self.c.drawString(25*mm, 162*mm, "a)   primarily contribute to the student’s academic progress, for")
            self.c.drawString(31*mm, 157*mm, "example by inclusion in the student’s thesis?")
            self._large_checkbox(153*mm, 158*mm, text="Yes", filled=self.ra.scholarship_confirmation_1)
            self._large_checkbox(170*mm, 158*mm, text="No", filled=not self.ra.scholarship_confirmation_1)

            self.c.drawString(25*mm, 151*mm, "b)   primarily contribute to or benefit someone other than the")
            self.c.drawString(31*mm, 146*mm, "student, for example by supporting your research program or")
            self.c.drawString(31*mm, 141*mm, "the grant?")
            self._large_checkbox(153*mm, 147*mm, text="Yes", filled=self.ra.scholarship_confirmation_2)
            self._large_checkbox(170*mm, 147*mm, text="No", filled=not self.ra.scholarship_confirmation_2)

            self.c.drawString(25*mm, 135*mm, "c)   are not meant to be included in the student’s thesis?")
            self.c.line(37*mm, 134*mm, 57*mm, 134*mm)
            self._large_checkbox(153*mm, 133*mm, text="Yes", filled=self.ra.scholarship_confirmation_3)
            self._large_checkbox(170*mm, 133*mm, text="No", filled=not self.ra.scholarship_confirmation_3)

            self.c.drawString(25*mm, 129*mm, "d)   are not meant to be part of the student’s education in the")
            self.c.drawString(31*mm, 124*mm, "student’s academic discipline?")
            self.c.line(37*mm, 128*mm, 57*mm, 128*mm)
            self._large_checkbox(153*mm, 125*mm, text="Yes", filled=self.ra.scholarship_confirmation_4)
            self._large_checkbox(170*mm, 125*mm, text="No", filled=not self.ra.scholarship_confirmation_4)
            
            self.c.drawString(18*mm, 116*mm, "3.")
            self.c.setFont("Helvetica-Bold", 10)
            self.c.drawString(25*mm, 116*mm, "As part of your interaction with the student who is receiving the")
            self.c.drawString(25*mm, 111*mm, "scholarship, do you/will you:")

            self.c.setFont("Helvetica", 10)
            self.c.drawString(25*mm, 104*mm, "a)   ask the student to perform research or research-related activities")
            self.c.drawString(31*mm, 99*mm, "at specific times or places?")
            self._large_checkbox(153*mm, 101*mm, text="Yes", filled=self.ra.scholarship_confirmation_5)
            self._large_checkbox(170*mm, 101*mm, text="No", filled=not self.ra.scholarship_confirmation_5)

            self.c.setFont("Helvetica", 10)
            self.c.drawString(25*mm, 93*mm, "b)   require the student to track and/or report the hours during which")
            self.c.drawString(31*mm, 88*mm, "the student is performing research or research-related activities?")
            self._large_checkbox(153*mm, 89*mm, text="Yes", filled=self.ra.scholarship_confirmation_6)
            self._large_checkbox(170*mm, 89*mm, text="No", filled=not self.ra.scholarship_confirmation_6)

            self.c.setFont("Helvetica", 10)
            self.c.drawString(25*mm, 82*mm, "c)   ask or expect the student to perform a specified amount of")
            self.c.drawString(31*mm, 77*mm, "research or research-related activities in a given week?")
            self._large_checkbox(153*mm, 78*mm, text="Yes", filled=self.ra.scholarship_confirmation_7)
            self._large_checkbox(170*mm, 78*mm, text="No", filled=not self.ra.scholarship_confirmation_7)

            self.c.setFont("Helvetica", 10)
            self.c.drawString(25*mm, 70*mm, "d)   ask the student to discuss with you on a regular basis their")
            self.c.drawString(31*mm, 65*mm, "research and/or research related activities for any reason other")
            self.c.drawString(31*mm, 60*mm, "than supporting the student’s academic progress?")
            self._large_checkbox(153*mm, 66*mm, text="Yes", filled=self.ra.scholarship_confirmation_8)
            self._large_checkbox(170*mm, 66*mm, text="No", filled=not self.ra.scholarship_confirmation_8)

            self.c.setFont("Helvetica", 10)
            self.c.drawString(25*mm, 53*mm, "e)   ask the student to train or otherwise support other researchers")
            self.c.drawString(31*mm, 48*mm, "in your research group for any reason other than supporting the")
            self.c.drawString(31*mm, 43*mm, "student’s academic progress?")
            self._large_checkbox(153*mm, 49*mm, text="Yes", filled=self.ra.scholarship_confirmation_9)
            self._large_checkbox(170*mm, 49*mm, text="No", filled=not self.ra.scholarship_confirmation_9)

            self.c.setFont("Helvetica-Bold", 10)
            self.c.drawString(18*mm, 36*mm, "Subsequent semester appointments will have the same answers to these questions.")
            self._large_checkbox(170*mm, 35*mm, text="Yes", filled=self.ra.scholarship_subsequent)

            self.c.setFont("Helvetica", 10)
            self.c.drawString(18*mm, 29*mm, "Feel free to provide any additional information below. ")

            self._box_entry(18*mm, 0*mm, 180*mm, 28*mm)
            f = Frame(19*mm, 0*mm, 180*mm, 28*mm, 0, 0, 0, 0)
            f.addFromList([Paragraph(self.ra.scholarship_notes, style=self.NOTE_STYLE)], self.c)

            self.c.setFont("Helvetica", 7)
            self.c.drawString(18*mm, -5*mm, "Created 20230213")
            self.c.drawString(175*mm, -5*mm, "pg. 2 of 2")

        self.c.save()
    

class RAForm(SFUMediaMixin):
    MAIN_WIDTH = 8*inch # size of the main box
    ENTRY_FONT = "Helvetica-Bold"
    NOTE_STYLE = ParagraphStyle(name='Normal',
                                fontName=ENTRY_FONT,
                                fontSize=10,
                                leading=11,
                                alignment=TA_LEFT,
                                textColor=black)

    def __init__(self, ra):
        self.ra = ra
        self._media_setup()

    def _checkbox(self, x, y, text="", filled=0, leading=0):
        self.c.circle(x+1.5*mm, y+1.5*mm, 1.5*mm, stroke=1, fill=filled)
        self.c.setFont("Helvetica", 7)
        self.c.drawString(x+5*mm, y+0.5*mm+leading, text)

    def _box_entry(self, x, y, width, height, content=None):
        self.c.setLineWidth(1)
        self.c.rect(x, y, width, height)
        if content:
            self.c.setFont(self.ENTRY_FONT, 12)
            self.c.drawString(x+3*mm, y+height-4.5*mm, content)

    def draw_pdf(self, outfile):
        """
        Generates PDF in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)
        self.c.setStrokeColor(black)

        self.c.translate(6*mm, 16*mm) # origin = bottom-left of the content
        self.c.setStrokeColor(black)

        # SFU logo
        self.c.drawImage(logofile, x=0, y=247*mm, width=20*mm, height=10*mm)
        self.c.setFont('BemboMTPro', 10)
        self.c.setFillColor(self.sfu_red)
        self._drawStringLeading(self.c, 23*mm, 250*mm, 'Simon Fraser University'.translate(self.sc_trans_bembo), charspace=1.4)
        self.c.setFont('DINPro', 5)
        self.c.setFillColor(self.sfu_grey)
        self._drawStringLeading(self.c, 23*mm, 247.5*mm, 'Engaging the World'.upper(), charspace=2)
        self.c.setFillColor(black)

        # form header
        self.c.setFont("Helvetica-Bold", 11)
        self.c.drawCentredString(self.MAIN_WIDTH/2, 238*mm, "Payroll Appointment Form (PAF): For Non Affiliated Temporary Appointments")
        self.c.setFont("Helvetica", 5)
        self.c.drawCentredString(self.MAIN_WIDTH/2, 234.5*mm, "FOR GUIDE FOR THE COMPLETION OF PAYROLL APPOINTMENT FORM (PP4), PLEASE VISIT OUR PAYROLL WEBSITE CLICK HERE")

        # type of employee checkboxes
        self.c.setLineWidth(0.5)
        self.c.rect(0, 198*mm, self.MAIN_WIDTH, 35.5*mm)

        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawCentredString(self.MAIN_WIDTH/2, 228*mm, "Please Check Appropriate Box")
        self.c.drawString(2*mm, 222*mm, "Employment Income")
        self.c.drawCentredString(self.MAIN_WIDTH/2, 222*mm, "Employment Income")
        self.c.drawString(155*mm, 222*mm, "Scholarship Income")

        cat = self.ra.hiring_category
        self._checkbox(1.5*mm, 216*mm, text="Research Assistant", filled=(cat=='RA'))
        self._checkbox(1.5*mm, 211*mm, text="Recreation Services Staff", filled=(cat=='RSS'))
        self._checkbox(1.5*mm, 206*mm, text="Post Doctoral Fellows", filled=(cat=='PDF'))
        self._checkbox(1.5*mm, 201*mm, text="Other Non Continuing", filled=(cat=='ONC'))
        self._checkbox(67*mm, 215.5*mm, text="University Research Assistant (R50.04)", leading=1.5*mm, filled=(cat=='RA2'))
        self.c.setFont("Helvetica", 5)
        self.c.drawString(72*mm, 215*mm, "Min of 2 years with Benefits")
        self._checkbox(67*mm, 203*mm, text="University Research Assistant (R50.04)", leading=1.5*mm, filled=(cat=='RAR'))
        self.c.setFont("Helvetica", 5)
        self.c.drawString(72*mm, 202.5*mm, "Renewal after 2 years with Benefits")
        self._checkbox(142*mm, 215.5*mm, text="Graduate Research Assistant Scholarship", filled=(cat=='GRA'))
        self._checkbox(142*mm, 203*mm, text="National Scholarship", filled=(cat=='NS'))

        # health/numbers
        if self.ra.medical_benefits:
            fills = [1, 0]
        else:
            fills = [0, 1]
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(1*mm, 193*mm, "Health Benefits")
        self._checkbox(1*mm, 187*mm, text="Yes, Eligible for Health Benefits", filled=fills[0])
        self._checkbox(1*mm, 182*mm, text="No, Not Eligible for Health Benefits", filled=fills[1])

        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(52*mm, 190*mm, "Social Insurance")
        self.c.drawString(137*mm, 190*mm, "SFUID")

        self._box_entry(83*mm, 188*mm, 51*mm, 6.5*mm, content=str(self.ra.sin or ''))
        self._box_entry(148*mm, 188*mm, 55*mm, 6.5*mm, content=str(self.ra.person.emplid))

        self.c.setLineWidth(1)
        self.c.line(0, 181*mm, self.MAIN_WIDTH, 181*mm)

        # personal/position details
        self.c.setFont("Helvetica", 9)
        self.c.drawString(3*mm, 176*mm, "Last Name")
        self.c.drawString(94*mm, 176*mm, "First Name")
        self.c.drawString(185*mm, 176*mm, "Initial")
        self._box_entry(1.5*mm, 165*mm, 87*mm, 7.5*mm, content=str(self.ra.person.last_name))
        self._box_entry(92*mm, 165*mm, 86*mm, 7.5*mm, content=str(self.ra.person.first_name))
        mi = None
        if self.ra.person.middle_name:
            mi = self.ra.person.middle_name[0]
        self._box_entry(183*mm, 165*mm, 19*mm, 7.5*mm, content=mi)

        self.c.setFont("Helvetica", 8)
        self.c.drawString(2.5*mm, 158*mm, "Department")
        self.c.drawString(117*mm, 158*mm, "Position Title")
        self._box_entry(30*mm, 156*mm, 83*mm, 6.5*mm, content=self.ra.unit.informal_name())
        self._box_entry(136*mm, 156*mm, 66*mm, 6.5*mm, content=str(self.ra.account.title))

        # position numbers
        self.c.setFont("Helvetica", 7)
        self.c.drawString(1.5*mm, 150*mm, "Project (6-8)")
        self.c.drawString(45*mm, 150*mm, "Object (4)")
        self.c.drawString(71*mm, 150*mm, "Fund (2)")
        self.c.drawString(85*mm, 150*mm, "Dept (4)")
        self.c.drawString(112*mm, 150*mm, "Program (5)")
        self.c.drawString(151*mm, 148*mm, "Position Number")
        self.c.setFont("Helvetica-Oblique", 7)
        self.c.drawString(1.5*mm, 147*mm, "if applicable")
        self.c.drawString(45*mm, 147*mm, "Required")
        self.c.drawString(71*mm, 147*mm, "Required")
        self.c.drawString(85*mm, 147*mm, "If no project")
        self.c.drawString(112*mm, 147*mm, "If no project")
        self._box_entry(1.5*mm, 139*mm, 40*mm,  6.5*mm, content=self.ra.project.get_full_project_number())
        self._box_entry(45*mm, 139*mm, 23*mm, 6.5 * mm, content="%04i" % self.ra.account.account_number)
        self._box_entry(71*mm, 139*mm, 11.5*mm, 6.5*mm, content="%i" % self.ra.project.fund_number)
        self._box_entry(85*mm, 139*mm, 25*mm, 6.5*mm, content=str(self.ra.project.department_code))
        self._box_entry(112*mm, 139*mm, 31*mm, 6.5*mm, content=self.ra.get_program_display())
        if self.ra.account.position_number <= 1:
            position_number = ''
        else:
            position_number = str(self.ra.account.position_number).zfill(8)
        self._box_entry(150*mm, 139*mm, 46*mm, 6.5*mm, content=position_number)

        # dates
        self.c.setFont("Helvetica", 8)
        self.c.drawString(1.5*mm, 133*mm, "Start Date")
        self.c.drawString(73*mm, 133*mm, "End Date")
        self._box_entry(21.5*mm, 131.5*mm, 42*mm, 5.5*mm, content=str(self.ra.start_date).replace('-', '/'))
        self._box_entry(92.5*mm, 131.5*mm, 42*mm, 5.5*mm, content=str(self.ra.end_date).replace('-', '/'))

        # money
        if self.ra.pay_frequency == 'L':
            hourly = ''
            biweekly = ''
            biweekhours = ''
            if self.ra.lump_sum_hours and self.ra.use_hourly():
                lumphours = str(self.ra.lump_sum_hours)
            else:
                lumphours = ''
            lumpsum = "$%.2f" % (self.ra.lump_sum_pay)
        elif self.ra.use_hourly():
            hourly = "$%.2f" % (self.ra.hourly_pay)
            biweekly = ""
            biweekhours = "%i:00" % (self.ra.hours)
            lumphours = ''
            lumpsum = ''
        else: # biweekly, not hourly
            hourly = ""
            biweekly = "$%.2f" % (self.ra.biweekly_pay)
            biweekhours = "%i:00" % (self.ra.hours)
            lumphours = ''
            lumpsum = ''

        self.c.setFont("Helvetica", 7)
        self.c.drawString(3*mm, 125*mm, "Hourly Rate")
        self.c.drawString(74*mm, 125*mm, "Bi-weekly Salary")
        self.c.drawString(142*mm, 125*mm, "Lump Sum Adjustment")
        self._box_entry(1.5*mm, 117*mm, 61*mm, 6.5*mm, content=hourly)
        self._box_entry(72.5*mm, 117*mm, 61*mm, 6.5*mm, content=biweekly)
        self._box_entry(141.5*mm, 117*mm, 61*mm, 6.5*mm, content=lumpsum)

        # Hours
        self.c.setFont("Helvetica", 5)
        self.c.drawString(2*mm, 112*mm, "Enter Hourly Rate if paid by the hour. Enter bi-weekly rate")
        self.c.drawString(2*mm, 109.5*mm, "if salary. DO NOT ENTER BOTH")

        self.c.drawString(81*mm, 113*mm, "Bi-weekly Hours -")
        self.c.drawString(81*mm, 110.5*mm, "must reflect number")
        self.c.drawString(81*mm, 108*mm, "of hours worked on")
        self.c.drawString(81*mm, 105.5*mm, "bi-weekly basis")
        self.c.drawString(147*mm, 113*mm, "Lum Sum Hours")

        self.c.drawString(107*mm, 112*mm, "Hours and")
        self.c.drawString(108*mm, 109.5*mm, "Minutes")
        self.c.drawString(172*mm, 112*mm, "Hours and")
        self.c.drawString(173*mm, 109.5*mm, "Minutes")

        self._box_entry(103*mm, 103*mm, 15.5*mm, 6*mm, content=biweekhours)
        self._box_entry(168*mm, 103*mm, 15.5*mm, 6*mm, content=lumphours)

        self.c.setFont("Helvetica", 5)
        self.c.drawString(1.5*mm, 100*mm, "Notes:")
        self.c.drawString(23*mm, 100*mm, "Bi-Weekly employment earnings rate must include vacation pay. Hourly rates will automatically have vacation pay added. The employer cost of the statutory benefits will be charged to the account in")
        self.c.drawString(23*mm, 97*mm, "addition to the earnings rate. Bi-weekly hours must reflect the number of hours worked and must meet legislative requirements for minimum wage.")

        # Commments
        self.c.setFont("Helvetica", 9)
        self.c.drawString(2*mm, 90.5*mm, "Comments:")
        self.c.setLineWidth(1)
        self._box_entry(22*mm, 80*mm, 180*mm, 14*mm, content='')

        f = Frame(23*mm, 80*mm, 175*mm, 14*mm, 0, 0, 0, 0)#, showBoundary=1)
        notes = []
        if self.ra.pay_frequency != 'L':
            default_note = "For total amount of $%s over %.1f pay periods." % (self.ra.lump_sum_pay, self.ra.pay_periods)
        else:
            default_note = "Lump sum payment of $%s." % (self.ra.lump_sum_pay,)
        notes.append(Paragraph(default_note, style=self.NOTE_STYLE))
        notes.append(Paragraph(self.ra.notes, style=self.NOTE_STYLE))
        f.addFromList(notes, self.c)
        self.c.setFont("Helvetica", 7.3)
        self.c.drawString(2.5*mm, 76*mm, "As signing authority, I certify that the appointment and its applicable benefits are eligible and for the purpose of the funding. In accordance with the Tri-Agency Financial")
        self.c.drawString(2.5*mm, 73*mm, "Administration Guide, this appointment is not for any part of compensation: to a grantee or to other persons who status would make them eligible to apply for grants")
        self.c.drawString(2.5*mm, 70*mm, "related to the Tri-Agency (NSERC, SSHRC,or CIHR); or for any co-applicants and collaborators of the grant regardless of their eligibility to apply for grants. Furthermore, the")
        self.c.drawString(2.5*mm, 67*mm, "appointment is NOT for a family member of the account holder or signing authority. If a family member relationship exists then additional approvals must be attached in")
        self.c.drawString(2.5*mm, 64*mm, "accordance with policies GP 37 and R10.01. Please see the procedures contained in GP 37 for more information.")

        # signatures
        self.c.setFont("Helvetica", 9)
        self.c.drawString(2*mm, 59*mm, "HIRING DEPARTMENT")
        self.c.drawString(117*mm, 59*mm, "REVIEWED BY")
        self.c.setFont("Helvetica", 7)
        self.c.drawString(2*mm, 51*mm, "Signature Authority")
        self.c.drawString(2*mm, 43*mm, "Date")
        self.c.drawString(98*mm, 51*mm, "Signature Authority")
        self.c.drawString(98*mm, 43*mm, "Date")
        self.c.drawString(2*mm, 32.5*mm, "Prepared by/Contact")
        self.c.drawString(2*mm, 29*mm, "Person (Phone no.)")
        self.c.drawString(2*mm, 19*mm, "Date")

        self._box_entry(35.5*mm, 49.5*mm, 60*mm, 6*mm, content='')
        self._box_entry(35.5*mm, 41*mm, 60*mm, 6*mm, content='')
        self._box_entry(35.5*mm, 25*mm, 60*mm, 14*mm, content='')
        self._box_entry(35.5*mm, 17*mm, 60*mm, 6*mm, content='')
        self._box_entry(132*mm, 49.5*mm, 60*mm, 6*mm, content='')
        self._box_entry(132*mm, 41*mm, 60*mm, 6*mm, content='')

        # footer
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawCentredString(self.MAIN_WIDTH/2, 12*mm, "PAYROLL WILL ONLY PROCESS COMPLETED FORMS")

        self.c.setFont("Helvetica", 5)
        self.c.drawString(2*mm, 7.5*mm, "The information on this form is collected under the authority of the University Act (RSBC 1996, C. 468), the Income Tax Act, the Pension Plan Act, the Employment Insurance Act, the Financial Information Act of BC, and the Workers Compensation Act")
        self.c.drawString(2*mm, 5*mm, "of BC. The information on this form is used by the University for payroll and benefit plan administration, statistical compilations, and operating programs and activities as required by University policies. The information on this form is disclosed to")
        self.c.drawString(2*mm, 2.5*mm, "government agencies as required by legislation. In accordance with Financial Information Act of BC, your Name, and Remuneration is public information and may be published. If you have any questions about the collection and use of this")
        self.c.drawString(2*mm, 0*mm, "information, please contact the Manager, Payroll.")
        self.c.drawString(2*mm, -5*mm, "PAYROLL APPOINTMENT FORM (formerly FPP4) - March 2016 (produced by %s RAForm)" % (product_name(hint='admin'),))

        self.c.showPage()
        self.c.save()



class RAForm_old(object):
    """
    Old FPP4 form. Kept for historical curiosity until such time as we're sure it's not needed anymore.
    """
    BOX_OFFSET = 0.1*inch # how far boxes are from the edges (i.e. from the larger box)
    ENTRY_SIZE = 0.4*inch # height of a data entry box
    ENTRY_HEIGHT = ENTRY_SIZE + BOX_OFFSET # height difference for adjacent entry boxes
    LABEL_OFFSET = 2 # right offset of a label from the box position
    LABEL_HEIGHT = 8 # height of a label (i.e. offset of top of box)
    DATA_BUMP = 4 # how far to move data up from bottom of box
    MAIN_WIDTH = 7.5*inch # size of the main box
    MAIN_HEIGHT = 7.5*inch # size of the main box
    CHECK_SIZE = 0.1*inch # checkbox size
    NOTE_STYLE = ParagraphStyle(name='Normal',
                                fontName='Helvetica',
                                fontSize=10,
                                leading=11,
                                alignment=TA_LEFT,
                                textColor=black)

    def __init__(self, ra):
        self.ra = ra

    def _draw_box_right(self, x, y, label, content, width=MAIN_WIDTH-BOX_OFFSET, tick=False):
        self._draw_box_left(x=self.MAIN_WIDTH - x - width - self.BOX_OFFSET, y=y, label=label,
                            content=content, width=width, tick=tick)

    def _draw_box_left(self, x, y, label, content, width=MAIN_WIDTH-BOX_OFFSET, tick=False):
        """
        Draw one text entry box with the above parameters.
        "width" parameter should include one BOX_OFFSET
        """
        # box/tickmark
        self.c.setLineWidth(2)
        if not tick:
            self.c.rect(x + self.BOX_OFFSET, y - self.BOX_OFFSET - self.ENTRY_SIZE, width - self.BOX_OFFSET, self.ENTRY_SIZE)
        else:
            self.c.line(x + self.BOX_OFFSET, y - self.BOX_OFFSET - self.ENTRY_SIZE, x + self.BOX_OFFSET, y - self.BOX_OFFSET - self.ENTRY_SIZE + 0.2*inch)

        # label
        self.c.setFont("Helvetica", 6)
        self.c.drawString(x + self.BOX_OFFSET + self.LABEL_OFFSET, y - self.BOX_OFFSET - self.LABEL_HEIGHT, label)

        # content
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawString(x + self.BOX_OFFSET + 2*self.LABEL_OFFSET, y - self.BOX_OFFSET - self.ENTRY_SIZE + self.DATA_BUMP, content)

    def _rule(self, height):
        self.c.setLineWidth(2)
        self.c.line(0, height, self.MAIN_WIDTH, height)

    def _signature_line(self, x, y, width, label):
        self.c.setLineWidth(1)
        self.c.line(x, y, x+width, y)
        self.c.setFont("Helvetica", 6)
        self.c.drawString(x, y-7, label)


    def draw_pdf(self, outfile):
        """
        Generates PDF in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)
        self.c.setStrokeColor(black)

        # draw form
        self.c.translate(0.5*inch, 2.25*inch) # origin = lower-left of the main box

        self.c.setStrokeColor(black)
        self.c.setLineWidth(2)
        self.c.rect(0, 0, self.MAIN_WIDTH, self.MAIN_HEIGHT)

        self.c.setFont("Helvetica", 10)
        self.c.drawCentredString(4*inch, 8.25*inch, "SIMON FRASER UNIVERSITY")
        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawCentredString(4*inch, 8*inch, "Student, Research & Other Non-Union")
        self.c.drawCentredString(4*inch, 7.75*inch, "Appointments")
        self.c.drawImage(logofile, x=0.5*inch, y=7.75*inch, width=1*inch, height=0.5*inch)
        self.c.setFont("Helvetica", 6)
        self.c.drawCentredString(4*inch, 7.6*inch, "PLEASE SEE GUIDE TO THE COMPLETION OF APPOINTMENT FOR FPP4")

        # SIN
        if self.ra.sin:
            sin = "%09i" % (self.ra.sin)
            sin = sin[:3] + '-' + sin[3:6] + '-' + sin[6:]
        else:
            sin = ''
        self._draw_box_left(0, self.MAIN_HEIGHT, width=3.125*inch, label="SOCIAL INSURANCE NUMBER (SIN)", content=sin)

        # emplid
        emplid = str(self.ra.person.emplid)
        emplid = emplid[:5] + '-' + emplid[5:]
        self._draw_box_right(0, self.MAIN_HEIGHT, width=3.375*inch, label="SFU ID #", content=emplid)

        # names
        self._draw_box_left(0, self.MAIN_HEIGHT - self.ENTRY_HEIGHT, label="LAST OR FAMILY NAME", content=self.ra.person.last_name)
        self._draw_box_left(0, self.MAIN_HEIGHT - 2*self.ENTRY_HEIGHT, label="FIRST NAME", content=self.ra.person.first_name)

        height = 5.875*inch
        self._rule(height)

        # position
        self._draw_box_left(0, height, width=3.125*inch, label="POSITION NUMBER", content='') # to be filled by HR
        self._draw_box_right(0, height, width=3.75*inch, label="POSITION TITLE", content=str(self.ra.account.title))

        # department
        dept = self.ra.unit.informal_name()
        if self.ra.unit.deptid():
            dept += " (%s)" % (self.ra.unit.deptid())
        self._draw_box_left(0, height - self.ENTRY_HEIGHT, width=3.125*inch, label="DEPARTMENT", content=dept)

        # fund/project/account
        self._draw_box_right(0, height - self.ENTRY_HEIGHT, width=3.75*inch, label="FUND", content="%i" % (self.ra.project.fund_number))
        self._draw_box_right(0, height - self.ENTRY_HEIGHT, width=3*inch,
                             label="DEPARTMENT/PROJECT NUM", tick=True, content="%06i" % (self.ra.project.project_number))
        self._draw_box_right(0, height - self.ENTRY_HEIGHT, width=1.25*inch,
                             label="ACCOUNT", tick=True, content="%06i" % (self.ra.account.account_number))

        height = 4.75*inch
        self._rule(height)

        # dates
        self._draw_box_left(0, height, width=2.125*inch, label="START DATE (yyyy/mm/dd)", content=str(self.ra.start_date).replace('-', '/'))
        self._draw_box_left(3*inch, height, width=1.5*inch, label="END DATE (yyyy/mm/dd)", content=str(self.ra.end_date).replace('-', '/'))

        # health benefit check boxes
        self.c.setLineWidth(1)
        self.c.setFont("Helvetica", 6)
        if self.ra.medical_benefits:
            fills = [1, 0]
        else:
            fills = [0, 1]
        self.c.rect(5*inch, height - self.BOX_OFFSET - self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[0])
        self.c.drawString(5*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 0.5*self.CHECK_SIZE - 3, "Yes, Eligible for Health Benefits")
        self.c.rect(5*inch, height - self.BOX_OFFSET - 2.5*self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[1])
        self.c.drawString(5*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 2*self.CHECK_SIZE - 3, "Not Eligible for Health Benefits")

        # pay
        if self.ra.pay_frequency == 'L':
            hourly = ''
            biweekly = ''
            hours = ''
            lumpsum = "$%.2f" % (self.ra.lump_sum_pay)
        else:
            hourly = "$  %.2f" % (self.ra.hourly_pay)
            biweekly = "$  %.2f" % (self.ra.biweekly_pay)
            hours = "%i : 00" % (self.ra.hours)
            lumpsum = ''
        if not self.ra.use_hourly():
            hourly = ''
            hours = ''
        self._draw_box_left(0, height - self.ENTRY_HEIGHT, width=2.125*inch, label="HOURLY", content=hourly)
        self._draw_box_left(3*inch, height - self.ENTRY_HEIGHT, width=1.5*inch, label="BI-WEEKLY", content=biweekly)
        self._draw_box_right(0, height - self.ENTRY_HEIGHT, width=2.25*inch, label="LUMP SUM ADJUSTMENT", content='')

        self._draw_box_left(3*inch, height - 2*self.ENTRY_HEIGHT, width=1.5*inch, label="BI-WEEKLY HOURS", content=hours)
        self._draw_box_left(self.MAIN_WIDTH - self.BOX_OFFSET - 2.25*inch, height - 2*self.ENTRY_HEIGHT, width=1*inch, label="LUMP SUM", content=lumpsum)

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(self.BOX_OFFSET, height - 1.125*inch, "Enter Hourly Rate if Paid by the hour.")
        self.c.drawString(self.BOX_OFFSET, height - 1.125*inch - 9, "Enter Biweekly rate if salary.  DO NOT")
        self.c.drawString(self.BOX_OFFSET, height - 1.125*inch - 18, "ENTER BOTH.")

        height = 3*inch
        self._rule(height)

        # appointment type checkboxes
        if self.ra.hiring_category == 'U':
            fills = [0,0,1,0]
        elif self.ra.hiring_category == 'E':
            fills = [0,1,0,0]
        elif self.ra.hiring_category == 'N':
            fills = [0,0,0,1]
        elif self.ra.hiring_category == 'S':
            fills = [1,0,0,0]
        else:
            fills = [0,0,0,0]

        self.c.setLineWidth(1)
        self.c.setFont("Helvetica", 6)
        self.c.rect(0.75*inch, height - self.BOX_OFFSET - self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[0])
        self.c.drawString(0.75*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 0.5*self.CHECK_SIZE - 3, "GRAD STUDENT RESEARCH ASSISTANT (SCHOLARSHIP INCOME)")
        self.c.rect(4*inch, height - self.BOX_OFFSET - self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[1])
        self.c.drawString(4*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 0.5*self.CHECK_SIZE - 3, "GRAD STUDENT RESEARCH ASSISTANT (EMPLOYMENT INCOME)")
        self.c.rect(4*inch, height - self.BOX_OFFSET - 3*self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[2])
        self.c.drawString(4*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 2.5*self.CHECK_SIZE - 3, "UNDERGRAD STUDENT")
        self.c.rect(4*inch, height - self.BOX_OFFSET - 5*self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[3])
        self.c.drawString(4*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 4.5*self.CHECK_SIZE - 3, "NON STUDENT")

        height = 2.25*inch
        self._rule(height)

        # notes
        self.c.setFont("Helvetica", 6)
        self.c.drawString(self.BOX_OFFSET, height - self.LABEL_HEIGHT, "NOTES:")
        self.c.setFont("Helvetica", 4)
        self.c.drawString(1.25*inch, height - 7, "BI-WEEKLY EMPLOYMENT EARNINGS RATE MUST INCLUDE VACATION PAY. HOURLY RATES WILL AUTOMATICALLY HAVE VACATION PAY ADDED.")
        self.c.drawString(1.25*inch, height - 12, "THE EMPLOYER COST OF STATUTORY BENEFITS WILL BE CHARGED TO THE ACCOUNT IN ADDITION TO THE EARNINGS RATE.")

        f = Frame(self.BOX_OFFSET, height - 1.125*inch, self.MAIN_WIDTH - 2*self.BOX_OFFSET, 1*inch) # showBoundary=1
        notes = []
        if self.ra.pay_frequency != 'L':
            default_note = "For total amount of $%s over %.1f pay periods." % (self.ra.lump_sum_pay, self.ra.pay_periods)
        else:
            default_note = "Lump sum payment of $%s." % (self.ra.lump_sum_pay,)
        notes.append(Paragraph(default_note, style=self.NOTE_STYLE))
        notes.append(Spacer(1, 8))
        notes.append(Paragraph(self.ra.notes, style=self.NOTE_STYLE))
        f.addFromList(notes, self.c)

        height = 1.125*inch
        self._rule(height)

        # signatures
        self._signature_line(self.BOX_OFFSET, height - 0.325*inch, 2*inch, "SIGNING AUTHORITY")
        self._signature_line(3.125*inch, height - 0.325*inch, 1.125*inch, "FINANCIAL SERVICES")
        self._signature_line(5.5*inch, height - 0.325*inch, 1.25*inch, "DATA ENTRY")
        self._signature_line(self.BOX_OFFSET, height - 0.75*inch, 2*inch, "DATE")
        self._signature_line(3.125*inch, height - 0.75*inch, 1.125*inch, "DATE")
        self._signature_line(5.5*inch, height - 0.75*inch, 1.25*inch, "DATE")

        # footer
        self.c.setFont("Helvetica", 4)
        height = 0
        self.c.drawString(0, height-10, "THE INFORMATION ON THIS FORM IS COLLECTED UNDER THE AUTHORITY OF THE UNIVERSITY ACT (RSBC 1996, C. 468), THE INCOME TAX ACT, THE PENSION PLAN ACT, THE EMPLOYMENT INSURANCE ACT, THE FINANCIAL INFORMATION ACT")
        self.c.drawString(0, height-15, "OF BC, AND THE WORKERS COMPENSATION ACT OF BC. THE INFORMATION ON THIS FORM IS USED BY THE UNIVERSITY FOR PAYROLL AND BENEFIT PLAN ADMINISTRATION, STATISTICAL COMPILATIONS, AND OPERATING PRGRAMS")
        self.c.drawString(0, height-20, "AND ACTIVITIES AS REQUIRED BY UNIVERSITY POLICIES. THE INFORMATION ON THIS FORM IS DISCLOSED TO GOVERNMENT AGENCIES AS REQURIED BY THE GOVERNMENT ACTS. YOUR BANKING INFORMATION IS DIESCLOSED")
        self.c.drawString(0, height-25, "TO FINANCIAL INSTITUTIONS FOR THE PURPOSE OF DIRECT DEPOSIT. IN ACCORDANCE WITH THE FINANCIAL INFORMATION ACT OF BC, YOUR NAME AND REMUNERATION  IS PUBLIC INFORMATION AND MAY BE PUBLISHED.")
        self.c.drawString(0, height-35, "IF YOU HAVE ANY QUESTIONS ABOUT THE COLLECTION AND USE OF THIS INFORMATION, PLEASE CONTACT THE SIMON FRASER UNIVERSITY PAYROLL SUPERVISOR.")

        self.c.setFont("Helvetica-Bold", 6)
        self.c.drawString(0, height-50, "REVISED Nov 2004 (produced by %s RAForm)" % (product_name(hint='admin'),))

        self.c.showPage()
        self.c.save()


def ra_form(ra, outfile):
    """
    Generate PAF form for this RAAppointment.
    """
    form = RAForm(ra)
    return form.draw_pdf(outfile)

def ra_paf(ra, config, outfile):
    """
    Generate PAF form for this RAAppointment.
    """
    form = RARequestForm(ra, config)
    return form.draw_pdf(outfile)



class TAForm(object):
    """
    For for HR to appoint a TA
    """
    BOX_HEIGHT = 0.25*inch
    LABEL_RIGHT = 2
    LABEL_UP = 2
    CONTENT_RIGHT = 4
    CONTENT_UP = 4
    LABEL_SIZE = 6
    CONTENT_SIZE = 12
    NOTE_STYLE = ParagraphStyle(name='Normal',
                                fontName='Helvetica',
                                fontSize=7,
                                leading=10,
                                alignment=TA_LEFT,
                                textColor=black)
                        

    def __init__(self, outfile):
        """
        Create TA Appointment Form(s) in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)

    def _draw_box(self, x, y, width, label='', label_size=LABEL_SIZE, content='', content_size=CONTENT_SIZE, right=False):
        height = self.BOX_HEIGHT
        self.c.setLineWidth(1)
        self.c.rect(x, y, width, height)

        if label:
            self.c.setFont("Helvetica", label_size)
            self.c.drawString(x + self.LABEL_RIGHT, y + height + self.LABEL_UP, label)

        if content:
            self.c.setFont("Helvetica", content_size)
            if right:
                self.c.drawRightString(x + width - self.CONTENT_RIGHT, y + self.CONTENT_UP, content)
            else:
                self.c.drawString(x + self.CONTENT_RIGHT, y + self.CONTENT_UP, content)


    def draw_form_cmptcontract(self, contract):
        """
        Draw the form for an old-style CMPT only contract (ta module)
        """
        initial_appointment_fill = 0
        if contract.appt == "INIT":
            initial_appointment_fill = 1
        reappointment_fill = 0
        if contract.appt == "REAP":
            reappointment_fill = 1

        courses = []
        total_bu = 0
        bu = 0
        for crs in contract.tacourse_set.filter(bu__gt=0):
            courses.append((
                crs.course.subject + ' ' + crs.course.number + ' ' + crs.course.section[:2],
                crs.description.description,
                crs.total_bu,
            ))
            bu += crs.bu
            total_bu += crs.total_bu

        payperiods = contract.posting.payperiods()
        total_pay = contract.pay_per_bu * total_bu
        biweekly_pay = total_pay / payperiods
        scholarship_pay = bu * contract.scholarship_per_bu
        biweekly_scholarship = scholarship_pay / payperiods

        acc_date = ''        
        if contract.status == 'ACC' and contract.config.get('accepted_date') is not None:  
            if type(contract.config.get('accepted_date')) is str:
                acc_date = contract.config.get('accepted_date')[:10]
            else:
                acc_date = contract.config.get('accepted_date').strftime("%Y/%m/%d")     

        return self.draw_form(
            emplid=contract.application.person.emplid,
            sin=contract.sin,
            last_name=contract.application.person.last_name,
            first_name=contract.application.person.first_name,
            unit_name=contract.application.posting.unit.informal_name(),
            deptid=contract.application.posting.unit.deptid(),
            appointment_start=contract.appointment_start,
            appointment_end=contract.appointment_end,
            pay_start=contract.pay_start,
            pay_end=contract.pay_end,
            initial_appointment_fill=initial_appointment_fill,
            reappointment_fill=reappointment_fill,
            position_number=contract.position_number.position_number,
            courses=courses,
            appt_category=contract.appt_category,
            appt_cond=contract.appt_cond,
            total_pay=total_pay,
            biweek_pay=biweekly_pay,
            total_schol=scholarship_pay,
            biweek_schol=biweekly_scholarship,
            remarks=contract.remarks,
            acc_date=acc_date,
            sigs=Signature.objects.filter(user__userid=contract.created_by),
        )

    def draw_form_contract(self, contract):
        """
        Draw the form for an new-style contract (tacontract module)
        """
        initial_appointment_fill = 0
        if contract.appointment == "INIT":
            initial_appointment_fill = 1
        reappointment_fill = 0
        if contract.appointment == "REAP":
            reappointment_fill = 1

        courses = []
        for crs in contract.course.filter(bu__gt=0):
            if not crs.description:
                description = "Office/Marking"
                if crs.labtut:
                    description = "Office/Marking/Lab"
            else:
                description = str(crs.description)

            courses.append((
                crs.course.subject + ' ' + crs.course.number + ' ' + crs.course.section[:2],
                description,
                crs.total_bu,
            ))

        return self.draw_form(
            emplid=contract.person.emplid,
            sin=contract.sin,
            last_name=contract.person.last_name,
            first_name=contract.person.first_name,
            unit_name=contract.category.account.unit.informal_name(),
            deptid=contract.category.account.unit.deptid(),
            appointment_start=contract.appointment_start,
            appointment_end=contract.appointment_end,
            pay_start=contract.pay_start,
            pay_end=contract.pay_end,
            initial_appointment_fill=initial_appointment_fill,
            reappointment_fill=reappointment_fill,
            position_number=contract.category.account.position_number,
            courses=courses,
            appt_category=contract.category.code,
            appt_cond=contract.conditional_appointment,
            total_pay=contract.total_pay,
            biweek_pay=contract.biweekly_pay,
            total_schol=contract.scholarship_pay,
            biweek_schol=contract.biweekly_scholarship,
            remarks=contract.comments,
            acc_date='',
            sigs=Signature.objects.filter(user__userid=contract.created_by),
        )

    def draw_form(self, emplid, sin, last_name, first_name, unit_name, deptid, appointment_start, appointment_end,
                  pay_start, pay_end, initial_appointment_fill, reappointment_fill, position_number, courses,
                  appt_category, appt_cond, total_pay, biweek_pay, total_schol, biweek_schol, remarks, acc_date, sigs):
        """
        Generic TA Form drawing method: probably called by one of the above that abstract out the object details.
        """

        # For backwards compatibility to older contracts without their own appoinment start/end dates/
        if not appointment_start:
            appointment_start = pay_start
        if not appointment_end:
            appointment_end = pay_end


        self.c.setStrokeColor(black)
        self.c.translate(0.625*inch, 1.25*inch) # origin = lower-left of the main box
        main_width = 7.25*inch

        # header
        self.c.drawImage(logofile, x=main_width/2 - 0.5*inch, y=227*mm, width=1*inch, height=0.5*inch)
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(main_width/2 + 1*inch, 233*mm, "SIMON FRASER UNIVERSITY")
        self.c.drawRightString(main_width/2 - 1*inch, 233*mm, "Teaching Assistant Appointment Form")

        # main outline
        self.c.setStrokeColor(black)
        self.c.setLineWidth(2)
        p = self.c.beginPath()
        p.moveTo(0,0)
        p.lineTo(0, 8.875*inch)
        p.lineTo(43*mm, 8.875*inch)
        p.lineTo(43*mm, 8.625*inch)
        p.lineTo(main_width, 8.625*inch)
        p.lineTo(main_width, 0)
        p.close()
        self.c.drawPath(p, stroke=1, fill=0)

        # personal info
        self._draw_box(0, 8.625*inch, 43*mm, label="SFU ID #", content=str(emplid))
        self._draw_box(0, 210*mm, 43*mm, label="CANADA SOCIAL INSURANCE NO.", content=None)
        self._draw_box(46*mm, 210*mm, 74*mm, label="LAST OR FAMILY NAME", content=str(last_name))
        self._draw_box(125*mm, 210*mm, 50*mm, label="FIRST NAME", content=str(first_name))

        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(35*mm, 205*mm, "THE DEPARTMENT HAS CONFIRMED THAT THE ABOVE APPOINTEE IS ELIGIBLE TO WORK IN CANADA")
        self.c.rect(150*mm, 203*mm, 5*mm, 5*mm, fill=True)

        self.c.translate(0, -7*mm) # translate to make room for the new employment eligibility line
        self._draw_box(15*mm, 202*mm, 160*mm, content="c/o " + str(unit_name)) # ADDRESS
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(2, 206*mm, "HOME")
        self.c.drawString(2, 203*mm, "ADDRESS")

        # appointment basic info
        self.c.drawString(2, 194*mm, "DEPARTMENT")
        dept = str(str(unit_name))
        if deptid:
            dept += " (%s)" % (deptid)
        self._draw_box(20*mm, 193*mm, 78*mm, content=dept) # DEPARTMENT
        self._draw_box(102*mm, 193*mm, 32*mm, label="APPOINTMENT START DATE", content=str(appointment_start))
        self._draw_box(139*mm, 193*mm, 32*mm, label="APPOINTMENT END DATE", content=str(appointment_end))

        # initial appointment boxes
        self.c.rect(14*mm, 185*mm, 5*mm, 5*mm, fill=initial_appointment_fill)
        self.c.rect(14*mm, 176*mm, 5*mm, 5*mm, fill=reappointment_fill)
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(21*mm, 188*mm, "INITIAL APPOINTMENT TO")
        self.c.drawString(21*mm, 186*mm, "THIS POSITION NUMBER")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(21*mm, 179*mm, "REAPPOINTMENT TO SAME POSITION")
        self.c.drawString(21*mm, 177*mm, "NUMBER OR REVISION TO APPOINTMENT")

        # position info
        self._draw_box(60*mm, 176*mm, 37*mm, label="POSITION NUMBER", content=str(position_number))
        self._draw_box(102*mm, 176*mm, 32*mm, label="PAYROLL START DATE", content=str(pay_start))
        self._draw_box(139*mm, 176*mm, 32*mm, label="PAYROLL END DATE", content=str(pay_end))


        # course assignment headers
        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(1*mm, 168*mm, "ASSIGNMENT")
        self.c.setLineWidth(1)
        self.c.rect(24*mm, 168*mm, 27*mm, 4*mm)
        self.c.rect(51*mm, 168*mm, 74*mm, 4*mm)
        self.c.rect(125*mm, 168*mm, 23*mm, 4*mm)
        self.c.setFont("Helvetica", 5)
        self.c.drawString(33*mm, 169*mm, "COURSE(S)")
        self.c.drawString(56*mm, 169*mm, "DESCRIPTION")
        self.c.drawString(132*mm, 169*mm, "BASE UNITS")


        # course assignments
        total_bu = 0
        for i, crs in zip(list(range(5)), list(courses)+[None]*5):
            h = 162*mm - i*6*mm # bottom of this row
            self.c.rect(24*mm, h, 27*mm, 6*mm)
            self.c.rect(51*mm, h, 74*mm, 6*mm)
            self.c.rect(125*mm, h, 23*mm, 6*mm)

            self.c.setFont("Helvetica", self.CONTENT_SIZE-2)
            if crs:
                self.c.drawString(25*mm, h + 1*mm, crs[0])
                self.c.drawString(52*mm, h + 1*mm, crs[1])
                self.c.drawRightString(147*mm, h + 1*mm, "%.2f" % (crs[2]))
                total_bu += crs[2]

        self.c.rect(125*mm, 132*mm, 23*mm, 6*mm)
        self.c.drawRightString(147*mm, 133*mm, "%.2f" % (total_bu))

        self._draw_box(153*mm, 160*mm, 22*mm, label="APPT. CATEGORY", content=appt_category)
        self._draw_box(153*mm, 145*mm, 22*mm, label="Cond. upon Enrol?", content="Yes" if appt_cond else "No")

        # salary/scholarship
        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(8*mm, 123*mm, "SALARY")
        self.c.drawString(1*mm, 112*mm, "SCHOLARSHIP")
        self.c.setFont("Helvetica", self.CONTENT_SIZE)
        self.c.drawString(29*mm, 122*mm + self.CONTENT_UP, "$")
        self.c.drawString(75*mm, 122*mm + self.CONTENT_UP, "$")
        self.c.drawString(29*mm, 111*mm + self.CONTENT_UP, "$")
        self.c.drawString(75*mm, 111*mm + self.CONTENT_UP, "$")
        self._draw_box(33*mm, 122*mm, 32*mm, label="BIWEEKLY RATE", right=True, content="%.2f" % (biweek_pay))
        self._draw_box(79*mm, 122*mm, 32*mm, label="SEMESTER RATE", right=True, content="%.2f" % (total_pay))
        self._draw_box(33*mm, 111*mm, 32*mm, label="BIWEEKLY RATE", right=True, content="%.2f" % (biweek_schol))
        self._draw_box(79*mm, 111*mm, 32*mm, label="SEMESTER RATE", right=True, content="%.2f" % (total_schol))

        self._draw_box(139*mm, 122*mm, 32*mm, label="EFF. DATE FOR RATE CHANGES", content=str(pay_start))
        self.c.setFont("Helvetica", 5)
        self.c.drawString(114*mm, 125*mm, "THESE RATES INCLUDE 4%")
        self.c.drawString(114*mm, 123*mm, "VACATION PAY")

        # As usual, work will be assigned using the Time Use Guidelines, and you are expected to track and report your hours in the normal manner.
        # remarks
        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(1*mm, 106*mm, "REMARKS")
        f = Frame(3*mm, 79*mm, main_width - 6*mm, 27*mm) #, showBoundary=1
        notes = []
        notes.append(Paragraph(remarks, style=self.NOTE_STYLE))
        f.addFromList(notes, self.c)

        self.c.translate(0, 7*mm) # translate back for the un-moved content

        self.c.line(0, 75*mm, main_width, 75*mm)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(3*mm, 70*mm, "INSTRUCTIONS:")
        self.c.drawString(3*mm, 63*mm, "DEPARTMENT:")
        self.c.drawString(3*mm, 59*mm, "This form is to be forwarded to Payroll for processing once the employee has confirmed (by email) their acceptance of the offer of")
        self.c.drawString(3*mm, 55*mm, "employment and upon the approval of the appropriate departmental signing authority.")
        self.c.drawString(3*mm, 45*mm, "APPOINTEE:")
        self.c.drawString(3*mm, 41*mm, "If this is an initial appointment in the TSSU bargaining unit, then as a condition of employment under the terms of the Collective")
        self.c.drawString(3*mm, 37*mm, 'Agreement you must complete and sign the first two sections of the form entitled "Appendix A to Article IV Dues and Union')
        self.c.drawString(3*mm, 33*mm, 'Membership or Non Membership" and return it with this appointment form.')

        # signatures
        if sigs:
            import PIL
            sig = sigs[0]
            sig.sig.open()
            img = PIL.Image.open(sig.sig)
            width, height = img.size
            hei = 8*mm
            wid = 1.0*width/height * hei
            sig.sig.open()
            ir = ImageReader(sig.sig)
            self.c.drawImage(ir, x=3*mm, y=9*mm, width=wid, height=hei)

        self.c.setLineWidth(1)
        self.c.line(0, 18*mm, main_width, 18*mm)
        self.c.line(0, 9*mm, main_width, 9*mm)
        self.c.line(60*mm, 18*mm, 60*mm, 0)
        self.c.line(120*mm, 18*mm, 120*mm, 0)

        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(1*mm, 16*mm, "APPROVAL BY DEPARTMENT")
        self.c.drawString(61*mm, 16*mm, "APPROVED BY FACULTY")
        self.c.drawString(1*mm, 1*mm, "DATE")
        self.c.drawString(61*mm, 1*mm, "DATE")
        self.c.drawString(121*mm, 1*mm, "DATE")
        self.c.drawString(121*mm, 16*mm, "TEACHING ASSISTANT SIGNATURE")

        self.c.setFont("Helvetica", self.CONTENT_SIZE)
        date = datetime.date.today()
        self.c.drawString(10*mm, 2*mm, str(date))
        self.c.drawString(131*mm, 2*mm, acc_date)
        
        # links
        self.c.setLineWidth(0.3)
        self.c.linkURL('https://www2.gov.bc.ca/gov/content/employment-business/employment-standards-advice/employment-standards/forms-resources/igm', (1*mm, -4*mm, 24*mm, -3.5*mm), relative=1)
        self.c.line(1*mm, -5.2*mm, 25.5*mm, -5.2*mm)
        self.c.linkURL('http://www.sfu.ca/policies.html', (140*mm, -4*mm, 167*mm, -3.5*mm), relative=1)
        self.c.setLineWidth(0.3)
        self.c.line(143.1*mm, -5.2*mm, 163.1*mm, -5.2*mm)
        self.c.setLineWidth(1)

        # footer
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(1*mm, -3*mm, "ORIGINAL: DEAN     COPY : EMPLOYEE     COPY : DEPARTMENT     COPY : UNION (IF TSSU APP'T)     COPY: PAYROLL")
        self.c.setFont("Helvetica", 3.25)
        self.c.drawString(1*mm, -5*mm, "BC’S EMPLOYMENT STANDARDS ACT (ESA) PROVIDES EMPLOYERS AND EMPLOYEES WITH GUIDELINES TO ENSURE THE CONSISTENT AND LEGAL APPLICATION OF EMPLOYMENT PRACTICES AND EMPLOYEE RIGHTS. REFER TO THE ESA WEBSITE AND SFU’S POLICIES AND PROCEDURES FOR FACTS AND PROCEDURAL")
        self.c.drawString(1*mm, -5*mm - 4, "INFORMATION. NOTE THAT CERTAIN CLAUSES IN COLLECTIVE AGREEMENTS WILL SUPERSEDE LANGUAGE IN THE ESA AND VICE VERSA.")
        self.c.drawString(1*mm, -5*mm - 8, "THE INFORMATION ON THIS FORM IS COLLECTED UNDER THE AUTHORITY OF THE UNIVERSITY ACT (RSBC 1996, C.468), THE INCOME TAX ACT, THE PENSION PLAN ACT, THE EMPLOYMENT INSURANCE ACT, THE FINANCIAL INFORMATION ACT OF BC, AND THE WORKERS COMPENSATION ACT OF BC. THE")
        self.c.drawString(1*mm, -5*mm - 12, "INFORMATION ON THIS FORM IS USED BY THE UNIVERSITY FOR PAYROLL AND BENEFIT PLAN ADMINISTRATION, STATISTICAL COMPILATIONS AND OPERATING PROGRAMS AND ACTIVITIES AS REQUIRED BY UNIVERSITY POLICIES. THE INFORMATION ON THIS FORM IS DISCLOSED TO GOVERNMENT AGENCIES")
        self.c.drawString(1*mm, -5*mm - 16, "AS REQUIRED BY THE GOVERNMENT ACTS. YOUR BANKING INFORMATION IS DISCLOSED TO FINANCIAL INSITUTIONS FOR THE PURPOSE OF DIRECT DEPOSIT. IN ACCORDANCE WITH THE FINANCIAL INFORMATION ACT OF BC, YOUR NAME AND REMUNERATION IS PUBLIC INFORMATION AND MAY BE")
        self.c.drawString(1*mm, -5*mm - 20, "PUBLISHED.")
        self.c.drawString(1*mm, -5*mm - 28, "IF YOU HAVE ANY QUESTIONS ABOUT THE COLLECTION AND USE OF THIS INFORMATION, PLEASE CONTACT THE SIMON FRASER UNIVERSITY PAYROLL SUPERVISOR.")

        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(1*mm, -18*mm, "Updated June 2023 (produced by %s TAForm)" % (product_name(hint='admin'),))

        self.c.showPage()

    def save(self):
        self.c.save()



def ta_form(contract, outfile):
    """
    Generate TA Appointment Form for this TAContract (ta module).
    """
    doc = TAForm(outfile)
    doc.draw_form_cmptcontract(contract)
    doc.save()

def ta_forms(contracts, outfile):
    """
    Generate TA Appointment Forms for this list of TAContracts (ta module) in one PDF
    """
    doc = TAForm(outfile)
    for c in contracts:
        doc.draw_form_cmptcontract(c)
    doc.save()

def tacontract_form(contract, outfile):
    """
    Generate TA Appointment Form for this TAContract (tacontract module).
    """
    doc = TAForm(outfile)
    doc.draw_form_contract(contract)
    doc.save()


def tacontract_forms(contracts, outfile):
    """
    Generate TA Appointment Form for this list of TAContracts (tacontract module).
    """
    doc = TAForm(outfile)
    for c in contracts:
        doc.draw_form_contract(c)
    doc.save()


class GradeChangeForm(SFUMediaMixin):
    def __init__(self, outfile):
        self._media_setup()
        self.c = canvas.Canvas(outfile, pagesize=letter)

    def title_font(self):
        self.c.setFont("DINPro-Bold", 8.5)
    def label_font(self):
        self.c.setFont("BemboMTPro", 8.5)
    def entry_font(self):
        self.c.setFont("Helvetica-Bold", 15)
    def entry_font_small(self):
        self.c.setFont("Helvetica-Bold", 12)

    def check_label(self, x, y, label, fill=0):
        self.label_font()
        self.c.rect(x, y, 3*mm, 3*mm, fill=0)
        if fill:
            self.c.line(x, y, x+3*mm, y+3*mm)
            self.c.line(x+3*mm, y, x, y+3*mm)
        self.c.drawString(x+5*mm, y, label)

    def draw_form(self, member, oldgrade, newgrade, user):
        """
        Generates form for this contract
        """
        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.6)
        self.c.translate(16*mm, 25*mm) # origin = lower-left of content
        main_width = 7.0*inch

        # header
        self.c.drawImage(logofile, x=0, y=224*mm, width=1*inch, height=0.5*inch)
        self.c.setFont("BemboMTPro", 11)
        self.c.drawString(43*mm, 228*mm, "RECORDS AND REGISTRATION".translate(self.sc_trans_bembo))
        self.c.drawString(43*mm, 223*mm, "STUDENT SERVICES".translate(self.sc_trans_bembo))
        self.title_font()
        self.c.drawString(121*mm, 228*mm, "CHANGE OF GRADE NOTIFICATION")
        self.c.drawString(121*mm, 224*mm, 'AND/OR EXTENSION OF "DE" GRADE')

        # student info
        self.title_font()
        self.c.drawString(0, 210*mm, "SFU STUDENT NUMBER")
        self.c.rect(35*mm, 207*mm, 92*mm, 8*mm, fill=0)
        self.entry_font()
        self.c.drawString(40*mm, 209*mm, str(member.person.emplid))

        self.title_font()
        self.c.drawString(0, 203*mm, "STUDENT NAME (PLEASE PRINT CLEARLY)")

        self.label_font()
        self.c.drawString(0, 195*mm, "Surname")
        self.c.line(12*mm, 195*mm, 91*mm, 195*mm)
        self.c.drawString(93*mm, 195*mm, "Given Names")
        self.c.line(112*mm, 195*mm, main_width, 195*mm)
        self.entry_font()
        self.c.drawString(15*mm, 196*mm, member.person.last_name)
        fname = member.person.first_name
        if member.person.middle_name:
            fname += ' ' + member.person.middle_name
        #if member.person.pref_first_name:
        #    fname += ' (' + member.person.pref_first_name + ')'
        self.c.drawString(115*mm, 196*mm, fname)

        # term info
        name = str(member.offering.semester.name)
        year = 1900 + int(name[0:3])
        semester = name[3]
        self.title_font()
        self.c.drawString(0, 189*mm, "TERM")
        self.label_font()
        self.c.drawString(0, 183*mm, "Year")
        self.c.line(6*mm, 183*mm, 30*mm, 183*mm)
        self.check_label(36*mm, 183*mm, 'Fall', fill=semester=='7')
        self.check_label(50*mm, 183*mm, 'Spring', fill=semester=='1')
        self.check_label(67*mm, 183*mm, 'Summer', fill=semester=='4')
        self.check_label(86*mm, 183*mm, 'Intersession', fill=0)
        self.check_label(110*mm, 183*mm, 'Summer Session', fill=0)
        self.c.rect(140*mm, 183*mm, 40*mm, 8*mm, fill=0)
        self.c.drawString(148*mm, 178*mm, "4-digit term number")
        self.entry_font()
        self.c.drawString(10*mm, 184*mm, str(year))
        self.c.drawString(148*mm, 185*mm, str(name))

        # course info
        self.title_font()
        self.c.drawString(0, 175*mm, "COURSE")
        self.label_font()
        self.c.drawString(0, 169*mm, "Course subject (e.g. CHEM)")
        self.c.rect(36*mm, 168*mm, 41*mm, 8*mm, fill=0)
        self.c.drawString(81*mm, 169*mm, "Course number")
        self.c.rect(102*mm, 168*mm, 41*mm, 8*mm, fill=0)
        self.entry_font()
        self.c.drawString(40*mm, 170*mm, member.offering.subject)
        self.c.drawString(110*mm, 170*mm, member.offering.number)
        self.label_font()
        self.c.drawString(0, 159*mm, "Class number/section")
        self.c.rect(28*mm, 157*mm, 51*mm, 8*mm, fill=0)
        self.c.drawString(82*mm, 159*mm, "Course title")
        self.c.line(97*mm, 159*mm, main_width, 159*mm)
        self.entry_font()
        self.c.drawString(35*mm, 159*mm, member.offering.section)
        self.entry_font_small()
        self.c.drawString(98*mm, 160*mm, member.offering.title)

        # grade change
        self.title_font()
        self.c.drawString(0, 149*mm, "IF CHANGE OF GRADE:")
        self.label_font()
        self.c.drawString(0, 141*mm, "Original grade")
        self.c.rect(20*mm, 139*mm, 21*mm, 8*mm, fill=0)
        self.c.drawString(45*mm, 141*mm, "Revised grade")
        self.c.rect(64*mm, 139*mm, 21*mm, 8*mm, fill=0)
        self.entry_font()
        if oldgrade:
            old = oldgrade
        else:
            old = ''
        if newgrade:
            new = newgrade
        else:
            new = ''
        self.c.drawString(25*mm, 141*mm, old)
        self.c.drawString(69*mm, 141*mm, new)

        # DE extension
        self.title_font()
        self.c.drawString(0, 132*mm, "IF EXTENSION OF \u201CDE\u201D GRADE:")
        self.label_font()
        self.c.drawString(0, 127*mm, "Extension due date:")
        self.c.drawString(30*mm, 127*mm, "Year (YYYY)")
        self.c.line(47*mm, 127*mm, 67*mm, 127*mm)
        self.c.drawString(69*mm, 127*mm, "Month (MM)")
        self.c.line(86*mm, 127*mm, 103*mm, 127*mm)
        self.c.drawString(105*mm, 127*mm, "Day (DD)")
        self.c.line(118*mm, 127*mm, 136*mm, 127*mm)

        # reasons
        self.title_font()
        self.c.drawString(0, 120*mm, "REASON FOR CHANGE OF GRADE/EXTENION OF \u201CDE\u201D GRADE")
        self.c.drawString(0, 116*mm, "(NOTE: WHEN ASSIGNING A GRADE OF \u201CFD\u201D AN ACADEMIC DISHONESTY REPORT NEEDS TO BE FILED.)")
        self.c.line(0*mm, 109*mm, main_width, 109*mm)
        self.c.line(0*mm, 101*mm, main_width, 101*mm)
        self.c.line(0*mm, 93*mm, main_width, 93*mm)

        self.label_font()
        self.c.drawString(0, 86*mm, "Has the student applied to graduate this term?")
        self.c.drawString(0, 80*mm, "Is this student's academic standing currently RTW or PW?")
        self.check_label(76*mm, 86*mm, 'Yes', fill=0)
        self.check_label(95*mm, 86*mm, 'No', fill=0)
        self.check_label(76*mm, 80*mm, 'Yes', fill=0)
        self.check_label(95*mm, 80*mm, 'No', fill=0)

        # approvals
        self.title_font()
        self.c.drawString(0, 72*mm, "APPROVALS")
        self.label_font()
        self.c.drawString(0, 67*mm, "Instructor signature")
        self.c.line(25*mm, 67*mm, 108*mm, 67*mm)
        self.c.drawString(110*mm, 67*mm, "Date")
        self.c.line(117*mm, 67*mm, main_width, 67*mm)
        self.c.drawString(0, 59*mm, "Instructor name (PLEASE PRINT)")
        self.c.line(44*mm, 59*mm, main_width, 59*mm)
        self.entry_font()
        self.c.drawString(46*mm, 60*mm, user.name())
        self.c.drawString(120*mm, 68*mm, str(datetime.date.today().strftime('%B %d, %Y')))

        self.label_font()
        self.c.drawString(0, 51*mm, "Chair signature")
        self.c.line(20*mm, 51*mm, 108*mm, 51*mm)
        self.c.drawString(110*mm, 51*mm, "Date")
        self.c.line(117*mm, 51*mm, main_width, 51*mm)
        self.c.drawString(0, 43*mm, "Chair name (PLEASE PRINT)")
        self.c.line(38*mm, 43*mm, main_width, 43*mm)
        self.entry_font()

        # FOIPOP
        self.title_font()
        self.c.drawString(0, 35*mm, "FREEDOM OF INFORMATION AND PROTECTION OF PRIVACY")
        self.label_font()
        self.c.drawString(0, 31*mm, "The information on this form is collected under the authority of the University Act (RSBC 1996 c468 s.27[4a]). This information is needed, and")
        self.c.drawString(0, 27*mm, "will be used, to update the student's record. If you have any questions about the collection and use of this information contact the Associate Registrar,")
        self.c.drawString(0, 23*mm, "Information, Records and Registration, 778.782.3198.")

        self.c.drawString(0, 15*mm, "Accepted (for the Registrar)")
        self.c.line(35*mm, 15*mm, 122*mm, 15*mm)
        self.c.drawString(124*mm, 15*mm, "Date")
        self.c.line(131*mm, 15*mm, main_width, 15*mm)

        # footer
        self.c.setFont("BemboMTPro", 7.5)
        self.c.drawString(43*mm, 6*mm, "Information, Records and Registration, MBC 3200")
        self.c.drawString(43*mm, 3*mm, "8888 University Drive, Burnaby BC Canada V5A 1S6")
        self.c.drawString(43*mm, 0*mm, "students.sfu.ca/records")
        self.c.drawString(122*mm, 6*mm, "FAX: 778.782.4969")
        self.c.drawString(122*mm, 3*mm, "urecords@sfu.ca")
        self.c.drawString(154*mm, 6*mm, "NOVEMBER".translate(self.sc_trans_bembo) + " " + "2009".translate(self.digit_trans))
        self.c.drawString(154*mm, 3*mm, "(produced by %s" % (product_name(hint='course'),))
        self.c.drawString(154*mm, 0*mm, "GradeChangeForm)")




    def save(self):
        self.c.save()

def grade_change_form(member, oldgrade, newgrade, user, outfile):
    doc = GradeChangeForm(outfile)
    doc.draw_form(member, oldgrade, newgrade, user)
    doc.save()


class CardReqForm(object):
    LABEL_FONT = ("Helvetica", 9)
    ENTRY_FONT = ("Helvetica-Bold", 9)
    MED_GREY = CMYKColor(0, 0, 0, 0.5)
    LT_GREY = CMYKColor(0, 0, 0, 0.2)

    def __init__(self, outfile):
        """
        Create Card Requisition Form(s) in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)
        self.main_width = 192*mm

    def save(self):
        self.c.save()

    def _header_line(self, y, text):
        self.c.setFillColor(black)
        self.c.rect(0, y, self.main_width, 3.5*mm, fill=1)
        self.c.setFillColor(white)
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawCentredString(self.main_width/2, y + 0.5*mm, text)
        self.c.setFillColor(black)

    def _line_entry(self, x, y, text, line_offset, line_length, entry_text=''):
        self.c.setFont(*self.LABEL_FONT)
        self.c.setLineWidth(1)
        self.c.drawString(x, y+1*mm, text)
        self.c.line(x+line_offset, y, x+line_offset+line_length, y)
        self.c.setFont(*self.ENTRY_FONT)
        self.c.drawString(x+line_offset+2*mm, y+1*mm, entry_text)

    def _checkbox(self, x, y, text, offset=0.5*mm, fill=0, boxheight=4.5*mm, fontsize=9):
        self.c.setLineWidth(2)
        self.c.setFont("Helvetica", fontsize)
        boxwidth = 4.5*mm
        self.c.rect(x, y, boxwidth, boxheight)
        self.c.setLineWidth(1)
        if fill:
            self.c.line(x,y,x+boxwidth, y+boxheight)
            self.c.line(x+boxwidth,y,x, y+boxheight)
        self.c.drawString(x+boxwidth+offset, y+1*mm, text)

    def draw_form(self, grad, extra_rooms=None):
        """
        Generates card requisition form for this grad
        """
        self.c.setStrokeColor(black)
        self.c.setFillColor(black)
        self.c.setLineWidth(1)
        self.c.translate(7*mm, 30*mm) # origin = lower-left of the content

        self.c.setFont("Helvetica-Bold", 11)
        self.c.drawCentredString(self.main_width/2, 223*mm, 'SFU BURNABY CAMPUS SECURITY - ACCESS & PHYSICAL SECURITY SOLUTIONS')
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawCentredString(self.main_width/2, 219*mm, 'CARD / FOB / KEY REQUISITION')

        # personal info
        self._header_line(213*mm, 'CARD/FOB/KEYHOLDER DETAILS (Please type or print)')
        self._line_entry(0*mm, 208*mm, 'Last Name', 22*mm, 58*mm, grad.person.last_name)
        self._line_entry(86*mm, 208*mm, 'SFU ID', 30*mm, 45*mm, str(grad.person.emplid))
        self._line_entry(0*mm, 204*mm, 'Given Name', 22*mm, 58*mm, grad.person.first_name)
        self._line_entry(86*mm, 204*mm, 'email or phone #', 30*mm, 45*mm, str(grad.person.email()))

        self._checkbox(0*mm, 197*mm, 'Faculty', offset=1*mm)
        self._checkbox(22*mm, 197*mm, 'Staff', offset=1*mm)
        self._checkbox(40*mm, 197*mm, 'Student', fill=1)
        self._checkbox(63*mm, 197*mm, 'Contractor')
        self._checkbox(90*mm, 197*mm, 'Other:')
        self._line_entry(108*mm, 197*mm, '', 0*mm, 53*mm, '')

        # key areas: boxes/outlines
        self.c.setLineWidth(2)
        self.c.translate(0*mm, 150*mm) # origin = lower-left of the key-areas boxes
        self.c.rect(0, 0, 44*mm, 42*mm)
        self.c.line(4.5*mm, 36*mm, 4.5*mm, 0*mm)
        self.c.line(9*mm, 42*mm, 9*mm, 0*mm)
        self.c.line(27*mm, 36*mm, 27*mm, 0*mm)
        self.c.line(0*mm, 36*mm, 44*mm, 36*mm)
        self.c.line(0*mm, 28*mm, 44*mm, 28*mm)
        self.c.setFillColor(black)
        self.c.rect(9*mm, 28*mm, 35*mm, 8*mm, fill=1)
        self.c.rect(49*mm, 28*mm, 143*mm, 8*mm, fill=1)
        self.c.setFillColor(self.MED_GREY)
        self.c.setLineWidth(0)
        self.c.rect(49*mm, 36*mm, 143*mm, 6*mm, fill=1)
        self.c.setLineWidth(2)
        self.c.setFillColor(black)
        self.c.rect(49*mm, 0*mm, 143*mm, 28*mm)
        self.c.line(71*mm, 0*mm, 71*mm, 36*mm)
        self.c.line(76*mm, 0*mm, 76*mm, 36*mm)
        self.c.line(129*mm, 0*mm, 129*mm, 36*mm)
        self.c.line(170*mm, 0*mm, 170*mm, 36*mm)
        self.c.setLineWidth(1)
        for i in range(5):
            y = 28.0*mm/6*(i+1)
            self.c.line(0, y, 44*mm, y)
            self.c.line(49*mm, y, 192*mm, y)

        # key areas: text
        self.c.setFont("Helvetica", 7)
        self.c.drawCentredString(4.5*mm, 39*mm, 'Item')
        self.c.drawCentredString(4.5*mm, 37*mm, 'Type')
        self.c.drawCentredString(27*mm, 37*mm, 'Area (keys / cards / fobs)')
        self.c.drawString(50*mm, 37*mm, 'Schedule (applied only to Card / Fob space access)')
        self.c.saveState()
        self.c.rotate(90)
        self.c.drawString(29*mm, -3*mm, 'Key')
        self.c.drawString(29*mm, -7.5*mm, 'Card')
        self.c.restoreState()
        self.c.setFillColor(white)
        self.c.drawString(10*mm, 29*mm, 'Building')
        self.c.drawString(27*mm, 29*mm, 'Room / Door #')
        self.c.drawString(49*mm, 29*mm, 'Effective Date')
        self.c.drawCentredString(73*mm, 32*mm, '24')
        self.c.drawCentredString(73*mm, 29*mm, 'Hr')
        self.c.drawString(77*mm, 29*mm, 'Other Days/Times')
        self.c.drawString(130*mm, 29*mm, 'Access Group (if known)')
        self.c.drawString(171*mm, 29*mm, 'Expiry Date')
        self.c.setFillColor(black)

        rooms = grad.program.unit.config.get('card_rooms', '').split('|')
        if extra_rooms:
            rooms += extra_rooms.split('|')

        if grad.current_status in STATUS_APPLICANT:
            # applicants start access next semester
            # ... assuming nobody does these requests >4mo in advance. I'll take that bet.
            start = Semester.next_starting().start
        else:
            # everyone else starts now
            start = datetime.date.today()

        end = start + datetime.timedelta(days=(365*5+1))
        for i,r in enumerate(rooms):
            y = 28.0*mm/6*(5-i) + 1*mm
            if ':' in r:
                bld,rm = r.split(':', 2)
            else:
                bld,rm = r, ''

            self.c.drawString(6*mm, y, 'X')
            self.c.drawString(10*mm, y, bld)
            self.c.drawString(28*mm, y, rm)
            self.c.drawString(50*mm, y, start.isoformat())
            self.c.drawString(72*mm, y, 'X')
            self.c.drawString(171*mm, y, end.isoformat())

        self.c.translate(0*mm, -150*mm) # origin = lower-left of the content

        self._line_entry(23*mm, 145*mm, 'Desk or cabinet key #', 35*mm, 45*mm)
        self.c.setFont(*self.LABEL_FONT)
        self.c.drawString(104*mm, 145*mm, '(attach an envelope to include a sample key if possible)')
        self._checkbox(0*mm, 136*mm, 'New Card', offset=2*mm, fill=1)
        self._checkbox(23*mm, 136*mm, 'Update existing card', offset=1*mm)
        self._line_entry(81*mm, 136*mm, 'Card/Fob #:', 22*mm, 45*mm)
        self._line_entry(23*mm, 130*mm, 'Additional Information:', 35*mm, 94*mm)

        # office-use blocks
        self.c.translate(0*mm, 88*mm) # origin = lower-left of the office-use boxes
        self.c.setFillColor(self.MED_GREY)
        self.c.setLineWidth(0)
        self.c.rect(0*mm, 33*mm, 93*mm, 4.5*mm, fill=1)
        self.c.rect(103*mm, 33*mm, 89*mm, 4.5*mm, fill=1)
        self.c.setFillColor(self.LT_GREY)
        self.c.rect(103*mm, 0*mm, 89*mm, 33*mm, fill=1)
        self.c.setFillColor(black)
        self.c.setLineWidth(2)
        self.c.rect(0*mm, 28*mm, 93*mm, 5*mm, fill=1)
        self.c.rect(0*mm, 0*mm, 93*mm, 28*mm)
        self.c.line(14*mm, 0*mm, 14*mm, 28*mm)
        self.c.line(44*mm, 0*mm, 44*mm, 28*mm)
        self.c.line(62*mm, 0*mm, 62*mm, 28*mm)
        self.c.line(85*mm, 0*mm, 85*mm, 28*mm)
        self.c.setLineWidth(1)
        for i in range(5):
            y = 28.0*mm/6*(i+1)
            self.c.line(0, y, 93*mm, y)

        self.c.rect(143*mm, 9*mm, 28*mm, 20*mm)
        self.c.line(157*mm, 14*mm, 157*mm, 29*mm)
        self.c.line(143*mm, 24*mm, 171*mm, 24*mm)
        self.c.line(143*mm, 19*mm, 171*mm, 19*mm)
        self.c.line(143*mm, 14*mm, 171*mm, 14*mm)

        # office-use text
        self.c.setFont(*self.LABEL_FONT)
        self.c.drawString(1*mm, 34*mm, 'Office use only (key code may be entered if known)')
        self.c.drawString(104*mm, 34*mm, 'Office use only')
        self.c.setFont("Helvetica", 7)
        self.c.setFillColor(white)
        self.c.drawString(1*mm, 29*mm, 'Keyway')
        self.c.drawString(15*mm, 29*mm, 'Bitting')
        self.c.drawString(45*mm, 29*mm, 'Hook')
        self.c.drawString(63*mm, 29*mm, 'Key code')
        self.c.drawString(86*mm, 29*mm, 'SN')
        self.c.setFillColor(black)
        self.c.drawString(104*mm, 25*mm, 'Door Key')
        self.c.drawString(104*mm, 20*mm, 'Cabinet/Desk Key')
        self.c.drawString(104*mm, 15*mm, 'Card/Fob')
        self.c.drawString(104*mm, 10*mm, 'Grand Total')
        self.c.drawString(144*mm, 30*mm, 'SC')
        self.c.drawString(158*mm, 30*mm, 'Deposit')
        for x,y in [(144,25),(144,20),(144,15),(144,10),(158,25),(158,20),(158,15)]:
            self.c.drawString(x*mm, y*mm, '$')
        self._line_entry(104*mm, 1*mm, 'JV:', 5*mm, 40*mm)
        self._line_entry(152*mm, 1*mm, 'Invoice:', 13*mm, 26*mm)
        self.c.translate(0*mm, -88*mm) # origin = lower-left of the content

        # payment details
        self._header_line(82*mm, 'PAYMENT DETAILS')
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, 78*mm, 'Charge To:')
        self.c.drawString(112*mm, 78*mm, 'Refund')
        self.c.drawString(112*mm, 75*mm, 'Deposit to:')
        self.c.setFont("Helvetica", 8)
        self.c.drawString(1*mm, 75*mm, 'Department')
        self.c.drawString(68*mm, 75*mm, 'Individual')

        self._checkbox(0*mm, 70*mm, 'Deposit', offset=0.5*mm, boxheight=3.5*mm, fontsize=8)
        self._checkbox(0*mm, 66.5*mm, 'Service Charge', offset=0.5*mm, fill=1, boxheight=3.5*mm, fontsize=8)
        self._checkbox(67*mm, 70*mm, 'Deposit', offset=0.5*mm, fill=1, boxheight=3.5*mm, fontsize=8)
        self._checkbox(67*mm, 66.5*mm, 'Service Charge', offset=0.5*mm, boxheight=3.5*mm, fontsize=8)
        self._checkbox(111*mm, 70*mm, 'Department', offset=0.5*mm, boxheight=3.5*mm, fontsize=8)
        self._checkbox(111*mm, 66.5*mm, 'Individual', offset=0.5*mm, boxheight=3.5*mm, fontsize=8)

        self.c.setFont("Helvetica-Bold", 8)
        self._line_entry(1*mm, 63*mm, 'Account Code:', 21*mm, 36*mm, entry_text=str(grad.program.unit.config.get('card_account', '')))

        # find a sensible person to sign the form
        signers = list(Role.objects_fresh.filter(unit=grad.program.unit, role='ADMN').order_by('-id')) + list(Role.objects_fresh.filter(unit=grad.program.unit, role='GRPD').order_by('-id'))
        sgn_name = ''
        sgn_userid = ''
        sgn_phone = ''
        for role in signers:
            import PIL
            try:
                sig = Signature.objects.get(user=role.person)
                sig.sig.open('rb')
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                hei = 7*mm
                wid = 1.0*width/height * hei
                sig.sig.open('rb')
                ir = ImageReader(sig.sig)
                self.c.drawImage(ir, x=24*mm, y=27*mm, width=wid, height=hei)
                # info about the person who is signing it (for use below)
                sgn_name = role.person.name()
                sgn_userid = role.person.userid
                sgn_phone = role.person.phone_ext() or grad.program.unit.config.get('tel', '')
                break
            except Signature.DoesNotExist:
                pass

        # authorization details
        self._header_line(58*mm, 'AUTHORIZATION DETAILS')
        self.c.setFont("Helvetica", 7)
        self.c.drawString(0*mm, 53*mm, 'I understand that by signing and submitting this request that that the person listed above is required to pick-up their')
        self.c.drawString(0*mm, 50*mm, 'key/card/fob from Access Control WMC 3101 within 30 days unless details are supplied in additional information field above.')
        self._line_entry(1*mm, 40*mm, 'Date', 9*mm, 22*mm, entry_text=datetime.date.today().isoformat())
        self._line_entry(36*mm, 40*mm, 'Department', 22*mm, 125*mm, entry_text=grad.program.unit.name)
        self._line_entry(1*mm, 34*mm, 'Authorized by', 31*mm, 41*mm, entry_text=sgn_name)
        self._line_entry(77*mm, 34*mm, 'Computing ID', 22*mm, 36*mm, entry_text=sgn_userid)
        self._line_entry(1*mm, 27*mm, 'Signature', 22*mm, 50*mm, entry_text='')
        self._line_entry(77*mm, 27*mm, 'Phone #', 22*mm, 36*mm, entry_text=sgn_phone)

        # signatures
        self._header_line(23*mm, 'READ & SIGN AT TIME OF PICK-UP')
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, 20*mm, 'Please read the following before signing:')
        self.c.setFont("Helvetica", 7)
        self.c.drawString(1*mm, 17.5*mm, '\u2022 I acknowledge that cards, fobs and keys are the property of SFU and are issued for my own use.')
        self.c.drawString(1*mm, 15*mm, '\u2022 Items issued will not be passed on to another person and will be returned to this office ONLY')
        self.c.drawString(1*mm, 12.5*mm, '\u2022 Lost or Found cards/fobs/keys must be reported or returned to Campus Security TC 050 (778-782-3100).')
        self.c.drawString(1*mm, 10*mm, '\u2022 Policy AD 1-4 applies')
        self.c.setLineWidth(2)
        self.c.line(45*mm, 2*mm, 90*mm, 2*mm)
        self.c.line(94*mm, 2*mm, 116*mm, 2*mm)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(45*mm, -1*mm, 'Card / key holder signature')
        self.c.drawString(94*mm, -1*mm, 'Date')

        self.c.showPage()


class CardReqForm_old(object):
    # old version of the form: keep until we're sure it's gone, Nov 2013
    LINE_WIDTH = 1

    def __init__(self, outfile):
        """
        Create Card Requisition Form(s) in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)

    def save(self):
        self.c.save()

    def title_font(self):
        self.c.setFont("Helvetica-Bold", 12)
    def label_font(self):
        self.c.setFont("Helvetica", 12)
    def entry_font(self):
        self.c.setFont("Helvetica-Bold", 10)

    def check_label(self, x, y, label, fill=False):
        self.label_font()
        self.c.setLineWidth(0.4)
        self.c.rect(x, y, 3*mm, 3*mm, fill=0)
        self.c.setLineWidth(self.LINE_WIDTH)
        if fill:
            self.c.line(x, y, x+3*mm, y+3*mm)
            self.c.line(x+3*mm, y, x, y+3*mm)
        self.c.drawString(x+8*mm, y, label)


    def draw_form(self, grad):
        """
        Generates card requisition form for this grad
        """
        self.c.setStrokeColor(black)
        self.c.translate(23*mm, 12*mm) # origin = lower-left of the main box
        main_width = 166*mm
        self.c.setStrokeColor(black)
        self.c.setFillColor(black)
        self.c.setLineWidth(self.LINE_WIDTH)

        # top header
        self.title_font()
        self.c.drawString(0*mm, 251*mm, "SIMON FRASER UNIVERSITY")
        self.c.drawString(0*mm, 246*mm, "CARD REQUISITION")
        self.c.drawString(118*mm, 258*mm, "CARD NO.")
        self.c.rect(118*mm, 250*mm, 47*mm, 6.5*mm, fill=0)
        for i in range(1,6):
            self.c.line(118*mm + i*47.0/6*mm, 250*mm, 118*mm + i*47.0/6*mm, 256.5*mm)
        self.check_label(118*mm, 244*mm, 'New Issue', fill=True)
        self.check_label(118*mm, 238*mm, 'Addendum')

        # basic info
        self.label_font()
        self.c.drawString(0, 235*mm, 'Department:')
        self.c.line(25*mm, 235*mm, 89*mm, 235*mm)
        self.c.drawString(0, 223*mm, 'Last Name:')
        self.c.line(23*mm, 223*mm, 89*mm, 223*mm)
        self.c.drawString(0, 217.5*mm, 'Given Names:')
        self.c.line(28*mm, 217.5*mm, 89*mm, 217.5*mm)
        self.c.drawString(0, 212*mm, 'ID No.:')
        self.c.line(14*mm, 212*mm, 89*mm, 212*mm)

        self.entry_font()
        self.c.drawString(29*mm, 236*mm, grad.program.unit.informal_name())
        self.c.drawString(29*mm, 224*mm, grad.person.last_name)
        self.c.drawString(29*mm, 218.5*mm, grad.person.first_name)
        self.c.drawString(29*mm, 213*mm, str(grad.person.emplid))

        # traffic and security use box
        self.title_font()
        self.c.setLineWidth(self.LINE_WIDTH)
        self.c.setFillColor(CMYKColor(0, 0, 0, .2))
        self.c.rect(main_width-69*mm, 208*mm, 69*mm, 28*mm, fill=1)
        self.c.setFillColor(black)
        self.c.drawString(99*mm, 229*mm, 'TRAFFIC & SECURITY')
        self.c.drawString(99*mm, 223*mm, 'OFFICE USE ONLY')
        self.label_font()
        self.c.drawString(99*mm, 218*mm, 'Service Charge')
        self.c.drawString(132*mm, 218*mm, '$')
        self.c.line(135*mm, 218*mm, 161*mm, 218*mm)
        self.c.drawString(99*mm, 213*mm, 'Deposit')
        self.c.drawString(132*mm, 213*mm, '$')
        self.c.line(135*mm, 213*mm, 161*mm, 213*mm)

        self.c.line(0, 208*mm, main_width, 208*mm)

        # charge to/refund
        self.title_font()
        self.c.drawString(0*mm, 196.5*mm, 'CHARGE TO:')
        self.c.drawString(0*mm, 190*mm, 'Individual')
        self.c.drawString(50*mm, 190*mm, 'Department')
        self.c.drawString(110*mm, 196.5*mm, 'REFUND:')

        self.check_label(0*mm, 182*mm, 'Deposit', fill=True)
        self.check_label(0*mm, 174.5*mm, 'Service Charge')
        self.check_label(50*mm, 182*mm, 'Deposit')
        self.check_label(50*mm, 174.5*mm, 'Service Charge', fill=True)
        self.check_label(110*mm, 182*mm, 'Individual', fill=True)
        self.check_label(110*mm, 174.5*mm, 'Department')

        # account code
        self.title_font()
        self.c.drawString(0*mm, 163*mm, 'Account Code')
        self.c.rect(30*mm, 162*mm, 68*mm, 6.5*mm, fill=0)
        for i in range(12):
            h = 3*mm
            if i == 8:
                h = 6.5*mm
            x = 30*mm + i*68.0/12*mm
            self.c.line(x, 162*mm, x, 162*mm+h)

        self.entry_font()
        acct = grad.program.unit.config.get('card_account', '')
        for i,c in enumerate(str(acct)):
            x = 32*mm + i*68.0/12*mm
            self.c.drawString(x, 163*mm, c)

        self.c.line(0, 157*mm, main_width, 157*mm)

        # classification
        self.title_font()
        self.c.drawString(0*mm, 148*mm, 'CLASSIFICATION')
        self.check_label(13*mm, 140*mm, 'Staff')
        self.check_label(51*mm, 140*mm, 'Faculty')
        self.check_label(89*mm, 140*mm, 'RA')
        self.check_label(128*mm, 140*mm, 'Visitor')
        self.check_label(13*mm, 133*mm, 'Undergrad')
        self.check_label(51*mm, 133*mm, 'Graduate', fill=True)
        self.check_label(89*mm, 133*mm, '_____________')

        self.c.drawString(0*mm, 123*mm, 'EMPLOYEE GROUP')
        self.check_label(13*mm, 115*mm, 'CUPE')
        self.check_label(51*mm, 115*mm, 'APSA')
        self.check_label(89*mm, 115*mm, 'Student', fill=True)
        self.check_label(128*mm, 115*mm, 'Polyparty')
        self.check_label(13*mm, 108*mm, 'Contract')
        self.check_label(51*mm, 108*mm, 'TSSU')
        self.check_label(89*mm, 108*mm, 'SFUFA')
        self.check_label(128*mm, 108*mm, '____________')

        self.c.line(0, 102*mm, main_width, 102*mm)

        # areas
        self.title_font()
        self.c.drawString(0*mm, 95*mm, 'AREAS')
        self.c.drawString(80*mm, 95*mm, 'SCHEDULE')
        self.c.setFont("Helvetica", 10)
        self.c.drawString(0*mm, 88*mm, 'Room #/Door #')
        self.c.drawString(80*mm, 88*mm, '24 Hr.')
        self.c.drawString(100*mm, 88*mm, 'M-F 8:30-4:30')
        self.c.drawString(130*mm, 88*mm, 'Other Days/Times')
        for i in range(3):
            y = 82*mm - i*5.5*mm
            self.c.rect(0*mm, y, 75*mm, 5.5*mm, fill=0)
            self.check_label(82*mm, y+1*mm, '', fill=True)
            self.check_label(108*mm, y+1*mm, '')
            self.c.line(130*mm, y, 166*mm, y)


        self.entry_font()
        rooms = grad.program.unit.config.get('card_rooms', '').split("|")
        for i,rm in enumerate(rooms):
            y = 83*mm - i*5.5*mm
            self.c.drawString(1*mm, y, rm)

        # find a sensible person to sign the form
        signers = list(Role.objects_fresh.filter(unit=grad.program.unit, role='ADMN').order_by('-id')) + list(Role.objects_fresh.filter(unit=grad.program.unit, role='GRPD').order_by('-id'))
        for role in signers:
            import PIL
            try:
                sig = Signature.objects.get(user=role.person)
                sig.sig.open('rb')
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                hei = 7*mm
                wid = 1.0*width/height * hei
                sig.sig.open('rb')
                ir = ImageReader(sig.sig)
                self.c.drawImage(ir, x=114*mm, y=50*mm, width=wid, height=hei)
                break
            except Signature.DoesNotExist:
                pass

        # dates and signature
        self.title_font()
        self.c.drawString(0*mm, 57*mm, 'Effective Date:')
        self.c.line(32*mm, 57*mm, 74*mm, 57*mm)
        self.c.drawString(80*mm, 57*mm, 'Expiry Date:')
        self.c.line(106*mm, 57*mm, 166*mm, 57*mm)
        self.c.drawString(0*mm, 51*mm, 'Date:')
        self.c.line(13*mm, 51*mm, 74*mm, 51*mm)
        self.c.drawString(80*mm, 51*mm, 'Authorized By:')
        self.c.line(113*mm, 51*mm, 166*mm, 51*mm)

        self.entry_font()
        today = datetime.date.today()
        expiry = today + datetime.timedelta(days=365*5+1)
        self.c.drawString(34*mm, 58*mm, today.strftime("%B %d, %Y"))
        self.c.drawString(108*mm, 58*mm, expiry.strftime("%B %d, %Y"))
        self.c.drawString(34*mm, 52*mm, today.strftime("%B %d, %Y"))

        self.c.setDash(6,3)
        self.c.line(0, 46*mm, main_width, 46*mm)

        # rules and signature
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(0*mm, 40*mm, "Please read the following before signing:")
        self.c.setFont("Helvetica", 10)
        self.c.drawString(0*mm, 35*mm, "\u2022 THIS CARD IS FOR MY OWN USE.")
        self.c.drawString(0*mm, 30*mm, "\u2022 IT REMAINS THE POPERTY OF SFU.")
        self.c.drawString(0*mm, 25*mm, "\u2022 IT WILL NOT BE PASSED ON TO ANOTHER PERSON")
        self.c.drawString(0*mm, 20*mm, "\u2022 IT WILL BE RETURNED TO THIS OFFICE ONLY, WHEN NO LONGER OF USE TO MYSELF.")

        self.c.setDash(1)
        self.c.line(0, 5*mm, 62*mm, 5*mm)
        self.c.line(69*mm, 5*mm, 136*mm, 5*mm)
        self.c.drawString(0*mm, 0*mm, "SIGNATURE")
        self.c.drawString(69*mm, 0*mm, "DATE")

        self.c.showPage()

def card_req_forms(grads, outfile):
    doc = CardReqForm(outfile)
    for g in grads:
        doc.draw_form(g)
    doc.save()


class FASnetForm(object):
    ENTRY_HEIGHT = 10*mm
    LEGAL_STYLE = ParagraphStyle(name='Normal',
                                fontName='Times-Roman',
                                fontSize=10,
                                leading=11,
                                alignment=TA_LEFT,
                                borderPadding=0,
                                textColor=black)
    TINYLEGAL_STYLE = ParagraphStyle(name='Normal',
                                fontName='Times-Roman',
                                fontSize=8,
                                leading=8,
                                alignment=TA_LEFT,
                                textColor=black)


    def __init__(self, outfile):
        """
        Create FASnet account form in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)
        self.legal = open(os.path.join(settings.BASE_DIR, 'external', 'sfu', 'fasnet_legal.txt')).read()

    def save(self):
        self.c.save()

    def label_font(self):
        self.c.setFont("Times-Roman", 14)
    def entry_font(self):
        self.c.setFont("Helvetica", 12)

    def check_label(self, x, y, label, fill=False):
        self.label_font()
        self.c.setLineWidth(0.4)
        self.c.rect(x, y, 3*mm, 3*mm, fill=0)
        if fill:
            self.c.line(x, y, x+3*mm, y+3*mm)
            self.c.line(x+3*mm, y, x, y+3*mm)
        self.c.drawStringRight(x-2*mm, y, label)

    def label_blank(self, x, y, label, value='', labelwidth=40*mm, linelength=70*mm, fill=False):
        self.label_font()
        self.c.drawString(x, y, label+":")
        self.c.setLineWidth(0.4)
        self.c.line(x+labelwidth, y-1*mm, x+labelwidth+linelength, y-1*mm)
        self.entry_font()
        self.c.drawString(x+labelwidth+2*mm, y, value)


    def draw_form(self, grad):
        """
        Generates card requisition form for this grad
        """
        self.c.setStrokeColor(black)
        self.c.translate(23*mm, 12*mm) # origin = lower-left of the main box
        main_width = 180*mm
        self.c.setStrokeColor(black)
        self.c.setFillColor(black)
        self.c.setLineWidth(0.5)

        # for form itself

        # top header
        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawCentredString(main_width/2, 243*mm, 'SIMON FRASER UNIVERSITY')
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawCentredString(main_width/2, 236*mm, 'FASnet Account Application')

        # the blanks
        base_y = 220*mm
        self.label_blank(0*mm, base_y, 'Campus Userid', grad.person.userid or '')
        self.label_blank(0*mm, base_y - 1*self.ENTRY_HEIGHT, 'Family Name', grad.person.last_name)
        self.label_blank(0*mm, base_y - 2*self.ENTRY_HEIGHT, 'Given Name(s)', grad.person.first_name)
        self.label_blank(0*mm, base_y - 3*self.ENTRY_HEIGHT, 'Student Number', str(grad.person.emplid))

        self.label_blank(0*mm, base_y - 5*self.ENTRY_HEIGHT, 'Account Type', 'Graduate Student')
        self.label_blank(0*mm, base_y - 6*self.ENTRY_HEIGHT, 'Department', grad.program.unit.informal_name())

        self.label_blank(0*mm, base_y - 7*self.ENTRY_HEIGHT, 'Groups', 'cs_grads group')
        self.label_blank(0*mm, base_y - 8*self.ENTRY_HEIGHT, 'Research Lab(s)', '')
        self.label_blank(0*mm, base_y - 9*self.ENTRY_HEIGHT, 'Home Directory', '/cs/grad1,2,3')
        self.label_blank(0*mm, base_y - 10*self.ENTRY_HEIGHT, 'Platforms', 'Unix & Windows')

        # find a sensible person to sign the form
        signers = list(Role.objects_fresh.filter(unit=grad.program.unit, role='GRAD').order_by('-id')) \
                  + list(Role.objects_fresh.filter(unit=grad.program.unit, role='ADMN').order_by('-id')) \
                  + list(Role.objects_fresh.filter(unit=grad.program.unit, role='GRPD').order_by('-id'))
        for role in signers:
            import PIL
            try:
                sig = Signature.objects.get(user=role.person)
                sig.sig.open('rb')
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                hei = 10*mm
                wid = 1.0*width/height * hei
                sig.sig.open('rb')
                ir = ImageReader(sig.sig)
                self.c.drawImage(ir, x=45*mm, y=base_y - 15*self.ENTRY_HEIGHT, width=wid, height=hei)
                self.entry_font()
                self.c.drawString(42*mm, base_y - 12*self.ENTRY_HEIGHT, role.person.name())
                break
            except Signature.DoesNotExist:
                pass

        self.label_blank(0*mm, base_y - 12*self.ENTRY_HEIGHT, 'Sponsor', '')
        self.label_blank(0*mm, base_y - 13*self.ENTRY_HEIGHT, 'Expiry', '4 years')

        self.label_blank(0*mm, base_y - 15*self.ENTRY_HEIGHT, 'Sponsor Signature', '')
        self.label_blank(0*mm, base_y - 16*self.ENTRY_HEIGHT, 'Date', datetime.date.today().strftime("%B %d, %Y"))

        self.c.showPage()

        # page 2: leagalese

        p = Paragraph("In using information resources at Simon Fraser University you are agreeing to comply with policies and procedures as specified in Simon Fraser University's Policies and Procedures document GP24 and any other University/Departmental policies. The following is an excerpt from GP24.",
                  self.LEGAL_STYLE)
        f = Frame(0.5*inch, 0.5*inch, 7.5*inch, 10*inch)
        f.addFromList([p], self.c)

        content = []
        for txt in self.legal.split('\n\n'):
            content.append(Spacer(1, 5))
            p = Paragraph(txt, self.TINYLEGAL_STYLE)
            content.append(p)

        f = Frame(0.75*inch, 1*inch, 7*inch, 9*inch)
        f.addFromList(content, self.c)

        self.label_blank(0.5*inch, 1*inch, 'Signature of Applicant', '', labelwidth=48*mm, linelength=60*mm)
        self.label_blank(125*mm, 1*inch, 'Date', '', labelwidth=14*mm, linelength=40*mm)

        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawCentredString(4.25*inch, 0.7*inch, 'Please drop off completed form at the Dean of Applied Science Office (ASB 9861).')
        self.c.drawCentredString(4.25*inch, 0.5*inch, 'For account related inquiries please email helpdesk@fas.sfu.ca.')

        self.c.showPage()


def fasnet_forms(grads, outfile):
    doc = FASnetForm(outfile)
    for g in grads:
        doc.draw_form(g)
    doc.save()


class FormMixin(object):
    def __init__(self, outfile):
        """
        Create form in the file object (which could be a Django HttpResponse).
        This is the base class, there are various subclasses for different forms.
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)

    def save(self):
        self.c.save()

    def checkbox(self, x, y, filled=0):
        self.c.rect(x*mm, y*mm, 3.1*mm, 3.8*mm, fill=filled)

    def rect(self, x, y, width, height, filled=0):
        self.c.rect(x*mm, y*mm, width*mm, height*mm, fill=filled)

    def header_label(self, x, y, content):
        if content:
            self.c.setFont("Helvetica-Bold", 9)
            self.c.drawString(x*mm, y*mm, content)

    def header_label_italics(self, x, y, content):
        if content:
            self.c.setFont("Helvetica-BoldOblique", 8)
            self.c.drawString(x*mm, y*mm, content)

    def header_label_large(self, x, y, content):
        if content:
            self.c.setFont("Helvetica-Bold", 12)
            self.c.drawString(x * mm, y * mm, content)

    def header_label_large_nobold(self, x, y, content):
        if content:
            self.c.setFont("Helvetica", 12)
            self.c.drawString(x * mm, y * mm, content)

    def label(self, x, y, content):
        if content:
            self.c.setFont("Helvetica", 9)
            self.c.drawString(x*mm, y*mm, content)

    def label_mid(self, x, y, content):
        if content:
            self.c.setFont("Helvetica", 8)
            self.c.drawString(x*mm, y*mm, content)

    def label_mid_bold(self, x, y, content):
        if content:
            self.c.setFont("Helvetica-Bold", 8)
            self.c.drawString(x*mm, y*mm, content)

    def label_small(self, x, y, content):
        if content:
            self.c.setFont("Helvetica", 7)
            self.c.drawString(x*mm, y*mm, content)

    def subscript_label(self, x, y, content):
        if content:
            self.c.setFont("Helvetica", 6)
            self.c.drawString(x*mm, y*mm, content)

    def subscript_small_label(self, x, y, content):
        if content:
            self.c.setFont("Helvetica", 5)
            self.c.drawString(x*mm, y*mm, content)

    def subscript_small_label_bold(self, x, y, content):
        if content:
            self.c.setFont("Helvetica-Bold", 5)
            self.c.drawString(x * mm, y * mm, content)
        
    def subscript_tiny_label(self, x, y, content):
        if content:
            self.c.setFont("Helvetica", 4)
            self.c.drawString(x*mm, y*mm, content)

    def hdouble_line(self, x1, x2, y):
        self.c.line(x1*mm, y*mm, x2*mm, y*mm)
        self.c.line(x1*mm, y*mm-0.5*mm, x2*mm, y*mm-0.5*mm)

    def hline(self, x1, x2, y):
        self.c.line(x1*mm, y*mm, x2*mm, y*mm)

    def vline(self, x, y1, y2):
        self.c.line(x*mm, y1*mm, x*mm, y2*mm)

    def label_filled(self, x, y, content):
        if content:
            self.c.setFont("Courier", 9)
            self.c.drawString(x*mm, y*mm, content)

    def label_filled_large(self, x, y, content):
        if content:
            self.c.setFont("Courier", 11)
            self.c.drawString(x*mm, y*mm, content)

    def label_filled_centred(self, x, y, content):
        if content:
            self.c.setFont("Courier", 9)
            self.c.drawCentredString(x*mm, y*mm, content)

    def label_filled_small(self, x, y, content):
        if content:
            self.c.setFont("Courier", 8)
            self.c.drawString(x * mm, y * mm, content)


class YellowFormTenure(FormMixin):

    def draw_form(self, data):

        x_origin=15*mm
        y_origin=12*mm
        x_max=190
        self.c.translate(x_origin, y_origin) # origin = lower-left of the main box
        self.c.setStrokeColor(black)

        # Header
        self.header_label_italics(0, 254, 'UPDATED FORM: JULY 9, 1997')
        self.header_label_italics(87, 254, 'SUBMIT ORIGINAL (TYPED) YELLOW FORM TO VICE PRESIDENT ACADEMIC')
        self.c.rect(-2*mm, 245*mm, 194*mm, 5*mm)
        self.header_label(36, 246.5, 'RECOMMENDATION FOR APPOINTMENT')
        self.header_label(109, 246.5, 'TENURE TRACK FACULTY')

        # Personal information
        self.header_label(0, 240, 'PERSONAL INFORMATION:')
        self.hline(0, 42, 239.5)
        self.label(0, 235, 'Surname:')
        self.label(81, 235, 'Given:')
        self.label(144, 235, 'Preferred:')
        self.hline(16, 71, 234.5)
        self.label_filled(17, 235, data.get('last_name'))
        self.hline(90, 139, 234.5)
        self.label_filled(91, 235, data.get('first_name'))
        self.hline(158, x_max, 234.5)
        self.label_filled(159, 235, data.get('pref_first_name'))
        self.label(0, 227, 'Canadian SIN:')
        self.label(81, 227, 'Date of Birth: ')
        self.label(102, 227, 'Yr')
        self.label(117, 227, 'Mo')
        self.label(134, 227, 'Day')
        self.label(148, 227, 'Gender:')
        self.label(163.5, 227, 'M')
        self.label(175, 227, 'F')
        self.hline(30, 32, 228.5)
        self.hline(38, 40, 228.5)
        self.hline(107, 117, 226.5)
        self.hline(124, 133, 226.5)
        self.hline(140, 147, 226.5)
        # Add SIN to the form if it's exactly 9 digits to avoid out-of-range index issues
        sin = str(data.get('sin'))
        if len(sin) == 9:
            self.label_filled(24, 227, sin[0:3])
            self.label_filled(32.5, 227, sin[3:6])
            self.label_filled(40.5, 227, sin[6:9])
        # See if we have a FacultyMemberInfo record for this person so we may have a birthdate.
        dob = data.get('dob')
        if dob:
            self.label_filled(108, 227, str(dob.year))
            self.label_filled(127, 227, str(dob.month))
            self.label_filled(143, 227, str(dob.day))
        self.checkbox(169, 226, data.get('gender') == 'M')
        self.checkbox(180, 226, data.get('gender') == 'F')
        self.label(0, 219.5, 'Is the Candidate a Canadian Citizen or Permanent Resident?')
        self.label(95, 219.5, 'Yes')
        self.label(111, 219.5, 'No')
        self.checkbox(104, 219)
        self.checkbox(120, 219)
        self.label(0, 214, 'Country of Citizenship:')
        self.hline(38, x_max, 213.5)
        self.label(0, 208, 'Mailing Address:')
        self.hline(38, x_max, 207.5)
        self.label(0, 203, 'Telephone:')
        self.label(83, 203, 'HOUSEHOLD moved from:')
        self.hline(33, 35, 204.5)
        self.hline(20, 76, 202.5)
        self.hline(121, x_max, 202.5)
        self.subscript_label(22, 200.5, '(area code)')
        self.subscript_label(148.5, 200.5, '(City/Country)')
        self.label_small(3, 192, 'DEGREES HELD')
        self.label_small(25, 192, 'YEAR OF DEGREE')
        self.label_small(75, 192, 'INSTITUTION')
        self.label_small(100, 192, 'CITY/COUNTRY')
        self.label_small(153, 192, 'DEGREE VERIFICATION')
        self.hline(3, 22, 191.5)
        self.hline(25, 47, 191.5)
        self.hline(75, 119, 191.5)
        self.hline(153, 181.5, 191.5)
        self.subscript_label(5, 188.5, '(or in progress)')
        self.subscript_small_label(30, 188.5, '(mark "Cand."')
        self.subscript_small_label(25.5, 186.5, 'if degree not yet complete)')
        self.label(147, 182, 'Yes')
        self.label(157, 182, 'No')
        self.label(170, 182, 'by')
        self.hline(2, 23.5, 181.5)
        self.label_filled_centred(12.5, 182, data.get('degree1'))
        self.hline(25, 47.5, 181.5)
        self.label_filled_centred(36, 182, data.get('year1'))
        self.hline(49, 145, 181.5)
        self.label_filled(49, 182, data.get('institution1'))
        self.hline(174, 187, 181.5)
        self.label_filled(100, 182, data.get('location1'))
        self.subscript_tiny_label(9.5, 180, '(Highest)')
        self.checkbox(153.5, 181.5)
        self.checkbox(162.5, 181.5)
        self.label(147, 176.5, 'Yes')
        self.label(157, 176.5, 'No')
        self.label(170, 176.5, 'by')
        self.hline(2, 23.5, 176)
        self.hline(25, 47.5, 176)
        self.hline(49, 145, 176)
        self.hline(174, 187, 176)
        self.label_filled_centred(12.5, 176.5, data.get('degree2'))
        self.label_filled_centred(36, 176.5, data.get('year2'))
        self.label_filled(49, 176.5, data.get('institution2'))
        self.label_filled(100, 176.5, data.get('location2'))
        self.checkbox(153.5, 176)
        self.checkbox(162.5, 176)
        self.label(147, 171, 'Yes')
        self.label(157, 171, 'No')
        self.label(170, 171, 'by')
        self.hline(2, 23.5, 170.5)
        self.hline(25, 47.5, 170.5)
        self.hline(49, 145, 170.5)
        self.hline(174, 187, 170.5)
        self.label_filled_centred(12.5, 171, data.get('degree3'))
        self.label_filled_centred(36, 171, data.get('year3'))
        self.label_filled(49, 171, data.get('institution3'))
        self.label_filled(100, 171, data.get('location3'))
        self.checkbox(153.5, 170.5)
        self.checkbox(162.5, 170.5)
        self.c.rect(0*mm, 168*mm, 190*mm, 29*mm)

        self.label(0, 162, 'Present position:')
        self.label(134.5, 162, 'Salary: $')
        self.hline(27, 131, 161.5)
        self.hline(147, x_max, 161.5)
        self.label(0, 156, 'Institution:')
        self.hline(27, x_max, 155.5)
        self.subscript_tiny_label(155.5, 154, '(City/Country)')

        self.label(0,149, 'Principal subject taught (see Stats Canada codes):')
        self.label(144, 149, 'Code:')
        self.hline(74, 139, 148.5)
        self.hline(153, x_max, 148)

        self.label(0, 142, 'Candidate has held position at SFU before: ')
        self.label(68.5, 142, 'Yes')
        self.label(84, 142, 'No')
        self.label(93.5, 142, 'If yes give details:')
        self.checkbox(74.5, 141)
        self.checkbox(88.5, 141)
        self.hline(123, x_max, 141)

        self.label(0, 136, 'Previous position #:')
        self.hline(32, 82, 135)
        self.hline(88, x_max, 135)

        self.hdouble_line(0, x_max, 131.5)

        # Appointment Information
        self.header_label(0,127.5, 'APPOINTMENT INFORMATION')
        self.hline(0, 47, 127)
        self.label(0, 122, 'Dept: (Home):')
        self.label(101, 122, '(2')
        self.label(106, 122, 'Dept):')
        self.subscript_tiny_label(103.7, 123.6, 'nd')
        self.hline(24, 98, 121.5)
        self.label_filled(25, 122, data.get('unit'))
        self.hline(114, x_max, 121.5)
        self.label_mid(114, 118, 'If start date is not September 1')
        self.label_mid(153.5, 118, ', which year will be')
        self.label_mid(114, 115.5, 'considered start date for renewal & tenure?')
        self.subscript_tiny_label(152.2, 119.2, 'st')
        self.label(0, 115.5, 'Start Date:')
        self.label(19, 115.5, 'Yr')
        self.label(32, 115.5, 'Mo')
        self.label(44, 115.5, 'Day')
        self.label(60.5, 115.5, 'End Date: Yr')
        self.label(89, 115.5, 'Mo')
        self.label(100.5, 115.5, 'Day')
        self.hline(22, 31.5, 115)
        self.hline(36.5, 43, 115)
        self.hline(49, 57, 115)
        self.hline(79, 88.5, 115)
        self.hline(93, 100, 115)
        self.hline(106, 114, 115)
        self.hline(180, x_max, 115)
        # Let's add the start and end dates if we have any
        start_date = data.get('start_date')
        if start_date:
            self.label_filled(23.5, 115.5, str(start_date.year))
            self.label_filled(38.5, 115.5, str(start_date.month))
            self.label_filled(51, 115.5, str(start_date.day))
        end_date = data.get('end_date')
        if end_date:
            self.label_filled(80.5, 115.5, str(end_date.year))
            self.label_filled(95, 115.5, str(end_date.month))
            self.label_filled(108, 115.5, str(end_date.day))
        self.label(0, 107.5, 'Full-Time')
        self.label(20, 107.5, 'Part-time')
        self.label(52.5, 107.5, '%')
        self.label(57, 107.5, 'Is this a replacement position?')
        self.label(104.5, 107.5, 'Yes')
        self.label(122.5, 107.5, 'CFL Position')
        self.label(143.5, 107.5, '#(1):')
        self.label(166, 107.5, 'FTE')
        self.label(184, 107.5, '%')
        self.label(143.5, 104, '#(2):')
        self.label(166, 104, 'FTE')
        self.label(184, 104, '%')
        self.checkbox(14.5, 107, True)
        self.checkbox(35, 107)
        self.hline(43, 52, 107)
        self.checkbox(112, 107)
        self.hline(150, 161, 107)
        self.hline(172.5, 183.5, 107)
        self.hline(150, 161, 103.5)
        self.hline(172.5, 183.5, 103.5)
        self.label_filled(174, 107.5, '100')
        self.label_filled(150.5, 107.5, data.get('position_number'))

        self.label(0, 100, 'Rank:')
        self.label(66, 100, 'Step:')
        self.label(81, 100, 'Market Dif:  $')
        self.label(131.5, 100, 'Start-up:  $')
        self.hline(9.5, 64.5, 99.5)
        self.hline(73.5, 79.5, 99.5)
        self.hline(99.5, 130, 99.5)
        self.hline(148, 182, 99.5)

        if data.get('rank'):
            self.label_filled(9.5, 100, data.get('rank'))
        if data.get('step'):
            self.label_filled_centred(76.5, 100, data.get('step'))

        if data.get('marketdiff'):
            self.label_filled(101, 100, data.get('marketdiff'))

        self.label(0, 94.5, 'Request appointment be concluded by:')
        self.label(118, 94.5, 'Number of teaching semesters credit, if any,')
        self.hline(168, 182, 88.5)
        self.label_filled_centred(175, 89, data.get('teaching_semester_credits'))
        self.label(3, 90.5, 'normal route')
        self.label(32, 90.5, 'or expedited route')
        self.checkbox(24, 90)
        self.checkbox(62, 90)

        self.header_label(0, 84.5, 'ATTACHMENTS:')
        self.hline(0, 25, 84)

        self.label(4.5, 79, 'Detailed recommendation for appointment')
        self.label(82, 79, 'Search procedures')
        self.label(144, 79, 'Advertisements')
        self.checkbox(0.5, 78.5)
        self.checkbox(78, 78.5)
        self.checkbox(140, 78.5)
        self.label(4.5, 73.5, 'CV\'s of shortlisted candidates')
        self.label(82, 73.5, 'Statement of employment equity')
        self.checkbox(0.5, 73)
        self.checkbox(78, 73)
        self.label(4.5, 68, 'Letter of reference for shortlisted candidates')
        self.label(82, 68, 'Assessment of teaching competence')
        self.checkbox(0.5, 67.5)
        self.checkbox(78, 67.5)

        self.hdouble_line(0, x_max, 64.5)

        # Approval
        self.header_label(0, 60.5, 'APPROVED BY:')
        self.hline(0, 24.5, 60)
        self.label(0.5, 55, 'Chair/Director:')
        self.label(136, 55, 'Date:')
        self.hline(38.5, 130, 54.5)
        self.hline(144, x_max, 54.5)
        self.label(0.5, 49, 'Dean of Faculty:')
        self.label(136, 49, 'Date:')
        self.hline(38.5, 130, 48.5)
        self.hline(144, x_max, 48.5)
        self.label(0.5, 43, 'Vice President Academic:')
        self.label(136, 43, 'Date:')
        self.hline(38.5, 130, 42.5)
        self.hline(144, x_max, 42.5)
        self.label(0.5, 37, 'President:')
        self.label(136, 37, 'Date:')
        self.hline(38.5, 130, 36.5)
        self.hline(144, x_max, 36.5)

        self.hdouble_line(0, x_max, 34)

        # Private use

        self.header_label(0, 30, 'FOR USE BY THE OFFICE OF THE VICE-PRESIDENT, ACADEMIC')
        self.subscript_label(86.5, 27.5, '(year)')
        self.label(0, 24, '1. Bi-wk. sal.')
        self.label(24, 24, '$')
        self.label(62, 24, '6.  Moving May')
        self.label(148.5, 24, '7.  Confirmation of offer of')
        self.hline(27.5, 53, 22.2)
        self.c.rect(85.5*mm, 23*mm, 8*mm, 3.8*mm)
        self.checkbox(186.5, 23.5)
        self.label(0, 19, '2. Ann. sal.')
        self.label(24, 19, '$')
        self.label(67, 19, 'a) Allowance')
        self.label(89.5, 19, '(moving within Canada)')
        self.label(153, 20.5, 'employment required')
        self.hline(27.5, 53, 18.5)
        self.checkbox(85.5, 18.5)
        self.label(0, 14.5, '3. Salary/Base')
        self.hline(27.5, 53, 13)
        self.label(0, 10, '4. Date of scale')
        self.hline(27.5, 53, 9)
        self.label(0, 5, '5. Pension:')
        self.label(29.5, 5, 'Yes')
        self.label(43, 5, 'No')
        self.checkbox(37, 4.5)
        self.checkbox(49, 4.5)
        self.header_label(62, 19.5, 'or')
        self.label(67, 14.5, 'b) Reimbursement for expenses')
        self.label(71, 10, 'distance')
        self.label(101.5, 10, 'km')
        self.header_label(110.5, 10, 'X')
        self.label(117, 10, 'rate')
        self.label(134, 10, '\xa2')
        self.header_label(137, 10, '=')
        self.label(140, 10, '$')
        self.c.line(82.5*mm,9*mm, 101*mm, 9*mm)
        self.hline(123.5, 133, 9)
        self.hline(142.5, 167.5, 9)
        self.header_label(73, 5, '+')
        self.label(76, 5, 'base')
        self.header_label(101.5, 5, '=')
        self.label(104, 5, 'Maximum $')
        self.hline(82.5, 101, 4.2)
        self.hline(122, 153.5, 4.2)
        self.header_label(62, 0, 'or')
        self.label(67, 0, 'c) Reimbursement outside North America')
        self.label(139, 0, 'Amount $')
        self.hline(153, x_max, -0.5)

        # All done, let's show the form.
        self.c.showPage()


def yellow_form_tenure(careerevent, outfile):

    doc = YellowFormTenure(outfile)
    data = build_data_from_event(careerevent)
    doc.draw_form(data)
    doc.save()


class YellowFormLimited(FormMixin):

    def checkbox(self, x, y, filled=0):
        self.c.circle(x*mm, y*mm + 1*mm, 1*mm, fill=filled)

    def draw_form(self, data):

        x_origin=13*mm
        y_origin=12*mm
        x_max=191
        self.c.translate(x_origin, y_origin)  # origin = lower-left of the main box
        self.c.setStrokeColor(black)

        # Header
        self.header_label(0.5, 256.5, '1992-11 OVPA')
        self.header_label(67, 256.5, 'RECOMMENDATION FOR APPOINTMENT')
        self.header_label(173, 256.5, 'Form No. 2')
        self.hline(67, 129.5, 256)
        self.label_mid_bold(8, 250, 'LECTURER')
        self.label_mid_bold(37, 250, 'SENIOR LECTURER')
        self.label_mid_bold(73, 250, 'CONTINUING LANGUAGE INSTRUCTOR')
        self.label_mid_bold(145.8, 250, 'CLINICAL PROFESSOR')
        self.checkbox(27.5, 250)
        self.checkbox(68.5, 250)
        self.checkbox(131, 250)
        self.checkbox(181, 250)
        self.label_mid_bold(0.5, 244, 'LAB INSTRUCTOR I')
        self.label_mid_bold(40.8, 244, 'LAB INSTRUCTOR II')
        self.label_mid_bold(81.5, 244, 'VISITING PROFESSOR')
        self.label_mid_bold(125.5, 244, 'LIMITED TERM')
        self.label_mid_bold(158.5, 244, 'RESEARCH ASSOC')
        self.checkbox(31, 244)
        self.checkbox(72, 244)
        self.checkbox(116, 244)
        self.checkbox(149.5, 244)
        self.checkbox(188.5, 244)
        self.hdouble_line(-1.5, x_max, 239.5)

        # Personal Information
        self.header_label(0.5, 236, 'PERSONAL INFORMATION:')
        self.hline(0.5, 42, 235.5)
        self.label(0.5, 230.5, 'Surname:')
        self.label(81, 230.5, 'Given:')
        self.label(145, 230.5, 'Preferred:')
        self.hline(16, 76.5, 230)
        self.label_filled(17, 230.5, data.get('last_name'))
        self.hline(91, 140, 230)
        self.label_filled(92, 230.5, data.get('first_name'))
        self.hline(159, 191, 230)
        self.label_filled(160, 230.5, data.get('pref_first_name'))
        self.label(0.5, 223, 'Canadian SIN:')
        self.label(81.5, 223, 'Date of Birth:')
        self.label(102.5, 223, 'Yr')
        self.label(119, 223, 'Mo')
        self.label(135, 223, 'Day')
        self.label(149.5, 223, 'Gender:')
        self.label(163, 223, 'M')
        self.label(176.5, 223, 'F')
        self.hline(35, 37, 224)
        self.hline(47.5, 49.5, 224)
        self.hline(24, 35, 222.5)
        self.hline(37, 47.5, 222.5)
        self.hline(49.5, 60, 222.5)
        self.hline(108, 117.5, 222.5)
        self.hline(124.5, 133.5, 222.5)
        self.hline(141.5, 147.5, 222.5)
        # Add SIN to the form if it's exactly 9 digits to avoid out-of-range index issues
        sin = str(data.get('sin'))
        if len(sin) == 9:
            self.label_filled(26, 223.5, sin[0:3])
            self.label_filled(39, 223.5, sin[3:6])
            self.label_filled(51.5, 223.5, sin[6:9])

        dob = data.get('dob')
        if dob:
            self.label_filled(109, 223, str(dob.year))
            self.label_filled(127, 223, str(dob.month))
            self.label_filled(143, 223, str(dob.day))
        self.checkbox(171.5, 223, data.get('gender') == 'M')
        self.checkbox(183.5, 223, data.get('gender') == 'F')
        self.label(0.5, 215, 'Is Candidate a Canadian Citizen or Cdn. Permanent Resident?')
        self.label(94, 215, 'Yes')
        self.label(111, 215, 'No')
        self.checkbox(104.5, 215)
        self.checkbox(121, 215)
        self.subscript_label(149.5, 216.5, 'VPA USE ONLY')
        self.label(0.5, 209, 'County of Citizenship:')
        self.header_label(142.5, 209, '/')
        self.hline(38, 142.5, 208.5)
        self.hline(145, 191, 208.5)
        self.label(0.5, 203.5, 'Address:')
        self.hline(20, 191, 203)
        self.label(0.5, 198, 'Telephone')
        self.label(83, 198, 'HOUSEHOLD moved from:')
        self.hline(21, 78, 197.5)
        self.hline(122.5, 191, 197.5)
        self.hline(33.5, 35, 199)
        self.subscript_label(22.5, 195, '(area code)')
        self.subscript_label(150, 195, '(City/Country)')
        self.label_small(3.5, 187.5, 'DEGREES HELD')
        self.label_small(26, 187.5, 'YEAR OF DEGREE')
        self.label_small(67, 187.5, 'INSTITUTION')
        self.label_small(110.5, 187.5, 'CITY/COUNTRY')
        self.subscript_label(161, 188, 'VPA USE ONLY')
        self.hline(3.5, 23, 187)
        self.hline(26, 48, 187)
        self.hline(67, 82.5, 187)
        self.hline(110.5, 129, 187)
        self.subscript_label(6, 184, '(or in progress)')
        self.subscript_label(26, 184, '(mark "Cand." if degree')
        self.subscript_label(29, 181.5, 'not yet complete)')
        self.label(146, 176.5, '/')
        self.hline(2, 24, 176)
        self.hline(26, 48, 176)
        self.hline(49.5, 146, 176)
        self.hline(148, 189, 176)
        self.label_filled_centred(13, 176.5, data.get('degree1'))
        self.label_filled_centred(36, 176.5, data.get('year1'))
        self.label_filled(49.5, 176.5, data.get('institution1'))
        self.label_filled(101, 176.5, data.get('location1'))
        self.subscript_tiny_label(10, 174.5, '(Highest)')
        self.label(146, 171, '/')
        self.hline(2, 24, 170.5)
        self.hline(26, 48, 170.5)
        self.hline(49.5, 146, 170.5)
        self.hline(148, 189, 170.5)
        self.label_filled_centred(13, 171, data.get('degree2'))
        self.label_filled_centred(36, 171, data.get('year2'))
        self.label_filled(49.5, 171, data.get('institution2'))
        self.label_filled(101, 171, data.get('location2'))
        self.label(146, 165.5, '/')
        self.hline(2, 24, 165)
        self.hline(26, 48, 165)
        self.hline(49.5, 146, 165)
        self.hline(148, 189, 165)
        self.label_filled_centred(13, 165.5, data.get('degree3'))
        self.label_filled_centred(36, 165.5, data.get('year3'))
        self.label_filled(49.5, 165.5, data.get('institution3'))
        self.label_filled(101, 165.5, data.get('location3'))
        self.label(0.5, 156.5, 'Present position:')
        self.label(135, 156.5, 'Salary: $')
        self.hline(27, 132, 156)
        self.hline(148, 191, 156)
        self.label(0.5, 151, 'Institution:')
        self.hline(27, 191, 150.5)
        self.subscript_tiny_label(157, 149, '(City/Country)')
        self.hdouble_line(0, 190.5, 145.5)

        # Position Information
        self.header_label(0.5, 141.5, 'POSITION INFORMATION:')
        self.hline(0.5, 39.5, 141)
        self.label(1, 136, 'Dept: (Home):')
        self.label(106, 136, '2')
        self.label(110, 136, 'Dept:')
        self.subscript_tiny_label(107.7, 137.5, 'nd')
        self.hline(24, 98.5, 135.5)
        self.label_filled(25, 136, data.get('unit'))
        self.hline(118, 191, 135.5)
        self.label(1, 129.5, 'Start Date:')
        self.label(19.5, 129.5, 'Yr')
        self.label(33, 129.5, 'Mo')
        self.label(44.5, 129.5, 'Day')
        self.label(61, 129.5, 'End Date:')
        self.label(77, 129.5, 'Yr')
        self.label(90, 129.5, 'Mo')
        self.label(105, 129.5, 'Day')
        self.hline(22.5, 32, 129)
        self.hline(37, 43.5, 129)
        self.hline(49.5, 58, 129)
        self.hline(80, 89, 129)
        self.hline(94, 100.5, 129)
        self.hline(110, 118, 129)
        # Let's add the start and end dates if we have any
        start_date = data.get('start_date')
        if start_date:
            self.label_filled(24, 129.5, str(start_date.year))
            self.label_filled(39.5, 129.5, str(start_date.month))
            self.label_filled(52.5, 129.5, str(start_date.day))
        end_date = data.get('end_date')
        if end_date:
            self.label_filled(81.5, 129.5, str(end_date.year))
            self.label_filled(96.5, 129.5, str(end_date.month))
            self.label_filled(112.5, 129.5, str(end_date.day))
        self.label(1,121.5, 'Full-time')
        self.label(19.5, 121.5, 'Part-Time')
        self.label(53, 121.5, '%')
        self.label(61, 121.5, 'Is this a replacement position?')
        self.label(104.5, 121.5, 'Yes')
        self.label(129.5, 121.5, 'Position')
        self.label(144.5, 121.5, '# :')
        self.checkbox(15.5, 121.5, True)
        self.checkbox(35.5, 121.5)
        self.checkbox(113, 121.5)
        self.hline(43, 52.5, 121)
        self.hline(151, 191, 121)
        self.label_filled(44.5, 121.5, '100')
        self.label_filled(152, 121.5, data.get('position_number'))
        self.label(1, 114.5, 'New Position ?')
        self.label(27.5, 114.5, 'Yes')
        self.label(45, 114.5, 'Fund')
        self.label(55, 114.5, ':')
        self.label(104, 114.5, 'Centre :')
        self.label_mid(142, 114.5, 'Funding source :')
        self.checkbox(40, 114.5)
        self.hline(57.5, 103.5, 114)
        self.hline(116, 141.5, 114)
        self.hline(163, 191, 114)
        self.label(1, 105.5, 'Rank:')
        self.label(120.5, 105.5, 'Step:')
        self.hline(10, 80, 105)
        self.hline(130.5, 191, 105)
        if data.get('rank'):
            self.label_filled(11, 105.5, data.get('rank'))
        if data.get('step'):
            self.label_filled_centred(160, 105.5, data.get('step'))

        self.label(1, 100, 'Principal subject taught (see Stats Canada codes) :')
        self.subscript_label(165, 102, 'VPA USE ONLY :')
        self.header_label(153, 99.5, '/')
        self.hline(75.5, 153, 97.5)
        self.hline(155.5, 190, 97.5)
        self.label(1, 90.5, 'Candidate has held position at SFU before :')
        self.label(76.5, 90.5, 'Yes')
        self.label(93.5, 90.5, 'No')
        self.label(109.5, 90.5, 'If yes, give details :')
        self.checkbox(87, 90.5)
        self.checkbox(103.5, 90.5)
        self.hline(140, 191, 90)
        self.label(115.5, 85, 'Previous position # :')
        self.hline(1, 115, 81)
        self.hline(147.5, 191, 81)
        self.label(1, 76, 'Continuing Language Instructors ONLY :  Number of base units per semester :')
        self.hline(118, 154.5, 75)
        self.hdouble_line(0, 191, 70.5)

        # Approved
        self.header_label(0.5, 66.5, 'APPROVED BY:')
        self.hline(0.5, 24.5, 66)
        self.label(1, 60.5, 'Chair/Director:')
        self.label(137.5, 60.5, 'Date:')
        self.hline(38.5, 131, 60)
        self.hline(145, 191, 60)
        self.label(1, 54.5, 'Dean of Faculty:')
        self.label(137.5, 54.5, 'Date:')
        self.hline(38.5, 131, 54)
        self.hline(145, 191, 54)
        self.label(1, 48.5, 'Vice President Academic:')
        self.label(137.5, 48.5, 'Date:')
        self.hline(38.5, 131, 48)
        self.hline(145, 191, 48)
        self.hdouble_line(0, 191, 45.5)

        # Private use
        self.header_label(0.5, 41.5, 'FOR USE BY THE OFFICE OF THE VICE-PRESIDENT, ACADEMIC:')
        self.hline(0.5, 99, 41)
        self.subscript_label(87.5, 38.5, '(year)')
        self.label(0.5, 35.5, '1. Bi-wk. sal.')
        self.label(24.5, 35.5, '$')
        self.label(63, 35.5, '6.')
        self.label(67.5, 35.5, 'Moving May')
        self.label(95.5, 35.5, 'scale')
        self.label(150, 35.5, '7.')
        self.label(154.5, 35.5, 'Confirmation of offer of')
        self.checkbox(189, 35.5)
        self.hline(27.5, 53, 33.2)

        self.label(0.5, 30, '2. Ann. sal.')
        self.label(24.5, 30, '$')
        self.label(67.5, 30, 'a) Allowance')
        self.checkbox(88, 30)
        self.label(90.5, 30, '(moving within Canada)')
        self.label(154.5, 32.5, 'employment required')
        self.hline(27.5, 53, 28.5)

        self.label(0.5, 24.5, '3. Salary/Base')
        self.header_label(63, 24.5, 'or')
        self.label(67.5, 24.5, 'b) Reimbursement for expenses')
        self.checkbox(115, 24.5)
        self.hline(27.5, 53, 23)

        self.label(0.5, 19.5, '4. Date of scale')
        self.label(70.5, 19.5, 'distance')
        self.label(102.5, 19.5, 'km')
        self.header_label(111.5, 19.5, 'X')
        self.label(117.5, 19.5, 'rate(')
        self.label(135, 19.5, '\xa2')
        self.label(136.5, 19.5, ')')
        self.header_label(138.5, 19.5, '=')
        self.label(141, 19.5, '$')
        self.hline(27.5, 53, 19)
        self.hline(83, 102, 19)
        self.hline(124.5, 134, 19)
        self.hline(143.5, 169, 19)

        self.label(0.5, 15, '5. Pension:')
        self.label(30, 15, 'Yes')
        self.label(43.5, 15, 'No')
        self.header_label(73, 15, '+')
        self.label(76, 15, 'base')
        self.header_label(102.5, 15, '=')
        self.label(105.5, 15, 'Maximum $')
        self.checkbox(38.5, 15)
        self.checkbox(51.5, 15)
        self.hline(83, 102, 14)
        self.hline(122, 154.5, 14)

        self.header_label(63, 10, 'or')
        self.label(67.5, 10, 'c) Reimbursement outside North America')
        self.checkbox(132, 10)
        self.label(139.5, 10, 'Amount: $')
        self.hline(154.5, 191, 9)
        self.label(67.5, 5.5, 'd) Reimbursement : Double return economy')
        self.checkbox(132, 5.5)
        self.label(139.5, 5.5, 'Amount: $')
        self.hline(154.5, 191, 4.5)
        self.label(94.5, 1, ': Single return economy')
        self.checkbox(132, 1)
        self.label(139.5, 1, 'Amount: $')
        self.hline(154.5, 191, 0)


        # All done, show the page
        self.c.showPage()


def yellow_form_limited(careerevent,  outfile):
    doc = YellowFormLimited(outfile)
    data = build_data_from_event(careerevent)
    doc.draw_form(data)
    doc.save()


def build_data_from_event(careerevent):
    """
    This builds the correct data object for our Appointment Forms (AKA Yellow Forms) to be generated if coming
    from a careerevent.

    :param CareerEvent careerevent: The event that called this generation
    :type: CareerEvent
    :return: a dict containing all the data necessary for the form generation
    :rtype: dict
    """
    # We have to put this import here to avoid a circular import problem.
    # This is horrible, but the best solution without refactoring everything.
    from faculty.models import FacultyMemberInfo, CareerEvent
    data = {}
    event = careerevent.event
    person = event.person

    data['last_name'] = person.last_name or ''
    data['first_name'] = person.first_name or ''
    data['pref_first_name'] = person.pref_first_name or ''
    data['sin'] = person.sin()
    if(FacultyMemberInfo.objects.filter(person=person)).exists():
            f = FacultyMemberInfo.objects.get(person=person)
            dob = f.birthday
            data['dob'] = dob
    data['gender'] = person.gender() or ''
    data['degree1'] = event.config.get('degree1') or ''
    data['year1'] = event.config.get('year1') or ''
    data['institution1'] = event.config.get('institution1') or ''
    data['location1'] = event.config.get('location1') or ''
    data['degree2'] = event.config.get('degree2') or ''
    data['year2'] = event.config.get('year2') or ''
    data['institution2'] = event.config.get('institution2') or ''
    data['location2'] = event.config.get('location2') or ''
    data['degree3'] = event.config.get('degree3') or ''
    data['year3'] = event.config.get('year3') or ''
    data['institution3'] = event.config.get('institution3') or ''
    data['location3'] = event.config.get('location3') or ''
    data['unit'] = event.unit.informal_name()
    data['start_date'] = event.start_date
    data['end_date'] = event.end_date
    data['position_number'] = event.config.get('position_number') or ''
    # Let's get the current salary event(s) for this person so we can get the rank and step
    salaries = CareerEvent.objects.filter(person=person, event_type='SALARY', unit=event.unit).effective_now()
    if salaries:
        # There should only be one of these effective in this unit, but just in case
        s = salaries[0]
        data['rank'] = s.get_handler().get_rank_display() or ''
        data['step'] = s.config.get('step') or ''

    data['teaching_semester_credits'] = event.config.get('teaching_semester_credits') or ''

    stipends = CareerEvent.objects.filter(person=person, event_type='STIPEND', unit=event.unit).effective_now()
    for stipend in stipends:
        if stipend.config.get('source') == 'MARKETDIFF':
            data['marketdiff'] = stipend.config.get('amount') or ''
            break
    return data


def build_data_from_position(position):
    """
    This builds the correct data object for our Appointment Forms (AKA Yellow Forms) to be generated if coming
    from a Position with a future candidate already set.

    :param Position position: The position that called this generation
    :type: Position
    :return: a dict containing all the data necessary for the form generation
    :rtype: dict
    """
    # We have to put this import here to avoid a circular import problem.
    # This is horrible, but the best solution without refactoring everything.
    from faculty.models import FacultyMemberInfo, CareerEvent
    from faculty.event_types.career import RANK_CHOICES

    data = {}
    person = position.any_person.get_person()
    data['last_name'] = person.last_name or ''
    data['first_name'] = person.first_name or ''
    data['pref_first_name'] = person.pref_first_name or ''
    data['sin'] = person.sin()

    # If this is a real Faculty member in our system, he/she may have
    # a DOB in the FacultyMemberInfo
    if isinstance(person, Person) and FacultyMemberInfo.objects.filter(person=person).exists():
            f = FacultyMemberInfo.objects.get(person=person)
            dob = f.birthday
            data['dob'] = dob

    # Otherwise, we may have it in that object's config.
    if not data.get('dob'):
        if person.birthdate():
            data['dob'] = datetime.datetime.strptime(person.birthdate(), "%Y-%m-%d")
    data['gender'] = person.gender() or ''
    data['degree1'] = position.degree1 or ''
    data['year1'] = position.year1 or ''
    data['institution1'] = position.institution1 or ''
    data['location1'] = position.location1 or ''
    data['degree2'] = position.degree2 or ''
    data['year2'] = position.year2 or ''
    data['institution2'] = position.institution2 or ''
    data['location2'] = position.location2 or ''
    data['degree3'] = position.degree3 or ''
    data['year3'] = position.year3 or ''
    data['institution3'] = position.institution3 or ''
    data['location3'] = position.location3 or ''
    data['unit'] = position.unit.informal_name()
    data['start_date'] = position.projected_start_date
    data['end_date'] = ''
    data['position_number'] = position.position_number
    data['rank'] = RANK_CHOICES.get(position.rank, '')
    if position.step:
        data['step'] = str(position.step)
    else:
        data['step'] = ''

    if position.teaching_semester_credits:
        data['teaching_semester_credits'] = str(position.teaching_semester_credits)
    else:
        data['teaching_semester_credits'] = ''

    # For now, we store marketdiffs only for real faculty members, but let's add this here in case.  Either way, if we
    # call this method from a position where the FuturePerson is now a real Faculty Member, this should still work.

    if isinstance(person, Person):
        stipends = CareerEvent.objects.filter(person=person, event_type='STIPEND', unit=position.unit).effective_now()
        for stipend in stipends:
            if stipend.config.get('source') == 'MARKETDIFF':
                data['marketdiff'] = stipend.config.get('amount') or ''
                break

    return data


def position_yellow_form_limited(position,  outfile):
    doc = YellowFormLimited(outfile)
    data = build_data_from_position(position)
    doc.draw_form(data)
    doc.save()


def position_yellow_form_tenure(position, outfile):

    doc = YellowFormTenure(outfile)
    data = build_data_from_position(position)
    doc.draw_form(data)
    doc.save()


class SessionalForm(FormMixin, SFUMediaMixin):
    NOTE_STYLE = ParagraphStyle(name='Normal',
                            fontName='Courier',
                            fontSize=6.6,
                            leading=6,
                            textColor=black)

    
    def __init__(self, *args, **kwargs):
        super(SessionalForm, self).__init__(*args, **kwargs)
        self._media_setup()

    def checkbox(self, x, y, filled=0):
        self.c.rect(x * mm, y * mm, 3.1 * mm, 3.1 * mm, fill=filled)

    def label_mid(self, x, y, content):
        self.c.setFont("Helvetica", 7.5)
        self.c.drawString(x * mm, y * mm, content)

    def label_mid_small(self, x, y, content):
        self.c.setFont("Helvetica", 7.25)
        self.c.drawString(x * mm, y * mm, content)

    def draw_form(self, contract):
        x_origin = 12 * mm
        y_origin = 10 * mm
        x_max = 195
        self.c.translate(x_origin, y_origin)  # origin = lower-left of the main box
        self.c.setStrokeColor(black)

        # SFU logo
        self.c.drawImage(logofile, x=0, y=247 * mm, width=15 * mm, height=8 * mm)
        self.c.setFont('BemboMTPro', 10)
        self.c.setFillColor(self.sfu_red)
        self._drawStringLeading(self.c, 17 * mm, 250 * mm, 'Simon Fraser University'.translate(self.sc_trans_bembo),
                                charspace=1.4)
        self.c.setFont('DINPro', 5)
        self.c.setFillColor(self.sfu_grey)
        self._drawStringLeading(self.c, 17 * mm, 247.5 * mm, 'Engaging the World'.upper(), charspace=2)
        self.c.setFillColor(black)

        # Header
        self.header_label_large(77, 239, 'Sessional Instructor')

        self.label_mid_bold(1, 231.5, 'SFUID')

        # Fill in the emplid
        if contract.sessional.emplid:
            emplid = str(contract.sessional.emplid())
            if len(emplid) == 9:
                self.label_filled_centred(14.67, 231.5, emplid[0])
                self.label_filled_centred(20, 231.5, emplid[1])
                self.label_filled_centred(25.33, 231.5, emplid[2])
                self.label_filled_centred(30.67, 231.5, emplid[3])
                self.label_filled_centred(36, 231.5, emplid[4])
                self.label_filled_centred(41.33, 231.5, emplid[5])
                self.label_filled_centred(46.67, 231.5, emplid[6])
                self.label_filled_centred(52, 231.5, emplid[7])
                self.label_filled_centred(57.33, 231.5, emplid[8])

        self.label_mid_bold(62, 231.5, 'Social Insurance #')

        # Fill in the SIN.  The contract should always have one as it is required, and the length should always
        # be 9 as the form enforces that, but let's triple-check anyway.
        if contract.sin and len(contract.sin) == 9:
            sin = contract.sin
            self.label_filled_centred(95, 231.5, sin[0])
            self.label_filled_centred(101, 231.5, sin[1])
            self.label_filled_centred(107, 231.5, sin[2])
            self.label_filled_centred(113, 231.5, sin[3])
            self.label_filled_centred(119, 231.5, sin[4])
            self.label_filled_centred(125, 231.5, sin[5])
            self.label_filled_centred(131, 231.5, sin[6])
            self.label_filled_centred(137, 231.5, sin[7])
            self.label_filled_centred(143, 231.5, sin[8])

        self.label(157, 231.5, 'Employee Group:  TSSU')
        self.rect(12, 229, 48, 7)
        self.rect(92, 229, 54, 7)
        self.rect(155, 228.8, 40, 8.5)
        self.vline(17.33, 229, 236)
        self.vline(22.67, 229, 236)
        self.vline(28, 229, 236)
        self.vline(33.33, 229, 236)
        self.vline(38.67, 229, 236)
        self.vline(44, 229, 236)
        self.vline(49.33, 229, 236)
        self.vline(54.67, 229, 236)
        self.vline(98, 229, 236)
        self.vline(104, 229, 236)
        self.vline(110, 229, 236)
        self.vline(116, 229, 236)
        self.vline(122, 229, 236)
        self.vline(128, 229, 236)
        self.vline(134, 229, 236)
        self.vline(140, 229, 236)

        self.label_mid(3, 223.2,'Last Name')
        self.label_mid(70, 223.2, 'First Name')
        self.rect(1, 215.5, 65, 6)
        self.label_filled(2, 217.5, contract.sessional.last_name())
        self.rect(68, 215.5, 62, 6)
        self.label_filled(69, 217.5, contract.sessional.first_name())
        self.label_mid(3, 211.2, 'Department of Employment')
        self.label_mid(68, 211.2, 'Position Number')
        self.rect(1, 203.5, 65, 6)
        self.label_filled(2, 205.5, contract.unit.name)
        self.rect(68, 203.5, 62, 6)
        self.vline(74.89, 203.5, 209.5)
        self.vline(81.78, 203.5, 209.5)
        self.vline(88.67, 203.5, 209.5)
        self.vline(95.56, 203.5, 209.5)
        self.vline(102.44, 203.5, 209.5)
        self.vline(109.33, 203.5, 209.5)
        self.vline(116.22, 203.5, 209.5)
        self.vline(123.11, 203.5, 209.5)

        # We only have 9 spots for position number.  Let's do so me magic to make it print however many digits
        # we have nicely.
        posn = str(contract.account.position_number)
        lp = len(posn)
        if lp <= 9:
            #  Center X positions for every possible digit
            x_positions = [71.44, 78.33, 85.22, 92.11, 99, 105.89, 112.78, 119.67, 126.56]
            lx = len(x_positions)
            for i in range(lp):
                self.label_filled_centred(x_positions[i + lx - lp], 205.5, posn[i])

        self.checkbox(135, 220, contract.appt_guarantee == 'GUAR')
        self.subscript_small_label_bold(141, 220.5,  'APPOINTMENT GUARANTEED')
        self.checkbox(135, 214, contract.appt_guarantee == 'COND')
        self.subscript_small_label_bold(141, 214.5, 'APPOINTMENT CONDITIONAL UPON ENROLMENT')
        self.checkbox(135, 208, contract.appt_type == 'INIT')
        self.subscript_small_label_bold(141, 208.5, 'INITIAL APPOINTMENT TO THIS POSITION NUMBER')
        self.checkbox(135, 202, contract.appt_type == 'REAP')
        self.subscript_small_label_bold(141, 202.5, 'REAPPOINTMENT TO SAME POSITION NUMBER OR REVISION')
        self.label_mid(48.5, 193, 'Payroll Start Date')
        self.label_mid(79, 193, 'Payroll End Date')
        self.label_mid(115.5, 193, 'Appointment Start Date')
        self.label_mid(152, 193, 'Appointment End Date')
        self.rect(46.8, 186, 25.5, 5)
        self.label_filled_centred(59.55, 187.5, str(contract.pay_start))
        self.rect(77, 186, 25.5, 5)
        self.label_filled_centred(89.75, 187.5, str(contract.pay_end))
        self.rect(114, 186, 31.5, 5)
        self.label_filled_centred(129.75, 187.5, str(contract.appointment_start))
        self.rect(150, 186, 31.5, 5)
        self.label_filled_centred(165.75, 187.5, str(contract.appointment_end))
        self.header_label(1.5, 179, 'ASSIGNMENT')
        self.rect(0, 139.5, x_max, 36.5)
        self.label_mid(25, 173.3, 'Course(s)')
        self.label_mid(86, 173.3, '1x2HR. Lecture')
        self.label_mid(112, 173.3, 'Sessional Lecturer')
        self.label_mid(2.5, 172, 'Dept.')
        self.label_mid(44, 172, 'No.')
        self.label_mid(64, 172, '1x3 HR. Lab. Etc.')
        self.label_mid(140, 172, 'Contact hours')
        self.label_mid(168.5, 172, 'Salary (from grid)')
        self.label_mid(112, 170, 'Codes 1 or 2')
        self.label_filled_centred(20.75, 164.4, contract.offering.subject)
        self.label_filled_centred(51.15, 164.4, contract.offering.number)

        if contract.course_hours_breakdown:
            if len(contract.course_hours_breakdown) > 28:
                breakdown = []
                breakdown.append(Paragraph(contract.course_hours_breakdown, style=self.NOTE_STYLE))
                f = Frame(61.5*mm, 160.8*mm, 48*mm, 8*mm, 0, 0, 0, 0)
                f.addFromList(breakdown, self.c)
            else:
                self.label_filled_small(61.5, 164.4, contract.course_hours_breakdown)

        self.label_filled_centred(151.9, 164.4, str(contract.contact_hours))
        self.label_filled_centred(180.5, 164.4, str(contract.total_salary))
        self.hline(0, x_max, 168.7)
        self.hline(0, x_max, 161.4)
        self.hline(0, x_max, 154.1)
        self.hline(0, x_max, 146.8)
        self.vline(41.5, 139.5, 168.7)
        self.vline(60.8, 139.5, 176)
        self.vline(109.8, 139.5, 176)
        self.vline(137.8, 139.5, 176)
        self.vline(166, 139.5, 176)
        self.label_small(27, 136, 'Biweekly Rate')
        self.label_small(51.8, 136, 'Semester Rate')
        self.label_small(157, 136, 'Effective date for rate changes')
        self.label_small(2, 131, 'Total salary incl.')
        self.label_small(2, 128, 'Vacation pay')
        self.rect(156, 130, 37.5, 4.5)
        self.rect(25.5, 127.8, 19.5, 6.5)
        self.rect(50, 127.8, 19.5, 6.5)
        self.label_filled_centred(59.75, 130.3, str(contract.total_salary))
        self.label(2.5, 117, 'Remarks')
        self.rect(16, 110.5, 177, 16)
        remarks_mandatory_string = 'Account number: ' + str(contract.account.account_number)
        self.label_filled(17, 123.5, remarks_mandatory_string)
        self.label_filled(17, 118.5, contract.notes)
        self.label_small(158, 106, 'Deadline for acceptance:')
        self.rect(156, 99, 37.5, 5)
        self.label_mid_bold(2, 101, 'INSTRUCTIONS TO THE APPOINTEE:')
        self.label_mid_small(2, 93.5, '1.a) This offer of appointment is conditional upon you accepting this appointment '
                                  'by signing and dating this appointment form (see bottom right hand corner box) and')
        self.label_mid_small(2, 90.25, 'returning the signed form to the Dean\'s Office by the deadline for acceptance above.')
        self.label_mid_small(2, 85.5, '1.b) If this is an initial appointment in the TSSU bargaining unit, then as a '
                                'condition of employment under the terms of the Collective Agreement you must '
                                'complete and')
        self.label_mid_small(2, 82.25, 'sign the first two sections of the attached form entitled "Appendix A to '
                                       'Article IV Dues and Union Membership or Non Membership" and return it with '
                                       'this appointment ')
        self.label_mid_small(2, 79, 'form.')

        self.rect(0, 51.5, x_max, 24)
        self.hline(0, x_max, 67.5)
        self.hline(0, x_max, 59.5)
        self.vline(65, 51.5, 75.5)
        self.vline(130, 51.5, 75.5)
        self.label(2, 70, 'Approval by Department')
        self.label(67, 70, 'Approval by Faculty')
        self.label(132, 70, 'Accepted by Appointee')
        self.rect(1, 60.5, 63, 6)
        self.rect(66, 60.5, 63, 6)
        self.rect(131, 60.5, 63, 6)
        self.label(2.5, 54, 'Date')
        self.label(67.5, 54, 'Date')
        self.label(132.5, 54, 'Date')
        self.rect(15, 52.5, 49, 6)
        self.rect(80, 52.5, 49, 6)
        self.rect(145, 52.5, 49, 6)
        self.label_mid_small(1.5, 40, 'The information on this form is collected under the authority of the university '
                                      'act (RSBC 1996, c.468), the income tax act, the pension plan act, the '
                                      'employment insurance')
        self.label_mid_small(1.5, 36.625, 'act, the financial information act of BC, and the workers compensation act '
                                          'of BC. The information on this form is used by the university for payroll '
                                          'and benefit plan')
        self.label_mid_small(1.5, 33.25, 'administration, statistical compilations and operating programs and '
                                         'activities as required by the university policies. The information on this '
                                         'form is disclosed to government')
        self.label_mid_small(1.5, 29.875, 'agencies as required by the government acts. Your banking information is '
                                          'disclosed to financial institutions for the purpose of direct deposit. '
                                          'In accordance with the')
        self.label_mid_small(1.5, 26.5, 'financial information act of BC, your name and remuneration is public '
                                        'information and may be published.')
        self.label_small(1.5, 22, 'If you have any questions about the collection and use of this information, please '
                                  'contact the Simon Fraser University payroll supervisor.')
        self.label_mid(0.5, 6, 'ORIGINAL: DEAN')
        self.label_mid(28, 6, 'COPY: EMPLOYEE')
        self.label_mid(58, 6, 'COPY: PAYROLL')
        self.label_mid(86, 6, 'COPY: DEPARTMENT')

        self.subscript_small_label_bold(0, 0, 'Sessional instructor TSSU v4 update April 2015 - Generated by ' + product_name(hint='admin'))



        # All done, show the page
        self.c.showPage()


def sessional_form(contract, outfile):
    doc = SessionalForm(outfile)
    doc.draw_form(contract)
    doc.save()


class KeyForm(FormMixin, SFUMediaMixin):
    def __init__(self, *args, **kwargs):
        super(KeyForm, self).__init__(*args, **kwargs)
        self._media_setup()

    def draw_form(self, booking):
        x_origin = 30.5 * mm
        y_origin = 43 * mm
        x_max = 156.1

        self.c.translate(x_origin, y_origin)  # origin = lower-left of the main box
        self.c.setStrokeColor(black)

        # SFU logo
        self.c.drawImage(logofile, x=0.5, y=200 * mm, width=24 * mm, height=10 * mm)
        self.c.setFont('BemboMTPro', 10)
        self.c.setFillColor(self.sfu_red)
        self._drawStringLeading(self.c, 28 * mm, 204 * mm, 'SIMON FRASER UNIVERSITY'.translate(self.sc_trans_bembo),
                                charspace=1.4)
        self.c.setFont('DINPro', 5)
        self.c.setFillColor(self.sfu_grey)
        self._drawStringLeading(self.c, 42 * mm, 201 * mm, 'Surrey'.upper(), charspace=2)
        self.c.setFillColor(black)

        # Top instructions
        self.header_label_large_nobold(0,191, "Key Policy")
        self.label(0, 182, "1.  I am accountable for the key listed below.")
        self.label(0, 175.5, "2.  The key is the property of SFU")
        self.label(0, 168.5, "3.  I will return the key when it is not needed, or when requested, without delay.")
        self.label(0, 162, "4.  I will return the key to Facilities Services Surrey or put it in the drop box.")
        self.label(0, 155, "5.  I will not give the key to another person, except as arranged through Facilities.")
        self.label(0, 148.5, "6.  I will not loan the key or attempt to have it copied.")
        self.label(0, 142, "7.  I will immediately report a lost or stolen key.")
        self.label(0, 135, "8.  I have not paid a deposit for this key.")
        self.header_label(0, 126, "I  have read and understand the above policy.")


        # Top rectangle
        self.rect(0, 82.5, x_max, 38)
        self.hline(0, x_max, 105.2)
        self.hline(0, x_max, 94)
        self.vline(x_max/2, 82.5, 120.5)
        self.vline(x_max/4, 82.5, 94)

        self.label_small(2, 117, "Signature")
        self.label_small(80.1, 117, "Date")
        self.label_small(2, 102.5, "Name")
        self.label_small(80.1, 102.5, "SFU ID")
        self.label_small(2, 91, "Department")
        self.label_small(41, 91, "Room")
        self.label_small(80.1, 91, "Email or telephone")

        self.label_filled_large(80.1, 108.2, datetime.datetime.today().strftime('%Y-%m-%d'))
        self.label_filled_large(2, 97, booking.person.name())
        self.label_filled_large(80.1, 97, str(booking.person.emplid))
        self.label_filled_large(41, 85.5, str(booking.location.room_number))
        self.label_filled_large(2, 85.5, booking.location.unit.label)
        self.label_filled_large(80.1, 85.5, booking.person.email())

        #  Bottom rectangle
        self.c.setFillGray(0.9)
        self.rect(0, 11, x_max, 67, filled=1)
        self.c.setFillGray(0)
        self.hline(0, x_max, 59.9)
        self.hline(0, x_max, 50.5)
        self.hline(0, x_max, 41.1)
        self.vline(x_max/2, 11, 59.9)
        self.c.setLineWidth(2)
        self.rect(x_max/2, 11, x_max/2, 48.9)

        self.header_label_large(2, 73, "Internal Use Only")
        self.label(2, 63, "Room")
        self.label(80, 63, "key")
        self.label(130, 63, "Serial")
        self.label(2, 54, "Date Returned")
        self.label(80, 54, "Date Lost")
        self.label(2, 45, "Initial")
        self.label(80, 45, "Initial")
        self.label(2, 35.5, "Notes / Comments")
        self.label(80, 35.5, "Notes / Comments")

        self.c.setFont("Helvetica", 5.8)
        self.c.drawString(0, 4.8*mm, "The information on this form is collected under the general authority of the "
                                   "University Act (R.S.B.C. 1979, c.419). It is related directly to and needed by the "
                                   "University for the")
        self.c.drawString(0, 2.4*mm, "Administration of keys and security on campus. The information will be used by SFU "
                                   "and will not be shared with any other parties except in the event of an emergency. "
                                   "If you")
        self.c.drawString(0, 0, "have any questions about the collection and use of this information, please "
                                   "contact the Manager, Facilities Services, SFU Surrey at (778) 782-7496.")
        self.c.drawString(0, -10*mm, "Form generated automatically by CourSys.")



        # All done, show the page
        self.c.showPage()



def key_form(booking, outfile):
    doc = KeyForm(outfile)
    doc.draw_form(booking)
    doc.save()

def ta_evaluation_form(ta_evaluation, member, course, outfile):
    """
    Generate TUG Form for individual TA.
    """
    doc = TAEvalForm(outfile)
    doc.draw_form_ta_eval(ta_evaluation, member, course)
    doc.save()  

class TAEvalForm(object):
    """
    For for HR to appoint a TA
    """
    BOX_HEIGHT = 0.25*inch
    LABEL_RIGHT = 2
    LABEL_UP = 2
    CONTENT_RIGHT = 4
    CONTENT_UP = 4
    LABEL_SIZE = 6
    CONTENT_SIZE = 12
    NOTE_STYLE = ParagraphStyle(name='Normal',
                                fontName='Helvetica',
                                fontSize=7,
                                leading=10,
                                alignment=TA_LEFT,
                                textColor=black)
                        

    def __init__(self, outfile):
        """
        Create TAEvalForm in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)

    def _draw_box(self, x, y, width, label='', label_size=LABEL_SIZE, content='', content_size=CONTENT_SIZE, right=False):
        height = self.BOX_HEIGHT
        self.c.setLineWidth(1)
        self.c.rect(x, y, width, height)

        if label:
            self.c.setFont("Helvetica", label_size)
            self.c.drawString(x + self.LABEL_RIGHT, y + height + self.LABEL_UP, label)

        if content:
            self.c.setFont("Helvetica", content_size)
            if right:
                self.c.drawRightString(x + width - self.CONTENT_RIGHT, y + self.CONTENT_UP, content)
            else:
                self.c.drawString(x + self.CONTENT_RIGHT, y + self.CONTENT_UP, content)


    def draw_form_ta_eval(self, ta_evaluation, member, course):
        """
        Draw the form for an new-style contract (tacontract module)
        """        
        return self.draw_form(
                ta_evaluation = ta_evaluation, member = member, course = course
        )

    def draw_form(self, ta_evaluation, member, course):
        """
        Generic TA Form drawing method: probably called by one of the above that abstract out the object details.
        """

        self.c.setStrokeColor(black)
        self.c.translate(15.8*mm, 31.7*mm) # origin = lower-left of the main box        

        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.5)
        p = self.c.beginPath()

        # header
        # x = from 179-225mm  
        self.c.setFont("Helvetica", 10)
        self.c.drawString(0, 225*mm, "APPENDIX E")
        p.moveTo(0, 224*mm)   #x, y
        p.lineTo(22*mm, 224*mm)
        self.c.drawImage(logofile, x=20.5*mm, y=210*mm, width=20.5*mm, height=10.3*mm)
        self.c.setFont("Helvetica-Oblique", 10)
        self.c.drawString(60.35*mm, 215*mm, "SIMON FRASER UNIVERSITY")
        p.moveTo(60.35*mm, 214*mm)   #x, y
        p.lineTo(110.5*mm, 214*mm)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(60.35*mm, 210*mm, "Teaching Assistant Evaluation")
        
        # description
        self.c.setFont("Helvetica", 7)
        self.c.drawString(0, 195*mm, "1. You must review this Evaluation Form and Evaluative Criteria with your TA at the beginning of the semester (ref. Art. 20 A).")
        self.c.drawString(0, 190*mm, "2. Whenever reasonably possible, supervisors shall bring serious or continuing problems to the attention of the TA before citing in this Evaluation Form (ref. Art. 20 I).")       
        self.c.drawString(0, 185*mm, "3. This form is to be completed by you at the conclusion of the semester. Your assessment of the TA's teaching abilities will become part of the TA's employment")
        self.c.drawString(0, 182*mm, "record. This feedback is intended to enhance teaching performance.")

        self.draw_form_page_1(ta_evaluation, member, course)
        self.draw_form_page_2(ta_evaluation)


    def draw_form_page_1(self, ta_evaluation, member, course):
        # section A
        # x = from 158-174mm       
        main_width = 184.15*mm
        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.5)
        p = self.c.beginPath() 
        p.moveTo(0, 158*mm)   #x, y
        p.lineTo(0, 174*mm)
        p.lineTo(main_width, 174*mm)
        p.lineTo(main_width, 158*mm)
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)

        if ta_evaluation.draft:
            self.c.setFont("Helvetica", 12)        
            self.c.drawString(1*mm, 176*mm, "DRAFT")
        moving_y = 170*mm

        self.c.setFont("Helvetica-Bold", 9)        
        self.c.drawString(1*mm, moving_y, "SECTION A: Teaching Assistant Information")
        moving_y = moving_y-5*mm
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, moving_y, "Name")
        self.c.setFont("Helvetica", 8)
        self.c.drawString(10*mm, moving_y, member.person.name())        
        p.moveTo(10*mm, moving_y-1*mm)   #x, y
        p.lineTo(60*mm, moving_y-1*mm)
        self.c.drawPath(p, stroke=1, fill=0)

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(65*mm, moving_y, "Department")
        self.c.setFont("Helvetica", 8)
        self.c.drawString(83*mm, moving_y, course.owner.name)
        p.moveTo(83*mm, moving_y-1*mm)   #x, y
        p.lineTo(125*mm, moving_y-1*mm)
        self.c.drawPath(p, stroke=1, fill=0)

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(128*mm, moving_y, "Semester")
        self.c.setFont("Helvetica", 8)
        self.c.drawString(142*mm, moving_y, course.semester.name)
        p.moveTo(142*mm, moving_y-1*mm)   #x, y
        p.lineTo(150*mm, moving_y-1*mm)
        self.c.drawPath(p, stroke=1, fill=0)

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(152*mm, moving_y, "Course#")
        self.c.setFont("Helvetica", 8)
        self.c.drawString(165*mm, moving_y, course.name())
        p.moveTo(165*mm, moving_y-1*mm)   #x, y
        p.lineTo(183*mm, moving_y-1*mm)
        self.c.drawPath(p, stroke=1, fill=0)

        moving_y = moving_y-5*mm
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, moving_y, "Course Title")
        self.c.setFont("Helvetica", 8)
        self.c.drawString(20*mm, moving_y, course.title)
        p.moveTo(20*mm, moving_y-1*mm)   #x, y
        p.lineTo(62*mm, moving_y-1*mm)
        self.c.drawPath(p, stroke=1, fill=0)

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(65*mm, moving_y, "Instructor")
        self.c.setFont("Helvetica", 8)
        self.c.drawString(83*mm, moving_y, course.instructors_str())
        p.moveTo(83*mm, moving_y-1*mm)   #x, y
        p.lineTo(150*mm, moving_y-1*mm)
        self.c.drawPath(p, stroke=1, fill=0)

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(152*mm, moving_y, "TA's 1st Appt.")
        self.c.setFont("Helvetica", 8)
        if ta_evaluation.first_appoint is None:
            self.c.drawString(172*mm, moving_y, 'Unknown')
        elif ta_evaluation.first_appoint:
            self.c.drawString(175*mm, moving_y, 'Yes')
        else:
            self.c.drawString(175*mm, moving_y, 'No')
        p.moveTo(175*mm, moving_y-1*mm)   #x, y
        p.lineTo(183*mm, moving_y-1*mm)
        self.c.drawPath(p, stroke=1, fill=0)

        # section B
        # x = from 50-155mm
        main_width = 184.15*mm
        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.5)
        p = self.c.beginPath() 
        
        # Section B - border
        #p.moveTo(0, 50*mm)   #x, y
        #p.lineTo(0, 150*mm)
        #p.lineTo(main_width, 150*mm)
        #p.lineTo(main_width, 50*mm)
        #p.close()        
        #self.c.drawPath(p, stroke=1, fill=0)
         
        self.c.setFont("Helvetica-Bold", 9)
        moving_y = 146*mm
        self.c.drawString(1*mm, moving_y, "SECTION B: EVALUATIVE CRITERIA")
        moving_y = moving_y-5*mm
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, moving_y, "Using the evaluative criteria below, indicate whether the TA's performance:")
        moving_y = moving_y-5*mm
        self.c.drawString(1*mm, moving_y, "1     Meets Job Requirements - Good")
        self.c.drawString(90*mm, moving_y, "2     Meets Job Requirements - Satistactory")
        moving_y = moving_y-5*mm
        self.c.drawString(1*mm, moving_y, "3     Does not meet job requirement -")
        self.c.drawString(90*mm, moving_y, "4     Does not meet job requirement -")
        moving_y = moving_y-3*mm
        self.c.drawString(6.5*mm, moving_y, "Requires some improvement *")
        self.c.drawString(95.5*mm, moving_y, "Requires major improvement *")        
        moving_y = moving_y-5*mm
        self.c.drawString(1*mm, moving_y, "5     No opportunity to evaluate or criterion is not applicable.")
        
        moving_y = moving_y-5*mm
        self.c.drawString(1*mm, moving_y, "* Whenever reasonably possible, supervisors shall bring serious or continuing problems to the attention of the TA before citing in this")
        moving_y = moving_y-3*mm
        self.c.drawString(1*mm, moving_y, "Evaluation Form(ref. Art. 20 I ).")
        p.moveTo(0, moving_y-1*mm)   #x, y
        p.lineTo(main_width, moving_y-1*mm)
        self.c.drawPath(p, stroke=1, fill=0)

        # section B - criterion
        moving_y = moving_y-10*mm
        
        p.moveTo(2*mm, moving_y-(2*mm))   #x, y
        p.lineTo(2*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(4.5*mm, moving_y, str(ta_evaluation.criteria_lab_prep))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(15*mm, moving_y, "Preparation of Lab/Tutorial Material")
        
        p.moveTo(92*mm, moving_y-(2*mm))   #x, y
        p.lineTo(92*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(94.5*mm, moving_y, str(ta_evaluation.criteria_meet_deadline))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(105*mm, moving_y, "Meets Deadlines")

        moving_y = moving_y-10*mm
        p.moveTo(2*mm, moving_y-(2*mm))   #x, y
        p.lineTo(2*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(4.5*mm, moving_y, str(ta_evaluation.criteria_maintain_hour))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(15*mm, moving_y, "Maintains Office Hours")
        
        p.moveTo(92*mm, moving_y-(2*mm))   #x, y
        p.lineTo(92*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(94.5*mm, moving_y, str(ta_evaluation.criteria_attend_plan))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(105*mm, moving_y, "Attendance at Planning/Coordinating Meetings")

        moving_y = moving_y-10*mm
        p.moveTo(2*mm, moving_y-(2*mm))   #x, y
        p.lineTo(2*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(4.5*mm, moving_y, str(ta_evaluation.criteria_attend_lec))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(15*mm, moving_y, "Attendance at Lectures")
        
        p.moveTo(92*mm, moving_y-(2*mm))   #x, y
        p.lineTo(92*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(94.5*mm, moving_y, str(ta_evaluation.criteria_grading_fair))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(105*mm, moving_y, "Grading Fair/Consistent")

        moving_y = moving_y-10*mm
        p.moveTo(2*mm, moving_y-(2*mm))   #x, y
        p.lineTo(2*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(4.5*mm, moving_y, str(ta_evaluation.criteria_lab_performance))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(15*mm, moving_y, "Performance in Lab/Tutorial")
        
        p.moveTo(92*mm, moving_y-(2*mm))   #x, y
        p.lineTo(92*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(94.5*mm, moving_y, str(ta_evaluation.criteria_quality_of_feedback))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(105*mm, moving_y, "Quality of Feedback")

        moving_y = moving_y-10*mm
        p.moveTo(2*mm, moving_y-(2*mm))   #x, y
        p.lineTo(2*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(4.5*mm, moving_y, str(ta_evaluation.criteria_quiz_prep))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(15*mm, moving_y, "Quiz Preparation/Assist in Exam Preparation")
        
        p.moveTo(92*mm, moving_y-(2*mm))   #x, y
        p.lineTo(92*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(94.5*mm, moving_y, str(ta_evaluation.criteria_instr_content))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(105*mm, moving_y, "Instructional Content")

        moving_y = moving_y-10*mm
        p.moveTo(2*mm, moving_y-(2*mm))   #x, y
        p.lineTo(2*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.setFont("Helvetica", 8)
        self.c.drawString(4.5*mm, moving_y, str(ta_evaluation.criteria_others))
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(15*mm, moving_y, "Other Job Requirements")
        
        #p.moveTo(55*mm, moving_y-(2*mm))   #x, y
        #p.lineTo(180*mm, moving_y-(2*mm))    
        #self.c.drawPath(p, stroke=1, fill=0)
        #self.c.setFont("Helvetica", 8)
        #self.c.drawString(55*mm, moving_y, str(ta_evaluation.criteria_other_comment))

        self.c.setFont("Helvetica", 8)
        wrap_line_max = 100
        lines = wrap(str(ta_evaluation.criteria_other_comment), wrap_line_max)
        
        if len(lines) == 0:
            moving_y = moving_y-5*mm

        for line in lines:
            self.c.drawString(55*mm, moving_y, line)
            p.moveTo(55*mm, moving_y-(1*mm))   #x, y
            p.lineTo(main_width-2*mm, moving_y-(1*mm))
            self.c.drawPath(p, stroke=1, fill=0)
            moving_y = moving_y-5*mm
 
        self.c.setFont("Helvetica-Bold", 8)
        # Section B - border
        p.moveTo(0, moving_y)   #x, y
        p.lineTo(0, 150*mm)
        p.lineTo(main_width, 150*mm)
        p.lineTo(main_width, moving_y)
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)

    def draw_form_page_2(self, ta_evaluation):
        
        self.c.showPage()
        p = self.c.beginPath()
        self.c.setStrokeColor(black)
        self.c.translate(15.8*mm, 31.7*mm) # origin = lower-left of the main box
        self.c.setLineWidth(0.5)
        main_width = 184.15*mm
        moving_y = 220*mm
        wrap_line_max = 138

        # section C
        # x around from 145-225mm          
        self.c.setFont("Helvetica-Bold", 9)        
        self.c.drawString(1*mm, moving_y, "SECTION C: EVALUATION COMMENTARY")
        moving_y = moving_y-3*mm
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, moving_y, "Please comment on the TA's positive contributions to instruction (e.g. teching methods, grading, ")
        moving_y = moving_y-3*mm
        self.c.drawString(1*mm, moving_y, "ability to lead discussion) - or other noteworthy strengths")

        moving_y = moving_y-5*mm
        self.c.setFont("Helvetica", 8)
        lines = wrap(str(ta_evaluation.positive_comment), wrap_line_max)        

        for line in lines:
            self.c.drawString(5*mm, moving_y, line)
            p.moveTo(5, moving_y-(1*mm))   #x, y
            p.lineTo(main_width-2*mm, moving_y-(1*mm))
            self.c.drawPath(p, stroke=1, fill=0)
            moving_y = moving_y-5*mm
 
        if len(lines) < 3:
            for n in range(1, 3-len(lines)+1):            
                p.moveTo(5, moving_y-(1*mm))   #x, y
                p.lineTo(main_width-2*mm, moving_y-(1*mm))
                self.c.drawPath(p, stroke=1, fill=0)
                moving_y = moving_y-5*mm

        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(1*mm, moving_y, "Please comment on those duties which you noted as not meeting job requirements and suggest ")
        moving_y = moving_y-3*mm
        self.c.drawString(1*mm, moving_y, "ways in which the TA's performance could be improved")

        moving_y = moving_y-5*mm
        self.c.setFont("Helvetica", 8)
        lines = wrap(str(ta_evaluation.improve_comment), wrap_line_max)        

        for line in lines:
            self.c.drawString(5*mm, moving_y, line)
            p.moveTo(5, moving_y-(1*mm))   #x, y
            p.lineTo(main_width-2*mm, moving_y-(1*mm))
            self.c.drawPath(p, stroke=1, fill=0)
            moving_y = moving_y-5*mm
 
        if len(lines) < 3:
            for n in range(1, 3-len(lines)+1):            
                p.moveTo(5, moving_y-(1*mm))   #x, y
                p.lineTo(main_width-2*mm, moving_y-(1*mm))
                self.c.drawPath(p, stroke=1, fill=0)
                moving_y = moving_y-5*mm                

        # draw section c box at the end as we need to know the lines
        p.moveTo(0, moving_y)   #x, y
        p.lineTo(0, 225*mm)
        p.lineTo(main_width, 225*mm)
        p.lineTo(main_width, moving_y)
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)

        # section D        
        # roughly calculate the section box height, if no enough for this page, show on new page
        lines = wrap(str(ta_evaluation.no_recommend_comment), wrap_line_max) 
        section_d_height = (45*mm) + (len(lines) * 5)*mm

        if section_d_height > moving_y:
            self.c.showPage()
            p = self.c.beginPath()
            self.c.setStrokeColor(black)
            self.c.translate(15.8*mm, 31.7*mm) # origin = lower-left of the main box
            self.c.setLineWidth(0.5)
            main_width = 184.15*mm
            moving_y = 220*mm

        section_d_start = moving_y        
        moving_y = moving_y-10*mm        
        self.c.setFont("Helvetica-Bold", 9)        
        self.c.drawString(1*mm, moving_y, "SECTION D: SUMMARY/OVERALL EVALUATION")
        
        moving_y = moving_y-8*mm
        self.c.setFont("Helvetica-Bold", 8)
        p.moveTo(2*mm, moving_y-(2*mm))   #x, y
        p.lineTo(2*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y+(4*mm))
        p.lineTo(8*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)        
        self.c.drawString(15*mm, moving_y, "Meets Job Requirements")

        p.moveTo(92*mm, moving_y-(2*mm))   #x, y
        p.lineTo(92*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)        
        self.c.drawString(105*mm, moving_y, "Does Not Meeting Requirements")

        if ta_evaluation.overall_evalation is not None:
            self.c.setFont("Helvetica", 8)
            if ta_evaluation.overall_evalation:
                self.c.drawString(4.5*mm, moving_y, "X")
            else:
                self.c.drawString(94.5*mm, moving_y, "X")

        moving_y = moving_y-7*mm
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(2*mm, moving_y, "Would you recommend this TA for reappointment?")
        p.moveTo(92*mm, moving_y-(2*mm))   #x, y
        p.lineTo(92*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y+(4*mm))
        p.lineTo(98*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)        
        self.c.drawString(105*mm, moving_y, "Yes")

        p.moveTo(122*mm, moving_y-(2*mm))   #x, y
        p.lineTo(122*mm, moving_y+(4*mm))
        p.lineTo(128*mm, moving_y+(4*mm))
        p.lineTo(128*mm, moving_y-(2*mm))
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)        
        self.c.drawString(135*mm, moving_y, "No")

        if ta_evaluation.recommend_TA is not None:
            self.c.setFont("Helvetica", 8)
            if ta_evaluation.recommend_TA:
                self.c.drawString(94.5*mm, moving_y, "X")
            else:
                self.c.drawString(124.5*mm, moving_y, "X")
        
        moving_y = moving_y-7*mm
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(2*mm, moving_y, "If No, explain briefly")
        moving_y = moving_y-5*mm        
        self.c.setFont("Helvetica", 8)
        lines = wrap(str(ta_evaluation.no_recommend_comment), wrap_line_max)        

        for line in lines:
            self.c.drawString(5*mm, moving_y, line)
            p.moveTo(5, moving_y-(1*mm))   #x, y
            p.lineTo(main_width-2*mm, moving_y-(1*mm))
            self.c.drawPath(p, stroke=1, fill=0)
            moving_y = moving_y-5*mm
 
        if len(lines) < 3:
            for n in range(1, 3-len(lines)+1):            
                p.moveTo(5, moving_y-(1*mm))   #x, y
                p.lineTo(main_width-2*mm, moving_y-(1*mm))
                self.c.drawPath(p, stroke=1, fill=0)
                moving_y = moving_y-5*mm     

        moving_y = moving_y-5*mm
        p.moveTo(5*mm, moving_y)   #x, y
        p.lineTo(80*mm, moving_y)
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.drawString(10*mm, moving_y+(1*mm), ta_evaluation.instructor_sign)        
        p.moveTo(105*mm, moving_y)   #x, y
        p.lineTo(175*mm, moving_y)
        self.c.drawPath(p, stroke=1, fill=0)
        if ta_evaluation.instructor_signdate:
            self.c.drawString(110*mm, moving_y+(1*mm), ta_evaluation.instructor_signdate.strftime('%Y/%m/%d'))
        moving_y = moving_y-3*mm
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(20*mm, moving_y, "Instruction's Signature")
        self.c.drawString(130*mm, moving_y, "Year/Month/Day")
        moving_y = moving_y-5*mm
        
        # draw section d box at the end as we need to know the lines
        p.moveTo(0, moving_y)   #x, y
        p.lineTo(0, section_d_start-(5*mm))
        p.lineTo(main_width, section_d_start-(5*mm))
        p.lineTo(main_width, moving_y)
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)

        # section E 
        # roughly calculate the section box height, if no enough for this page, show on new page
        lines = wrap(str(ta_evaluation.ta_comment), wrap_line_max) 
        section_d_height = (23*mm) + (len(lines) * 5)*mm

        if section_d_height > moving_y:
            self.c.showPage()
            p = self.c.beginPath()
            self.c.setStrokeColor(black)
            self.c.translate(15.8*mm, 31.7*mm) # origin = lower-left of the main box
            self.c.setLineWidth(0.5)
            main_width = 184.15*mm
            moving_y = 220*mm

        section_e_start = moving_y
        moving_y = moving_y-10*mm
        self.c.setFont("Helvetica-Bold", 9)        
        self.c.drawString(1*mm, moving_y, "SECTION E: TEACHING ASSISTANT'S COMMENTS")

        self.c.setFont("Helvetica-Bold", 8)
        moving_y = moving_y-5*mm        
        self.c.setFont("Helvetica", 8)
        lines = wrap(str(ta_evaluation.ta_comment), wrap_line_max)        

        for line in lines:
            self.c.drawString(5*mm, moving_y, line)
            p.moveTo(5, moving_y-(1*mm))   #x, y
            p.lineTo(main_width-2*mm, moving_y-(1*mm))
            self.c.drawPath(p, stroke=1, fill=0)
            moving_y = moving_y-5*mm
 
        if len(lines) < 3:
            for n in range(1, 3-len(lines)+1):            
                p.moveTo(5, moving_y-(1*mm))   #x, y
                p.lineTo(main_width-2*mm, moving_y-(1*mm))
                self.c.drawPath(p, stroke=1, fill=0)
                moving_y = moving_y-5*mm     

        moving_y = moving_y-5*mm
        p.moveTo(5*mm, moving_y)   #x, y
        p.lineTo(80*mm, moving_y)
        self.c.drawPath(p, stroke=1, fill=0)
        self.c.drawString(10*mm, moving_y+(1*mm), str(ta_evaluation.ta_sign))        
        p.moveTo(105*mm, moving_y)   #x, y
        p.lineTo(175*mm, moving_y)
        self.c.drawPath(p, stroke=1, fill=0)
        if ta_evaluation.ta_signdate:
            self.c.drawString(110*mm, moving_y+(1*mm), ta_evaluation.ta_signdate.strftime('%Y/%m/%d'))
        moving_y = moving_y-3*mm
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(20*mm, moving_y, "Teaching Assistant's Signature")
        self.c.drawString(130*mm, moving_y, "Year/Month/Day")
        moving_y = moving_y-5*mm

        # draw section e box at the end as we need to know the lines
        p.moveTo(0, moving_y)   #x, y
        p.lineTo(0, section_e_start-(5*mm))
        p.lineTo(main_width, section_e_start-(5*mm))
        p.lineTo(main_width, moving_y)
        p.close()        
        self.c.drawPath(p, stroke=1, fill=0)
        
        moving_y = moving_y-5*mm
        if moving_y < (12*mm):
            self.c.showPage()
            p = self.c.beginPath()
            moving_y = 220*mm

        self.c.setFont("Helvetica-Bold", 7)
        self.c.drawString(5*mm, moving_y, "Distribution of and retention of the Evaluation Form")
        moving_y = moving_y-3*mm
        self.c.drawString(5*mm, moving_y, "1. The original coy of the Evaluation Form must be forwarded to the Department Chair on completion and included in the TA's employment file.")
        moving_y = moving_y-3*mm
        self.c.drawString(5*mm, moving_y, "2. The TA must receive a copy of the Evaluation Form no later than the end of the first week of classes of the following semester")
        moving_y = moving_y-3*mm
        self.c.drawString(5*mm, moving_y, "3. The TA may make comments on the evaluation and such comments will then be added to the employment file. The TA should complete TA comments")
        moving_y = moving_y-3*mm
        self.c.drawString(5*mm, moving_y, "section, sign and date the form and return the form to the Department Chair as soon as possible.")
        
    def save(self):
        self.c.save()    

def tug_form(tug, contract_info, new_format, outfile):
    """
    Generate TUG Form for individual TA.
    """
    doc = TUGForm(outfile)
    doc.draw_form_tug(tug, contract_info, new_format)
    doc.save()    

class TUGForm(object):
    """
    For for HR to appoint a TA
    """
    BOX_HEIGHT = 0.25*inch
    LABEL_RIGHT = 2
    LABEL_UP = 2
    CONTENT_RIGHT = 4
    CONTENT_UP = 4
    LABEL_SIZE = 6
    CONTENT_SIZE = 12
    NOTE_STYLE = ParagraphStyle(name='Normal',
                                fontName='Helvetica',
                                fontSize=7,
                                leading=10,
                                alignment=TA_LEFT,
                                textColor=black)


    def __init__(self, outfile):
        """
        Create TUGForm in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)

    def _draw_box(self, x, y, width, label='', label_size=LABEL_SIZE, content='', content_size=CONTENT_SIZE, right=False):
        height = self.BOX_HEIGHT
        self.c.setLineWidth(1)
        self.c.rect(x, y, width, height)

        if label:
            self.c.setFont("Helvetica", label_size)
            self.c.drawString(x + self.LABEL_RIGHT, y + height + self.LABEL_UP, label)

        if content:
            self.c.setFont("Helvetica", content_size)
            if right:
                self.c.drawRightString(x + width - self.CONTENT_RIGHT, y + self.CONTENT_UP, content)
            else:
                self.c.drawString(x + self.CONTENT_RIGHT, y + self.CONTENT_UP, content)


    def draw_form_tug(self, tug, contract_info, new_format):
        """
        Draw the form for an new-style contract (tacontract module)
        """
        iterable_fields = [(_, params) for _, params in tug.config.items() if hasattr(params, '__iter__') ]
        total_hours = sum(decimal.Decimal(params.get('total',0)) for _, params in iterable_fields if params.get('total',0) is not None)
        total_hours = round(total_hours, 2)

        from ta.models import LAB_BONUS_DECIMAL, HOLIDAY_HOURS_PER_BU, HOURS_PER_BU, LAB_BONUS_DECIMAL, HOURS_PER_BU

        contract_info = None
        if contract_info:
            bu = contract_info.bu
            has_lab_or_tut = contract_info.has_labtut()
            lab_bonus_decimal = contract_info.prep_bu
            holiday_hours_per_bu = contract_info.holiday_hours_per_bu
            hours_per_bu = HOURS_PER_BU
            total_bu = contract_info.total_bu
            max_hours = contract_info.hours
        else:
            bu = tug.base_units
            has_lab_or_tut = tug.member.offering.labtas()
            lab_bonus_decimal = LAB_BONUS_DECIMAL
            holiday_hours_per_bu = HOLIDAY_HOURS_PER_BU
            hours_per_bu = HOURS_PER_BU
            total_bu = tug.base_units + LAB_BONUS_DECIMAL
            max_hours = tug.base_units * HOURS_PER_BU

        if new_format:
            return self.draw_form_newformat(
                tug = tug, 
                ta = tug.member, 
                course = tug.member.offering, 
                bu = bu,
                max_hours = max_hours, 
                total_hours = total_hours,                
                has_lab_or_tut= has_lab_or_tut,
                lab_bonus = lab_bonus_decimal,
                lab_bonus_4 = lab_bonus_decimal+4,                
                lab_bonus_hours = lab_bonus_decimal*hours_per_bu,
                hours_per_bu = hours_per_bu,
                holiday_hours_per_bu = holiday_hours_per_bu,
                total_bu = total_bu,
                draft = tug.draft,
            )
        else:
            return self.draw_form(
                tug = tug, 
                ta = tug.member, 
                course = tug.member.offering, 
                bu = bu,
                max_hours = max_hours, 
                total_hours = total_hours,                
                has_lab_or_tut= has_lab_or_tut,
                lab_bonus = lab_bonus_decimal,
                lab_bonus_4 = lab_bonus_decimal+4,                
                lab_bonus_hours = lab_bonus_decimal*hours_per_bu,
                hours_per_bu = hours_per_bu,
                holiday_hours_per_bu = holiday_hours_per_bu,
                total_bu = total_bu,
                draft = tug.draft,
            )

    def draw_form(self, tug, ta, course, bu, max_hours, total_hours, has_lab_or_tut, lab_bonus, lab_bonus_4,
                  lab_bonus_hours, hours_per_bu, holiday_hours_per_bu, total_bu, draft):
        """
        Generic TA Form drawing method: probably called by one of the above that abstract out the object details.
        """

        self.c.setStrokeColor(black)
        self.c.translate(0.625*inch, 1.25*inch) # origin = lower-left of the main box
        main_width = 7.25*inch

        # main outline
        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.5)
        p = self.c.beginPath()
        p.moveTo(0, 7.975*inch)   #x, y
        p.lineTo(0, 8.875*inch)
        p.lineTo(main_width, 8.875*inch)
        p.lineTo(main_width, 7.975*inch)
        p.close()
        p.moveTo(0, 158*mm)   #x, y
        p.lineTo(main_width, 158*mm)
        #p.close()
        self.c.drawPath(p, stroke=1, fill=0)

        # header
        #self.c.drawImage(logofile, x=main_width/2 - 0.5*inch, y=227*mm, width=1*inch, height=0.5*inch)
        self.c.drawImage(logofile, x=0, y=227*mm, width=1*inch, height=0.5*inch)
        self.c.setFont("Times-Roman", 12)
        self.c.drawString(2.5*inch, 235*mm, "Simon Fraser University")
        self.c.setFont("Times-Roman", 12)
        self.c.drawString(2*inch, 228*mm, "Teaching Assistant Time Use Guideline")
        if draft:
            self.c.drawString(6*inch, 228*mm, "DRAFT")

        # draw tug summary
        self.c.setFont("Times-Roman", 10)
        self.c.drawString(5, 220*mm, "TA Name: " + ta.person.name())
        self.c.drawString(main_width/2, 220*mm, "Instructor: " + course.instructors_str())
        self.c.drawString(5, 215*mm, "Course: " + str(course))
        self.c.drawString(5, 210*mm, "Maximum Hours to be Assigned: " + str(max_hours))
        self.c.drawString(5, 205*mm, "Base Units Assigned*:" + str(bu) + " x " + str(hours_per_bu) + ' = Maximum Hours: ' + str(max_hours) )
        if has_lab_or_tut:
            self.c.drawString(main_width/2, 205*mm, "{ + " + str(lab_bonus) + " for prep = "+ str(total_bu) + "}" )

       # draw tug description
        self.c.drawString(5, 195*mm, "Teaching Assistant total workload for the semester should approach but not exceed the maximum hours over the term of the ")
        self.c.drawString(5, 190*mm, "semester (normally 17 weeks).")
        self.c.setFont("Helvetica-Oblique", 9)
        self.c.drawString(5, 180*mm, "The following summary is an approximation of the length of time expected to be devoted to the major activities. There may be shifts ")
        self.c.drawString(5, 175*mm, "between activities, but the total hours required over the semester cannot exceed the maximum hours set out above.")


        # draw tug detail - title
        self.c.setFont("Times-Roman", 10)
        self.c.drawString(main_width*0.8, 165*mm, "Average")
        self.c.drawString(main_width*0.9, 165*mm, "Total")
        self.c.drawString(5, 160*mm, "Duties and Responsibilities")
        self.c.drawString(main_width*0.8, 160*mm, "hrs/week")
        self.c.drawString(main_width*0.9, 160*mm, "hrs/semester")

        # draw tug detail - detail
        # item
        self.c.drawString(5, 150*mm, "1. Preparation for labs/tutorials")
        self.c.drawString(5, 143*mm, "2. Attendance at planning/coordinating meetings with instructor")
        self.c.drawString(5, 136*mm, "3. Attendance at lectures")
        self.c.drawString(5, 129*mm, "4. Attendance at labs/tutorials")
        self.c.drawString(5, 122*mm, "5. Office hours/student consultation/electronic communication")
        self.c.drawString(5, 115*mm, "6. Grading **")
        self.c.drawString(5, 108*mm, "7. Quiz preparation/assist in exam preparation/Invigilation of exams")
        self.c.drawString(5, 101*mm, "8. Statutory Holiday Compensation -")
        self.c.drawString(15, 96*mm, "To compensate for all statutory holidays which may occur in a semester, the total workload")
        self.c.drawString(15, 91*mm, "required will be reduced by " + str(holiday_hours_per_bu) + " hour(s) for each base unit assigned excluding the additional")
        self.c.drawString(15, 86*mm, str(lab_bonus)+ " B.U. for preparation, e.g. 4.4 hours reduction for "+ str(lab_bonus_4) + " B.U. appointment.")        
        self.c.drawString(5, 79*mm, "9. Other - specify***")
        xpos = 74*mm
        for other in tug.others():
            self.c.drawString(15, xpos, other.get('label'))            
            xpos = xpos - (5*mm)
        self.c.drawString(5, xpos-2*mm, "Required Total Hours =")

        # weekly 
        self.c.drawString(main_width*0.8, 150*mm, str({None: ''}.get(tug.config['prep']['weekly'], tug.config['prep']['weekly'])))
        self.c.drawString(main_width*0.8, 143*mm, str({None: ''}.get(tug.config['meetings']['weekly'], tug.config['meetings']['weekly'])))
        self.c.drawString(main_width*0.8, 136*mm, str({None: ''}.get(tug.config['lectures']['weekly'], tug.config['lectures']['weekly'])))
        self.c.drawString(main_width*0.8, 129*mm, str({None: ''}.get(tug.config['tutorials']['weekly'], tug.config['tutorials']['weekly'])))
        self.c.drawString(main_width*0.8, 122*mm, str({None: ''}.get(tug.config['office_hours']['weekly'], tug.config['office_hours']['weekly'])))
        self.c.drawString(main_width*0.8, 115*mm, str({None: ''}.get(tug.config['grading']['weekly'], tug.config['grading']['weekly'])))
        self.c.drawString(main_width*0.8, 108*mm, str({None: ''}.get(tug.config['test_prep']['weekly'], tug.config['test_prep']['weekly'])))
        self.c.drawString(main_width*0.8, 101*mm, str({None: ''}.get(tug.config['holiday']['weekly'], tug.config['holiday']['weekly'])))        
        xpos = 74*mm
        for other in tug.others():
            self.c.drawString(main_width*0.8, xpos, str({None: ''}.get(other.get('weekly'), other.get('weekly'))))            
            xpos = xpos - (5*mm)

        # total 
        self.c.drawString(main_width*0.9, 150*mm, str({None: ''}.get(tug.config['prep']['total'], tug.config['prep']['total'])))
        self.c.drawString(main_width*0.9, 143*mm, str({None: ''}.get(tug.config['meetings']['total'], tug.config['meetings']['total'])))
        self.c.drawString(main_width*0.9, 136*mm, str({None: ''}.get(tug.config['lectures']['total'], tug.config['lectures']['total'])))
        self.c.drawString(main_width*0.9, 129*mm, str({None: ''}.get(tug.config['tutorials']['total'], tug.config['tutorials']['total'])))
        self.c.drawString(main_width*0.9, 122*mm, str({None: ''}.get(tug.config['office_hours']['total'], tug.config['office_hours']['total'])))
        self.c.drawString(main_width*0.9, 115*mm, str({None: ''}.get(tug.config['grading']['total'], tug.config['grading']['total'])))
        self.c.drawString(main_width*0.9, 108*mm, str({None: ''}.get(tug.config['test_prep']['total'], tug.config['test_prep']['total'])))
        self.c.drawString(main_width*0.9, 101*mm, str({None: ''}.get(tug.config['holiday']['total'], tug.config['holiday']['total'])))
        xpos = 74*mm
        for other in tug.others():
            self.c.drawString(main_width*0.9, xpos, str({None: ''}.get(other.get('total'), other.get('total'))))            
            xpos = xpos - (5*mm)
        self.c.drawString(main_width*0.9, xpos-2*mm, str({None: ''}.get(total_hours, total_hours)))

        # draw tug description
        self.c.drawString(5, xpos-20*mm, "Teaching Assistants and course instructors should familiarize themselves with the general working conditions set out in Article 13C, ")
        self.c.drawString(5, xpos-25*mm, "assignment and compensation in Article 13D, and workload review mechanisms in Article 13E.")

        self.c.drawString(5, xpos-30*mm, "*There are no hours of work associated with the additional 0.17 base unit for preparation, Article 13D. 2 b. See Appendix B for")
        self.c.drawString(5, xpos-35*mm, "calculation of hours.")
        self.c.drawString(5, xpos-40*mm, "** Includes grading of all assignments, reports and examinations.")
        self.c.drawString(5, xpos-45*mm, "*** Attendance at a TA/TM Day/Training")

        self.c.drawString(5, xpos-55*mm, "Instructor Signature:")
        self.c.drawString(main_width/2, xpos-55*mm, "TA Signature:")
        self.c.drawString(5, xpos-60*mm, "Date:")
        self.c.drawString(main_width/2, xpos-60*mm, "Date:")

    def draw_form_newformat(self, tug, ta, course, bu, max_hours, total_hours, has_lab_or_tut, lab_bonus, lab_bonus_4,
                  lab_bonus_hours, hours_per_bu, holiday_hours_per_bu, total_bu, draft):
        """
        Generic TA Form drawing method: probably called by one of the above that abstract out the object details.
        """

        self.c.setStrokeColor(black)
        self.c.translate(0.625*inch, 1.25*inch) # origin = lower-left of the main box
        main_width = 7.25*inch

        # main outline
        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.5)
        p = self.c.beginPath()
        p.moveTo(0, 7.975*inch)   #x, y
        p.lineTo(0, 8.675*inch)
        p.lineTo(main_width, 8.675*inch)
        p.lineTo(main_width, 7.975*inch)
        p.close()
        p.moveTo(0, 158*mm)   #x, y
        p.lineTo(main_width, 158*mm)
        #p.close()
        self.c.drawPath(p, stroke=1, fill=0)

        # header
        #self.c.drawImage(logofile, x=main_width/2 - 0.5*inch, y=227*mm, width=1*inch, height=0.5*inch)
        self.c.drawImage(logofile, x=0, y=227*mm, width=1*inch, height=0.5*inch)
        self.c.setFont("Times-Roman", 12)
        self.c.drawString(2.5*inch, 235*mm, "Simon Fraser University")
        self.c.setFont("Times-Roman", 12)
        self.c.drawString(2*inch, 228*mm, "Teaching Assistant Time Use Guideline")
        if draft:
            self.c.drawString(6*inch, 228*mm, "DRAFT")

        # draw tug summary
        self.c.setFont("Times-Roman", 10)
        self.c.drawString(5, 215*mm, "TA Name: " + ta.person.name())
        self.c.drawString(main_width/2, 215*mm, "Instructor: " + course.instructors_str())
        self.c.drawString(5, 210*mm, "Course: " + str(course))
        #self.c.drawString(5, 210*mm, "Maximum Hours to be Assigned: " + str(max_hours))
        self.c.drawString(5, 205*mm, "Base Units Assigned*:" + str(bu) + " x " + str(hours_per_bu) + ' = Maximum Hours: ' + str(max_hours) )
        if has_lab_or_tut:
            self.c.drawString(main_width/2, 205*mm, "{ + " + str(lab_bonus) + " for prep = "+ str(total_bu) + "}" )

       # draw tug description
        self.c.drawString(5, 195*mm, "Teaching Assistant total workload for the semester should approach but not exceed the maximum hours over the term of the ")
        self.c.drawString(5, 190*mm, "semester (normally 17 weeks).")
        self.c.setFont("Helvetica-Oblique", 9)
        self.c.drawString(5, 180*mm, "The following summary is an approximation of the length of time expected to be devoted to the major activities. There may be shifts ")
        self.c.drawString(5, 175*mm, "between activities, but the total hours required over the semester cannot exceed the maximum hours set out above.")


        # draw tug detail - title
        self.c.setFont("Times-Roman", 10)
        self.c.drawString(main_width*0.8, 165*mm, "Average")
        self.c.drawString(main_width*0.9, 165*mm, "Total")
        self.c.drawString(5, 160*mm, "Duties and Responsibilities")
        self.c.drawString(main_width*0.8, 160*mm, "hrs/week")
        self.c.drawString(main_width*0.9, 160*mm, "hrs/semester")

        # draw tug detail - detail
        # item
        self.c.drawString(5, 150*mm, "1. Preparation for labs/tutorials/workshops")
        self.c.drawString(5, 144*mm, "2. Attendance at orientation and planning/coordinating meetings with instructor")
        self.c.drawString(5, 138*mm, "3. Preparation for lectures")
        self.c.drawString(5, 132*mm, "4. Attendance at lectures, including breakout groups")
        self.c.drawString(5, 126*mm, "5. Support classroom course delivery, including technical support")
        self.c.drawString(5, 120*mm, "6. Attendance at labs/tutorials/workshops")
        self.c.drawString(5, 114*mm, "7. Leading dicussions")
        self.c.drawString(5, 108*mm, "8. Office hours/student consultation")
        self.c.drawString(5, 102*mm, "9. Electronic communication")
        self.c.drawString(5, 96*mm, "10. Grading **")
        self.c.drawString(5, 90*mm, "11. Quiz preparation/assist in exam preparation/Invigilation of exams")
        self.c.drawString(5, 84*mm, "12. Statutory Holiday Compensation -")
        self.c.drawString(15, 79*mm, "To compensate for all statutory holidays which may occur in a semester, the total workload")
        self.c.drawString(15, 74*mm, "required will be reduced by " + str(holiday_hours_per_bu) + " hour(s) for each base unit assigned excluding the additional")
        self.c.drawString(15, 69*mm, str(lab_bonus)+ " B.U. for preparation, e.g. 4.4 hours reduction for "+ str(lab_bonus_4) + " B.U. appointment.")        
        self.c.drawString(5, 63*mm, "13. Other - specify***")
        xpos = 57*mm
        for other in tug.others():
            self.c.drawString(15, xpos, other.get('label'))            
            xpos = xpos - (5*mm)
        self.c.drawString(5, xpos-2*mm, "Required Total Hours =")

        # weekly 
        self.c.drawString(main_width*0.8, 150*mm, str({None: ''}.get(tug.config['prep']['weekly'], tug.config['prep']['weekly'])))
        self.c.drawString(main_width*0.8, 144*mm, str({None: ''}.get(tug.config['meetings']['weekly'], tug.config['meetings']['weekly'])))
        self.c.drawString(main_width*0.8, 138*mm, str({None: ''}.get(tug.config['prep_lectures']['weekly'], tug.config['prep_lectures']['weekly'])))
        self.c.drawString(main_width*0.8, 132*mm, str({None: ''}.get(tug.config['lectures']['weekly'], tug.config['lectures']['weekly'])))
        self.c.drawString(main_width*0.8, 126*mm, str({None: ''}.get(tug.config['support']['weekly'], tug.config['support']['weekly'])))
        self.c.drawString(main_width*0.8, 120*mm, str({None: ''}.get(tug.config['tutorials']['weekly'], tug.config['tutorials']['weekly'])))
        self.c.drawString(main_width*0.8, 114*mm, str({None: ''}.get(tug.config['leading']['weekly'], tug.config['leading']['weekly'])))
        self.c.drawString(main_width*0.8, 108*mm, str({None: ''}.get(tug.config['office_hours']['weekly'], tug.config['office_hours']['weekly'])))
        self.c.drawString(main_width*0.8, 102*mm, str({None: ''}.get(tug.config['e_communication']['weekly'], tug.config['e_communication']['weekly'])))
        self.c.drawString(main_width*0.8, 96*mm, str({None: ''}.get(tug.config['grading']['weekly'], tug.config['grading']['weekly'])))
        self.c.drawString(main_width*0.8, 90*mm, str({None: ''}.get(tug.config['test_prep']['weekly'], tug.config['test_prep']['weekly'])))
        self.c.drawString(main_width*0.8, 84*mm, str({None: ''}.get(tug.config['holiday']['weekly'], tug.config['holiday']['weekly'])))        
        xpos = 57*mm
        for other in tug.others():
            self.c.drawString(main_width*0.8, xpos, str({None: ''}.get(other.get('weekly'), other.get('weekly'))))            
            xpos = xpos - (5*mm)

        # total 
        self.c.drawString(main_width*0.9, 150*mm, str({None: ''}.get(tug.config['prep']['total'], tug.config['prep']['total'])))
        self.c.drawString(main_width*0.9, 144*mm, str({None: ''}.get(tug.config['meetings']['total'], tug.config['meetings']['total'])))
        self.c.drawString(main_width*0.9, 138*mm, str({None: ''}.get(tug.config['prep_lectures']['total'], tug.config['prep_lectures']['total'])))
        self.c.drawString(main_width*0.9, 132*mm, str({None: ''}.get(tug.config['lectures']['total'], tug.config['lectures']['total'])))
        self.c.drawString(main_width*0.9, 126*mm, str({None: ''}.get(tug.config['support']['total'], tug.config['support']['total'])))
        self.c.drawString(main_width*0.9, 120*mm, str({None: ''}.get(tug.config['tutorials']['total'], tug.config['tutorials']['total'])))
        self.c.drawString(main_width*0.9, 114*mm, str({None: ''}.get(tug.config['leading']['total'], tug.config['leading']['total'])))
        self.c.drawString(main_width*0.9, 108*mm, str({None: ''}.get(tug.config['office_hours']['total'], tug.config['office_hours']['total'])))
        self.c.drawString(main_width*0.9, 102*mm, str({None: ''}.get(tug.config['e_communication']['total'], tug.config['e_communication']['total'])))
        self.c.drawString(main_width*0.9, 96*mm, str({None: ''}.get(tug.config['grading']['total'], tug.config['grading']['total'])))
        self.c.drawString(main_width*0.9, 90*mm, str({None: ''}.get(tug.config['test_prep']['total'], tug.config['test_prep']['total'])))
        self.c.drawString(main_width*0.9, 84*mm, str({None: ''}.get(tug.config['holiday']['total'], tug.config['holiday']['total'])))
        xpos = 57*mm
        for other in tug.others():
            self.c.drawString(main_width*0.9, xpos, str({None: ''}.get(other.get('total'), other.get('total'))))            
            xpos = xpos - (5*mm)
        self.c.drawString(main_width*0.9, xpos-2*mm, str({None: ''}.get(total_hours, total_hours)))

        # draw tug description
        self.c.drawString(5, xpos-10*mm, "Teaching Assistants and course instructors should familiarize themselves with the general working conditions set out in Article 13C, ")
        self.c.drawString(5, xpos-15*mm, "assignment and compensation in Article 13D, and workload review mechanisms in Article 13E.")

        self.c.drawString(5, xpos-20*mm, "*There are no hours of work associated with the additional 0.17 base unit for preparation, Article 13D. 2 b. See Appendix B for")
        self.c.drawString(5, xpos-25*mm, "calculation of hours.")
        self.c.drawString(5, xpos-30*mm, "** Includes grading of all assignments, reports and examinations - whether in class/lab or afterwards.")
        self.c.drawString(5, xpos-35*mm, "*** Attendance at a TA/TM Day/and other required Training")

        self.c.drawString(5, xpos-50*mm, "Instructor Signature:")
        self.c.drawString(main_width/2, xpos-50*mm, "TA Signature:")
        self.c.drawString(5, xpos-55*mm, "Date:")
        self.c.drawString(main_width/2, xpos-55*mm, "Date:")

    def save(self):
        self.c.save()

def taworkload_form(taworkload, max_hours, outfile):
    """
    Generate TUG Form for individual TA.
    """
    doc = WRForm(outfile)
    doc.draw_form_wr(taworkload, max_hours)
    doc.save()    

class WRForm(object):
    """
    For for HR to appoint a TA
    """
    BOX_HEIGHT = 0.25*inch
    LABEL_RIGHT = 2
    LABEL_UP = 2
    CONTENT_RIGHT = 4
    CONTENT_UP = 4
    LABEL_SIZE = 6
    CONTENT_SIZE = 12
    NOTE_STYLE = ParagraphStyle(name='Normal',
                                fontName='Helvetica',
                                fontSize=7,
                                leading=10,
                                alignment=TA_LEFT,
                                textColor=black)
                        

    def __init__(self, outfile):
        """
        Create TUGForm in the file object (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)

    def _draw_box(self, x, y, width, label='', label_size=LABEL_SIZE, content='', content_size=CONTENT_SIZE, right=False):
        height = self.BOX_HEIGHT
        self.c.setLineWidth(1)
        self.c.rect(x, y, width, height)

        if label:
            self.c.setFont("Helvetica", label_size)
            self.c.drawString(x + self.LABEL_RIGHT, y + height + self.LABEL_UP, label)

        if content:
            self.c.setFont("Helvetica", content_size)
            if right:
                self.c.drawRightString(x + width - self.CONTENT_RIGHT, y + self.CONTENT_UP, content)
            else:
                self.c.drawString(x + self.CONTENT_RIGHT, y + self.CONTENT_UP, content)


    def draw_form_wr(self, taworkload, max_hours):
        """
        Draw the form for an new-style contract (tacontract module)
        """
        return self.draw_form(                
                taworkload = taworkload,
                max_hours = max_hours
        )

    def draw_form(self, taworkload, max_hours):
        """
        Generic TA Form drawing method: probably called by one of the above that abstract out the object details.
        """

        self.c.setStrokeColor(black)
        self.c.translate(0.625*inch, 1.25*inch) # origin = lower-left of the main box
        main_width = 7.25*inch

        # draw line
        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.5)
        p = self.c.beginPath()

        # WR
        #self.c.drawImage(logofile, x=main_width/2 - 0.5*inch, y=227*mm, width=1*inch, height=0.5*inch)
        self.c.drawImage(logofile, x=0, y=227*mm, width=1*inch, height=0.5*inch)
        self.c.setFont("Times-Roman", 12)
        self.c.drawString(2.8*inch, 235*mm, "Simon Fraser University")
        self.c.setFont("Times-Roman", 12)
        self.c.drawString(3*inch, 228*mm, "TA Workload Review")

        # draw WR header
        self.c.setFont("Times-Roman", 10)
        self.c.drawString(0, 200*mm, "Instructor: " + taworkload.member.offering.instructors_str())
        self.c.drawString(main_width*0.7, 200*mm, "TA Name: " + taworkload.member.person.name())
        p.moveTo(0, 198*mm)   #x, y
        p.lineTo(main_width, 198*mm)

        self.c.drawString(0, 190*mm, "Semester: " + str(taworkload.member.offering.semester))
        self.c.drawString(main_width*0.3, 190*mm, "Course #: " + str(taworkload.member.offering.name()))
        self.c.drawString(main_width*0.7, 190*mm, "Original hrs Assigned: " + str(max_hours))
        p.moveTo(0, 188*mm)
        p.lineTo(main_width, 188*mm)

        self.c.drawString(main_width*0.2, 180*mm, "Will the number of hours required exceed the number of hours assigned?")
        if taworkload:
            if taworkload.reviewhour:
                self.c.drawString(main_width/2-18*mm, 170*mm, "YES")
            else:
                self.c.drawString(main_width/2-18*mm, 170*mm, "NO")
        p.moveTo(main_width/2-18*mm, 168*mm)
        p.lineTo((main_width+18*mm)/2, 168*mm)

        self.c.drawString(0, 160*mm, "Signature of Instructor:")
        self.c.drawString(main_width*0.7, 160*mm, "Date of Review:")
        if taworkload:
            self.c.drawString(0, 150*mm, str(taworkload.reviewsignature))
        p.moveTo(0, 148*mm)
        p.lineTo(main_width*0.3, 148*mm)
        if taworkload:
            self.c.drawString(main_width*0.7, 150*mm, str(taworkload.reviewdate))
        p.moveTo(main_width*0.7, 148*mm)
        p.lineTo(main_width, 148*mm)

        import textwrap
        self.c.drawString(main_width*0.2, 130*mm, "Decision if number of hours required exceeds the number or hours assigned:")
        if taworkload:
            reviewcomment = textwrap.wrap(str(taworkload.reviewcomment), 128)        
            xpos = 120*mm
            for i in range(len(reviewcomment)):
                self.c.drawString(0, xpos, str(reviewcomment[i]))
                p.moveTo(0, xpos-2*mm)   #x, y
                p.lineTo(main_width, xpos-2*mm)
                xpos = xpos-7*mm
                if i>12:
                    break

        if xpos-10*mm > 0:
            self.c.drawString(main_width/2, xpos-10*mm, "Signature of Authorized person in the Department")
            p.moveTo(0, xpos-10*mm)
            p.lineTo(main_width/2, xpos-10*mm)
        else:
            self.c.showPage()
            self.c.drawString(main_width/2, 220*mm, "Signature of Authorized person in the Department")
            p.moveTo(0, 220*mm)
            p.lineTo(main_width/2, 220*mm)

        #p.close()
        self.c.drawPath(p, stroke=1, fill=0)


    def save(self):
        self.c.save()         