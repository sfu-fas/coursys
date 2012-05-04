from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Spacer, Frame, KeepTogether, NextPageTemplate, PageBreak, Image, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import textobject, canvas
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont  
from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
import os, datetime
from dashboard.models import Signature

PAPER_SIZE = letter
black = CMYKColor(0, 0, 0, 1)
media_path = os.path.join('external', 'sfu')
logofile = os.path.join(media_path, 'logo.png')

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
        ttfFile = os.path.join(media_path, 'BemboMTPro-Regular.ttf')
        pdfmetrics.registerFont(TTFont("BemboMTPro", ttfFile))  
        ttfFile = os.path.join(media_path, 'DINPro-Regular.ttf')
        pdfmetrics.registerFont(TTFont("DINPro", ttfFile))  
        
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
                 closing="Yours truly", signer=None, paragraphs=None, cosigner_lines=None):
        self.date = date or datetime.date.today()
        self.salutation = salutation
        self.closing = closing
        self.flowables = []
        self.to_addr_lines = to_addr_lines
        self.from_name_lines = from_name_lines
        self.cosigner_lines = cosigner_lines
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
        # signature
        signature = [Paragraph(self.closing+",", style)]
        img = None
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
                signature.append(Spacer(1, space_height))
                signature.append(img)
            except Signature.DoesNotExist:
                signature.append(Spacer(1, 4*space_height))
        else:
            signature.append(Spacer(1, 4*space_height))
        
        for line in self.from_name_lines:
            signature.append(Paragraph(line, style))

        if self.cosigner_lines:
            # we have two signatures to display: rebuild the signature part in a table with both
            data = []
            data.append([Paragraph(self.closing+",", style), Paragraph(self.cosigner_lines[0]+",", style)])
            if img:
                data.append([img, Spacer(1, 4*space_height)])
            else:
                data.append([Spacer(1, 4*space_height), Spacer(1, 4*space_height)])

            extra = [''] * (len(self.from_name_lines) + len(self.cosigner_lines[1:]))
            for l1,l2 in zip(self.from_name_lines+extra, self.cosigner_lines[1:]+extra):
                if l1 or l2:
                    data.append([Paragraph(l1, style), Paragraph(l2, style)])            
            
            sig_table = Table(data)
            sig_table.setStyle(TableStyle(
                    [('LEFTPADDING', (0,0), (-1,-1), 0),
                     ('RIGHTPADDING', (0,0), (-1,-1), 0),
                     ('TOPPADDING', (0,0), (-1,-1), 0),
                     ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))

            close.append(sig_table)
        else:
            close.extend(signature)
        
        contents.append(KeepTogether(close))
        contents.append(NextPageTemplate(0)) # next letter starts on letterhead again
        contents.append(PageBreak())
        
        return contents


class RAForm(object):
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
        sin = "%09i" % (self.ra.sin)
        sin = sin[:3] + '-' + sin[3:6] + '-' + sin[6:]
        self._draw_box_left(0, self.MAIN_HEIGHT, width=3.125*inch, label="SOCIAL INSURANCE NUMBER (SIN)", content=sin)

        # emplid
        emplid = unicode(self.ra.person.emplid)
        emplid = emplid[:5] + '-' + emplid[5:]
        self._draw_box_right(0, self.MAIN_HEIGHT, width=3.375*inch, label="SFU ID #", content=emplid)
        
        # names
        self._draw_box_left(0, self.MAIN_HEIGHT - self.ENTRY_HEIGHT, label="LAST OR FAMILY NAME", content=self.ra.person.last_name)
        self._draw_box_left(0, self.MAIN_HEIGHT - 2*self.ENTRY_HEIGHT, label="FIRST NAME", content=self.ra.person.first_name)
        
        height = 5.875*inch
        self._rule(height)
        
        # position
        self._draw_box_left(0, height, width=3.125*inch, label="POSITION NUMBER", content='') # to be filled by HR
        self._draw_box_right(0, height, width=3.75*inch, label="POSITION TITLE", content=unicode(self.ra.account.title))
        
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
        self._draw_box_left(0, height, width=2.125*inch, label="START DATE (yyyy/mm/dd)", content=unicode(self.ra.start_date).replace('-', '/'))
        self._draw_box_left(3*inch, height, width=1.5*inch, label="END DATE (yyyy/mm/dd)", content=unicode(self.ra.end_date).replace('-', '/'))

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
            default_note = "For total amount of $%s over %i pay periods." % (self.ra.lump_sum_pay, self.ra.pay_periods)
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
        self.c.drawString(0, height-50, "REVISED Nov 2004 (produced by CourSys RAForm)")
        
        self.c.showPage()
        self.c.save()


def ra_form(ra, outfile):
    """
    Generate FPP4 form for this RAAppointment.
    """
    form = RAForm(ra)
    return form.draw_pdf(outfile)


class TAForm(object):
    BOX_HEIGHT = 0.25*inch
    LABEL_RIGHT = 2
    LABEL_UP = 2
    CONTENT_RIGHT = 4
    CONTENT_UP = 4
    LABEL_SIZE = 6
    CONTENT_SIZE = 12
    NOTE_STYLE = ParagraphStyle(name='Normal',
                                fontName='Helvetica',
                                fontSize=9,
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

    def draw_form(self, contract):
        """
        Generates form for this contract
        """
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
        self._draw_box(0, 8.625*inch, 43*mm, label="SFU ID #", content=unicode(contract.application.person.emplid))
        self._draw_box(0, 210*mm, 43*mm, label="CANADA SOCIAL INSURANCE NO.", content=unicode(contract.application.sin))
        self._draw_box(46*mm, 210*mm, 74*mm, label="LAST OR FAMILY NAME", content=unicode(contract.application.person.last_name))
        self._draw_box(125*mm, 210*mm, 50*mm, label="FIRST NAME", content=unicode(contract.application.person.first_name))
        self._draw_box(15*mm, 202*mm, 160*mm, content="c/o " + unicode(contract.application.posting.unit.name)) # ADDRESS
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(2, 206*mm, "HOME")
        self.c.drawString(2, 203*mm, "ADDRESS")
        
        # appointment basic info
        self.c.drawString(2, 194*mm, "DEPARTMENT")
        dept = unicode(contract.application.posting.unit.informal_name())
        if contract.application.posting.unit.deptid():
            dept += " (%s)" % (contract.application.posting.unit.deptid())
        self._draw_box(20*mm, 193*mm, 78*mm, content=dept) # DEPARTMENT
        self._draw_box(102*mm, 193*mm, 32*mm, label="APPOINTMENT START DATE", content=unicode(contract.pay_start))
        self._draw_box(139*mm, 193*mm, 32*mm, label="APPOINTMENT END DATE", content=unicode(contract.pay_end))
        
        # initial appointment boxes
        self.c.rect(14*mm, 185*mm, 5*mm, 5*mm, fill=1)
        self.c.rect(14*mm, 176*mm, 5*mm, 5*mm, fill=0)
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(21*mm, 188*mm, "INITIAL APPOINTMENT TO")
        self.c.drawString(21*mm, 186*mm, "THIS POSITION NUMBER")
        self.c.setFont("Helvetica", 5)
        self.c.drawString(21*mm, 179*mm, "REAPPOINTMENT TO SAME POSITION")
        self.c.drawString(21*mm, 177*mm, "NUMBER OR REVISION TO APPOINTMENT")

        # position info
        self._draw_box(60*mm, 176*mm, 37*mm, label="POSITION NUMBER", content=unicode(contract.position_number.position_number))
        self._draw_box(102*mm, 176*mm, 32*mm, label="PAYROLL START DATE", content=unicode(contract.pay_start))
        self._draw_box(139*mm, 176*mm, 32*mm, label="PAYROLL END DATE", content=unicode(contract.pay_end))
        
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
        courses = contract.tacourse_set.filter(bu__gt=0)
        total_bu = 0
        for i, crs in zip(range(5), list(courses)+[None]*5):
            h = 162*mm - i*6*mm # bottom of this row
            self.c.rect(24*mm, h, 27*mm, 6*mm)
            self.c.rect(51*mm, h, 74*mm, 6*mm)
            self.c.rect(125*mm, h, 23*mm, 6*mm)
            
            self.c.setFont("Helvetica", self.CONTENT_SIZE-2)
            if crs:
                self.c.drawString(25*mm, h + 1*mm, crs.course.subject + ' ' + crs.course.number + ' ' + crs.course.section[:2])
                self.c.drawString(52*mm, h + 1*mm, crs.get_description_display())
                self.c.drawRightString(147*mm, h + 1*mm, "%.2f" % (crs.bu))
                total_bu += crs.bu
        
        self.c.rect(125*mm, 132*mm, 23*mm, 6*mm)
        self.c.drawRightString(147*mm, 133*mm, "%.2f" % (total_bu))
        
        self._draw_box(153*mm, 155*mm, 22*mm, label="APPT. CATEGORY", content=contract.application.category)
            
        # salary/scholarship
        pp = contract.posting.payperiods()
        total_pay = total_bu*contract.pay_per_bu
        biweek_pay = total_pay/pp
        total_schol = total_bu*contract.scholarship_per_bu
        biweek_schol = total_schol/pp
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

        self._draw_box(139*mm, 122*mm, 32*mm, label="EFF. DATE FOR RATE CHANGES", content=unicode(contract.pay_start))
        self.c.setFont("Helvetica", 5)
        self.c.drawString(114*mm, 125*mm, "THESE RATES INCLUDE 4%")
        self.c.drawString(114*mm, 123*mm, "VACATION PAY")
        
        # remarks
        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(1*mm, 103*mm, "REMARKS")
        f = Frame(3*mm, 82*mm, main_width - 6*mm, 22*mm) #, showBoundary=1 
        notes = []
        notes.append(Paragraph(contract.remarks, style=self.NOTE_STYLE))
        f.addFromList(notes, self.c)

        # instructions
        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(5*mm, 78*mm, "INSTRUCTIONS TO THE APPOINTEE")
        self.c.setLineWidth(1)
        self.c.line(0, 76*mm+self.BOX_HEIGHT, main_width, 76*mm+self.BOX_HEIGHT)
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(100*mm, 78*mm, "DEADLINE FOR ACCEPTANCE")
        self._draw_box(139*mm, 76*mm, 32*mm, label="", content=unicode(contract.deadline))
        

        self.c.setFont("Helvetica", 6)
        self.c.drawString(5*mm, 71*mm, "1. a) This offer of appointment is conditional upon you accepting this appointment by signing and dating this appointment form (see bottom right hand corner box) and returning the signed")
        self.c.drawString(5*mm, 71*mm - 7, "form to the Dean's Office by the deadline for acceptance above.")
        self.c.drawString(5*mm, 71*mm - 14, "1. b) If this is an initial appointment in the TSSU bargaining unit, then as a condition of employment under the terms of the Colletive Agreement you must complete and sign the first two")
        self.c.drawString(5*mm, 71*mm - 21, 'sections of the attached form entitled "Appendix A to Article IV Dues and Union Membership or Non Membership" and return it with this appointment form.')
        
        self.c.drawString(5*mm, 60*mm, "2. Citizenship        Please complete a) or b) below")
        self.c.drawString(10*mm, 60*mm - 7, "a) First appointment in the category. Please check the box which indicates your status.")
        
        self.c.drawString(15*mm, 53*mm, "i Canadian citizen")
        self.c.drawString(56*mm, 53*mm, "ii Permanent Resident")
        self.c.drawString(98*mm, 53*mm, "iii Work or Study Permit*")
        self.c.drawString(131*mm, 53*mm, "* Please attach copy to this form.")
        self.c.rect(37*mm, 52*mm, 3*mm, 3*mm)
        self.c.rect(80*mm, 52*mm, 3*mm, 3*mm)
        self.c.rect(125*mm, 52*mm, 3*mm, 3*mm)
        
        self.c.drawString(10*mm, 49*mm, "b) Reappointment to this category")
        self.c.drawString(15*mm, 49*mm - 10, "i Has your citizenship status changed since your last appointment?")
        self.c.drawString(112*mm, 49*mm - 10, "No")
        self.c.drawString(130*mm, 49*mm - 10, "Yes")
        self.c.drawString(142*mm, 49*mm - 10, "Explain")
        self.c.rect(116*mm, 48*mm - 10, 3*mm, 3*mm)
        self.c.rect(135*mm, 48*mm - 10, 3*mm, 3*mm)
        
        self.c.drawString(15*mm, 49*mm - 20, "ii If you hold an employment authorization, please attach a copy to this form when you return it.")
        self.c.drawString(15*mm, 49*mm - 30, "N.B. If you are a student and an employee, and are not a Canadian citizen or permanent resident, you are required to hold a valid work or study permit.")
        
        self.c.drawString(5*mm, 32*mm, "3. Please check the box at the top of this form containing the Social Insurance No. If it is empty or incorrect, please provide the correct SIN#.")
        self.c.drawString(5*mm, 28*mm, "4. If you do not wish to accept this offer of appointment, please advise the department as soon as possible. If you have not accepted this appointment by the deadline shown above, it will")
        self.c.drawString(5*mm, 28*mm - 7, "be assumed that you have declined the offer of appointment")

        self.c.drawString(15*mm, 20*mm, "Appointment conditional upon enrolment")
        fill = 1 if contract.appt_cond else 0
        self.c.rect(59*mm, 19*mm, 3*mm, 3*mm, fill=fill)
        self.c.drawString(79*mm, 20*mm, "Appointment in TSSU Bargaining unit")
        fill = 1 if contract.appt_tssu else 0
        self.c.rect(120*mm, 19*mm, 3*mm, 3*mm, fill=fill)
        
        # signatures
        sigs = Signature.objects.filter(user__userid=contract.created_by)
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
        self.c.drawString(121*mm, 16*mm, "ACCEPTED BY APPOINTEE")
        self.c.drawString(1*mm, 1*mm, "DATE")
        self.c.drawString(61*mm, 1*mm, "DATE")
        self.c.drawString(121*mm, 1*mm, "DATE")
        
        self.c.setFont("Helvetica", self.CONTENT_SIZE)
        date = datetime.date.today()
        self.c.drawString(10*mm, 2*mm, unicode(date))
        
        # footer
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(1*mm, -3*mm, "ORIGINAL: DEAN     COPY : EMPLOYEE     COPY : DEPARTMENT     COPY : UNION (IF TSSU APP'T)     COPY: PAYROLL")
        self.c.setFont("Helvetica", 3.25)
        self.c.drawString(1*mm, -5*mm, "THE INFORMATION ON THIS FORM IS COLLECTED UNDER THE AUTHORITY OF THE UNIVERSITY ACT (RSBC 1996, C.468), THE INCOME TAX ACT, THE PENSION PLAN ACT, THE EMPLOYMENT INSURANCE ACT, THE FINANCIAL INFORMATION ACT OF BC, AND THE WORKERS COMPENSATION ACT OF BC. THE")
        self.c.drawString(1*mm, -5*mm - 4, "INFORMATION ON THIS FORM IS USED BY THE UNIVERSITY FOR PAYROLL AND BENEFIT PLAN ADMINISTRATION, STATISTICAL COMPILATIONS AND OPERATING PROGRAMS AND ACTIVITIES AS REQUIRED BY UNIVERSITY POLICIES. THE INFORMATION ON THIS FORM IS DISCLOSED TO GOVERNMENT AGENCIES")
        self.c.drawString(1*mm, -5*mm - 8, "AS REQUIRED BY THE GOVERNMENT ACTS. YOUR BANKING INFORMATION IS DISCLOSED TO FINANCIAL INSITUTIONS FOR THE PURPOSE OF DIRECT DEPOSIT. IN ACCORDANCE WITH THE FINANCIAL INFORMATION ACT OF BC, YOUR NAME AND REMUNERATION IS PUBLIC INFORMATION AND MAY BE")
        self.c.drawString(1*mm, -5*mm - 12, "PUBLISHED.")
        self.c.drawString(1*mm, -5*mm - 20, "IF YOU HAVE ANY QUESTIONS ABOUT THE COLLECTION AND USE OF THIS INFORMATION, PLEASE CONTACT THE SIMON FRASER UNIVERSITY PAYROLL SUPERVISOR.")

        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(1*mm, -18*mm, "Updated December 2004 (produced by CourSys TAForm)")

        self.c.showPage()
    
    def save(self):
        self.c.save()

def ta_form(contract, outfile):
    """
    Generate TA Appointment Form for this TAContract.
    """
    doc = TAForm(outfile)
    doc.draw_form(contract)
    doc.save()

def ta_forms(contracts, outfile):
    """
    Generate TA Appointment Forms for this list of TAContracts (in one PDF)
    """
    doc = TAForm(outfile)
    for c in contracts:
        doc.draw_form(c)
    doc.save()

