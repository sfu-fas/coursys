"""
All of the system's PDF generation lives here.

It's just easier that way: so many imports and commonalities between these chunks of code,
even though they serve very different parts of the overall system.
"""

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
from coredata.models import Role
from django.conf import settings
import os, datetime
from dashboard.models import Signature
from coredata.models import Semester
from grad.models import STATUS_APPLICANT

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
    saluations: letter's salutation (string)
    closing: letter's closing (string)
    signer: person signing the letter, if knows (a coredata.models.Person)
    """
    def __init__(self, to_addr_lines, from_name_lines, date=None, salutation="To whom it may concern",
                 closing="Yours truly", signer=None, paragraphs=None, cosigner_lines=None, use_sig=True):
        self.date = date or datetime.date.today()
        self.salutation = salutation
        self.closing = closing
        self.flowables = []
        self.to_addr_lines = to_addr_lines
        self.from_name_lines = from_name_lines
        self.cosigner_lines = cosigner_lines
        self.signer = signer
        self.use_sig = use_sig
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
        self.table_style = TableStyle([
                    ('FONT', (0,0), (-1,-1), 'BemboMTPro', 12, self.line_height),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ])
        
    def make_flowable(self, text):
        if text.startswith('||'):
            # it's our table microformat
            lines = text.split('\n')
            cells = [line.split('|')[2:] for line in lines] # [2:] effectively strips the leading '||'
            return Table(cells, style=self.table_style)
        else:
            return Paragraph(text, self.content_style)
    
    def add_paragraph(self, text):
        "Add a paragraph (represented as a string) to the letter: used by OfficialLetter.add_letter"
        self.flowables.append(self.make_flowable(text))

    def add_paragraphs(self, paragraphs):
        "Add a list of paragraphs (strings) to the letter"
        self.flowables.extend([self.make_flowable(text) for text in paragraphs])
    
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
        if self.salutation:
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
        if self.signer and self.use_sig:
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

class RAForm(object, SFUMediaMixin):
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
        self._drawStringLeading(self.c, 23*mm, 250*mm, u'Simon Fraser University'.translate(self.sc_trans_bembo), charspace=1.4)
        self.c.setFont('DINPro', 5)
        self.c.setFillColor(self.sfu_grey)
        self._drawStringLeading(self.c, 23*mm, 247.5*mm, u'Engaging the World'.upper(), charspace=2)
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
        self._checkbox(1.5*mm, 211*mm, text="Research Services Staff", filled=(cat=='RSS'))
        self._checkbox(1.5*mm, 206*mm, text="Post Doctoral Fellows", filled=(cat=='PDF'))
        self._checkbox(1.5*mm, 201*mm, text="Other Non Continuing", filled=(cat=='ONC'))
        self._checkbox(67*mm, 215.5*mm, text="University Research Assistant (R50.04)", leading=1.5*mm, filled=(cat=='RA2'))
        self.c.setFont("Helvetica", 5)
        self.c.drawString(72*mm, 215*mm, "Min of 2 years with Benefits")
        self._checkbox(67*mm, 203*mm, text="University Research Assistant (R50.04)", leading=1.5*mm, filled=(cat=='RAR'))
        self.c.setFont("Helvetica", 5)
        self.c.drawString(72*mm, 202.5*mm, "Renewal after 2 years with Benefits")
        self._checkbox(142*mm, 215.5*mm, text="Graduate Research Assistant", filled=(cat=='GRA'))
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
        
        self._box_entry(83*mm, 188*mm, 51*mm, 6.5*mm, content=unicode(self.ra.sin))
        self._box_entry(148*mm, 188*mm, 55*mm, 6.5*mm, content=unicode(self.ra.person.emplid))
        
        self.c.setLineWidth(1)
        self.c.line(0, 181*mm, self.MAIN_WIDTH, 181*mm)
        
        # personal/position details
        self.c.setFont("Helvetica", 9)
        self.c.drawString(3*mm, 176*mm, "Last Name")
        self.c.drawString(94*mm, 176*mm, "First Name")
        self.c.drawString(185*mm, 176*mm, "Initial")
        self._box_entry(1.5*mm, 165*mm, 87*mm, 7.5*mm, content=unicode(self.ra.person.last_name))
        self._box_entry(92*mm, 165*mm, 86*mm, 7.5*mm, content=unicode(self.ra.person.first_name))
        mi = None
        if self.ra.person.middle_name:
            mi = self.ra.person.middle_name[0]
        self._box_entry(183*mm, 165*mm, 19*mm, 7.5*mm, content=mi)
        
        self.c.setFont("Helvetica", 8)
        self.c.drawString(2.5*mm, 158*mm, "Department")
        self.c.drawString(117*mm, 158*mm, "Position Title")
        self._box_entry(30*mm, 156*mm, 83*mm, 6.5*mm, content=self.ra.unit.informal_name())
        self._box_entry(136*mm, 156*mm, 66*mm, 6.5*mm, content=unicode(self.ra.account.title))
        
        # position numbers
        self.c.setFont("Helvetica", 7)
        self.c.drawString(1.5*mm, 148*mm, "Fund (2 digit)")
        self.c.drawString(23*mm, 148*mm, "Dept (5 digit)")
        self.c.drawString(66*mm, 148*mm, "Prjct Num (6 digit)")
        self.c.drawString(110*mm, 148*mm, "Acct (4 digit)")
        self.c.drawString(151*mm, 148*mm, "Position Number")
        self._box_entry(1.5*mm, 139*mm, 16*mm, 6.5*mm, content="%i" % (self.ra.project.fund_number))
        self._box_entry(23*mm, 139*mm, 38*mm, 6.5*mm, content=unicode(self.ra.unit.deptid()))
        self._box_entry(66*mm, 139*mm, 38*mm, 6.5*mm, content="%06i" % (self.ra.project.project_number))
        self._box_entry(110*mm, 139*mm, 29*mm, 6.5*mm, content="%06i" % (self.ra.account.account_number))
        self._box_entry(150*mm, 139*mm, 48*mm, 6.5*mm, content='')
        
        # dates
        self.c.setFont("Helvetica", 8)
        self.c.drawString(1.5*mm, 133*mm, "Start Date")
        self.c.drawString(73*mm, 133*mm, "End Date")
        self._box_entry(21.5*mm, 131.5*mm, 42*mm, 5.5*mm, content=unicode(self.ra.start_date).replace('-', '/'))
        self._box_entry(92.5*mm, 131.5*mm, 42*mm, 5.5*mm, content=unicode(self.ra.end_date).replace('-', '/'))

        # money
        if self.ra.pay_frequency == 'L':
            hourly = ''
            biweekly = ''
            biweekhours = ''
            if self.ra.lump_sum_hours and self.ra.use_hourly():
                lumphours = unicode(self.ra.lump_sum_hours)
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
        
        self._box_entry(103*mm, 101*mm, 15.5*mm, 8*mm, content=biweekhours)
        self._box_entry(168*mm, 101*mm, 15.5*mm, 8*mm, content=lumphours)
        
        self.c.setFont("Helvetica", 5)
        self.c.drawString(1.5*mm, 96*mm, "Notes:")
        self.c.drawString(23*mm, 96*mm, "Bi-Weekly employment earnings rate must include vacation pay. Hourly rates will automatically have vacation pay added. The employer cost of the statutory benefits will be charged to the account in")
        self.c.drawString(23*mm, 93*mm, "addition to the earnings rate. Bi-weekly hours must reflect the number of hours worked and must meet legislative requirements for minimum wage.")
        
        # Commments
        self.c.setFont("Helvetica", 9)
        self.c.drawString(2*mm, 81.5*mm, "Comments:")
        self.c.setLineWidth(1)
        self._box_entry(22*mm, 76*mm, 180*mm, 14*mm, content='')

        f = Frame(23*mm, 76*mm, 175*mm, 14*mm)#, showBoundary=1)
        notes = []
        if self.ra.pay_frequency != 'L':
            default_note = "For total amount of $%s over %.1f pay periods." % (self.ra.lump_sum_pay, self.ra.pay_periods)
        else:
            default_note = "Lump sum payment of $%s." % (self.ra.lump_sum_pay,)
        notes.append(Paragraph(default_note, style=self.NOTE_STYLE))
        notes.append(Spacer(1, 8))
        notes.append(Paragraph(self.ra.notes, style=self.NOTE_STYLE))
        f.addFromList(notes, self.c)
        
        self.c.setFont("Helvetica", 7.5)
        self.c.drawString(2.5*mm, 72*mm, "As signing authority, I certify that the appointment and its applicable benefits are eligible and for the purpose of the funding. Furthermore, the appointment is NOT for a")
        self.c.drawString(2.5*mm, 68.5*mm, "family member of the account holder or signing authority. If a family member relationship exists then additional approvals must be attached in accordance with policies")
        self.c.drawString(2.5*mm, 65*mm, "GP 37 and R10.01. Please see the procedures contained in GP 37 for more information.")

        # signatures
        self.c.setFont("Helvetica", 9)
        self.c.drawString(2*mm, 59*mm, "HIRING DEPARTMENT")
        self.c.drawString(117*mm, 59*mm, "REVIEWED BY")
        self.c.setFont("Helvetica", 7)
        self.c.drawString(2*mm, 51*mm, "Signing Authority")
        self.c.drawString(2*mm, 43*mm, "Date")
        self.c.drawString(98*mm, 51*mm, "Signing Authority")
        self.c.drawString(98*mm, 43*mm, "Date")
        self.c.drawString(2*mm, 32.5*mm, "Prepared by/Conact")
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
        self.c.drawString(2*mm, -5*mm, "PAYROLL APPOINTMENT FORM (formerly FPP4) - July 2013 (produced by CourSys RAForm)")

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
        self.c.drawString(0, height-50, "REVISED Nov 2004 (produced by CourSys RAForm)")
        
        self.c.showPage()
        self.c.save()


def ra_form(ra, outfile):
    """
    Generate PAF form for this RAAppointment.
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
        self._draw_box(0, 210*mm, 43*mm, label="CANADA SOCIAL INSURANCE NO.", content=unicode(contract.sin))
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
        
        initial_appointment_fill = 0
        if contract.appt == "INIT":
            initial_appointment_fill = 1
        reappointment_fill = 0
        if contract.appt == "REAP":
            reappointment_fill = 1

        self.c.rect(14*mm, 185*mm, 5*mm, 5*mm, fill=initial_appointment_fill)
        self.c.rect(14*mm, 176*mm, 5*mm, 5*mm, fill=reappointment_fill)
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
        bu = 0
        for i, crs in zip(range(5), list(courses)+[None]*5):
            h = 162*mm - i*6*mm # bottom of this row
            self.c.rect(24*mm, h, 27*mm, 6*mm)
            self.c.rect(51*mm, h, 74*mm, 6*mm)
            self.c.rect(125*mm, h, 23*mm, 6*mm)
            
            self.c.setFont("Helvetica", self.CONTENT_SIZE-2)
            if crs:
                self.c.drawString(25*mm, h + 1*mm, crs.course.subject + ' ' + crs.course.number + ' ' + crs.course.section[:2])
                self.c.drawString(52*mm, h + 1*mm, crs.description.description)
                self.c.drawRightString(147*mm, h + 1*mm, "%.2f" % (crs.total_bu))
                bu += crs.bu
                total_bu += crs.total_bu
        
        self.c.rect(125*mm, 132*mm, 23*mm, 6*mm)
        self.c.drawRightString(147*mm, 133*mm, "%.2f" % (total_bu))
        
        self._draw_box(153*mm, 155*mm, 22*mm, label="APPT. CATEGORY", content=contract.appt_category)
            
        # salary/scholarship
        pp = contract.posting.payperiods()
        total_pay = total_bu*contract.pay_per_bu
        biweek_pay = total_pay/pp
        total_schol = bu*contract.scholarship_per_bu
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
        self.c.drawString(43*mm, 228*mm, u"RECORDS AND REGISTRATION".translate(self.sc_trans_bembo))
        self.c.drawString(43*mm, 223*mm, u"STUDENT SERVICES".translate(self.sc_trans_bembo))
        self.title_font()
        self.c.drawString(121*mm, 228*mm, u"CHANGE OF GRADE NOTIFICATION")
        self.c.drawString(121*mm, 224*mm, u'AND/OR EXTENSION OF "DE" GRADE')
        
        # student info
        self.title_font()
        self.c.drawString(0, 210*mm, u"SFU STUDENT NUMBER")
        self.c.rect(35*mm, 207*mm, 92*mm, 8*mm, fill=0)
        self.entry_font()
        self.c.drawString(40*mm, 209*mm, unicode(member.person.emplid))

        self.title_font()
        self.c.drawString(0, 203*mm, u"STUDENT NAME (PLEASE PRINT CLEARLY)")

        self.label_font()
        self.c.drawString(0, 195*mm, u"Surname")
        self.c.line(12*mm, 195*mm, 91*mm, 195*mm)
        self.c.drawString(93*mm, 195*mm, u"Given Names")
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
        self.c.drawString(0, 189*mm, u"TERM")
        self.label_font()
        self.c.drawString(0, 183*mm, u"Year")
        self.c.line(6*mm, 183*mm, 30*mm, 183*mm)
        self.check_label(36*mm, 183*mm, 'Fall', fill=semester=='7')
        self.check_label(50*mm, 183*mm, 'Spring', fill=semester=='1')
        self.check_label(67*mm, 183*mm, 'Summer', fill=semester=='4')
        self.check_label(86*mm, 183*mm, 'Intersession', fill=0)
        self.check_label(110*mm, 183*mm, 'Summer Session', fill=0)
        self.c.rect(140*mm, 183*mm, 40*mm, 8*mm, fill=0)
        self.c.drawString(148*mm, 178*mm, u"4-digit term number")
        self.entry_font()
        self.c.drawString(10*mm, 184*mm, unicode(year))
        self.c.drawString(148*mm, 185*mm, unicode(name))
        
        # course info
        self.title_font()
        self.c.drawString(0, 175*mm, u"COURSE")
        self.label_font()
        self.c.drawString(0, 169*mm, u"Course subject (e.g. CHEM)")
        self.c.rect(36*mm, 168*mm, 41*mm, 8*mm, fill=0)
        self.c.drawString(81*mm, 169*mm, u"Course number")
        self.c.rect(102*mm, 168*mm, 41*mm, 8*mm, fill=0)
        self.entry_font()
        self.c.drawString(40*mm, 170*mm, member.offering.subject)
        self.c.drawString(110*mm, 170*mm, member.offering.number)
        self.label_font()
        self.c.drawString(0, 159*mm, u"Class number/section")
        self.c.rect(28*mm, 157*mm, 51*mm, 8*mm, fill=0)
        self.c.drawString(82*mm, 159*mm, u"Course title")
        self.c.line(97*mm, 159*mm, main_width, 159*mm)
        self.entry_font()
        self.c.drawString(35*mm, 159*mm, member.offering.section)
        self.entry_font_small()
        self.c.drawString(98*mm, 160*mm, member.offering.title)
        
        # grade change
        self.title_font()
        self.c.drawString(0, 149*mm, u"IF CHANGE OF GRADE:")
        self.label_font()
        self.c.drawString(0, 141*mm, u"Original grade")
        self.c.rect(20*mm, 139*mm, 21*mm, 8*mm, fill=0)
        self.c.drawString(45*mm, 141*mm, u"Revised grade")
        self.c.rect(64*mm, 139*mm, 21*mm, 8*mm, fill=0)
        self.entry_font()
        if oldgrade:
            old = oldgrade
        else:
            old = u'' 
        if newgrade:
            new = newgrade
        else:
            new = u'' 
        self.c.drawString(25*mm, 141*mm, old)
        self.c.drawString(69*mm, 141*mm, new)

        # DE extension
        self.title_font()
        self.c.drawString(0, 132*mm, u"IF EXTENSION OF \u201CDE\u201D GRADE:")
        self.label_font()
        self.c.drawString(0, 127*mm, u"Extension due date:")
        self.c.drawString(30*mm, 127*mm, u"Year (YYYY)")
        self.c.line(47*mm, 127*mm, 67*mm, 127*mm)
        self.c.drawString(69*mm, 127*mm, u"Month (MM)")
        self.c.line(86*mm, 127*mm, 103*mm, 127*mm)
        self.c.drawString(105*mm, 127*mm, u"Day (DD)")
        self.c.line(118*mm, 127*mm, 136*mm, 127*mm)
        
        # reasons
        self.title_font()
        self.c.drawString(0, 120*mm, u"REASON FOR CHANGE OF GRADE/EXTENION OF \u201CDE\u201D GRADE")
        self.c.drawString(0, 116*mm, u"(NOTE: WHEN ASSIGNING A GRADE OF \u201CFD\u201D AN ACADEMIC DISHONESTY REPORT NEEDS TO BE FILED.)")
        self.c.line(0*mm, 109*mm, main_width, 109*mm)
        self.c.line(0*mm, 101*mm, main_width, 101*mm)
        self.c.line(0*mm, 93*mm, main_width, 93*mm)

        self.label_font()
        self.c.drawString(0, 86*mm, u"Has the student applied to graduate this term?")
        self.c.drawString(0, 80*mm, u"Is this student's academic standing currently RTW or PW?")
        self.check_label(76*mm, 86*mm, 'Yes', fill=0)
        self.check_label(95*mm, 86*mm, 'No', fill=0)
        self.check_label(76*mm, 80*mm, 'Yes', fill=0)
        self.check_label(95*mm, 80*mm, 'No', fill=0)
        
        # approvals
        self.title_font()
        self.c.drawString(0, 72*mm, u"APPROVALS")
        self.label_font()
        self.c.drawString(0, 67*mm, u"Instructor signature")
        self.c.line(25*mm, 67*mm, 108*mm, 67*mm)
        self.c.drawString(110*mm, 67*mm, u"Date")
        self.c.line(117*mm, 67*mm, main_width, 67*mm)
        self.c.drawString(0, 59*mm, u"Instructor name (PLEASE PRINT)")
        self.c.line(44*mm, 59*mm, main_width, 59*mm)
        self.entry_font()
        self.c.drawString(46*mm, 60*mm, user.name())
        self.c.drawString(120*mm, 68*mm, unicode(datetime.date.today().strftime('%B %d, %Y')))

        self.label_font()
        self.c.drawString(0, 51*mm, u"Chair signature")
        self.c.line(20*mm, 51*mm, 108*mm, 51*mm)
        self.c.drawString(110*mm, 51*mm, u"Date")
        self.c.line(117*mm, 51*mm, main_width, 51*mm)
        self.c.drawString(0, 43*mm, u"Chair name (PLEASE PRINT)")
        self.c.line(38*mm, 43*mm, main_width, 43*mm)
        self.entry_font()

        # FOIPOP
        self.title_font()
        self.c.drawString(0, 35*mm, u"FREEDOM OF INFORMATION AND PROTECTION OF PRIVACY")
        self.label_font()
        self.c.drawString(0, 31*mm, u"The information on this form is collected under the authority of the University Act (RSBC 1996 c468 s.27[4a]). This information is needed, and")
        self.c.drawString(0, 27*mm, u"will be used, to update the student's record. If you have any questions about the collection and use of this information contact the Associate Registrar,")
        self.c.drawString(0, 23*mm, u"Information, Records and Registration, 778.782.3198.")

        self.c.drawString(0, 15*mm, u"Accepted (for the Registrar)")
        self.c.line(35*mm, 15*mm, 122*mm, 15*mm)
        self.c.drawString(124*mm, 15*mm, u"Date")
        self.c.line(131*mm, 15*mm, main_width, 15*mm)
        
        # footer
        self.c.setFont("BemboMTPro", 7.5)
        self.c.drawString(43*mm, 6*mm, u"Information, Records and Registration, MBC 3200")
        self.c.drawString(43*mm, 3*mm, u"8888 University Drive, Burnaby BC Canada V5A 1S6")
        self.c.drawString(43*mm, 0*mm, u"students.sfu.ca/records")
        self.c.drawString(122*mm, 6*mm, u"FAX: 778.782.4969")
        self.c.drawString(122*mm, 3*mm, u"urecords@sfu.ca")
        self.c.drawString(154*mm, 6*mm, u"NOVEMBER".translate(self.sc_trans_bembo) + u" " + u"2009".translate(self.digit_trans))
        self.c.drawString(154*mm, 3*mm, u"(produced by CourSys")
        self.c.drawString(154*mm, 0*mm, u"GradeChangeForm)")
        



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
        self._line_entry(86*mm, 208*mm, 'SFU ID', 30*mm, 45*mm, unicode(grad.person.emplid))
        self._line_entry(0*mm, 204*mm, 'Given Name', 22*mm, 58*mm, grad.person.first_name)
        self._line_entry(86*mm, 204*mm, 'email or phone #', 30*mm, 45*mm, unicode(grad.person.email()))

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
        self._line_entry(1*mm, 63*mm, 'Account Code:', 21*mm, 36*mm, entry_text=unicode(grad.program.unit.config.get('card_account', '')))

        # find a sensible person to sign the form
        signers = list(Role.objects.filter(unit=grad.program.unit, role='ADMN').order_by('-id')) + list(Role.objects.filter(unit=grad.program.unit, role='GRPD').order_by('-id'))
        sgn_name = ''
        sgn_userid = ''
        sgn_phone = ''
        for role in signers:
            import PIL
            try:
                sig = Signature.objects.get(user=role.person)
                sig.sig.open()
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                hei = 7*mm
                wid = 1.0*width/height * hei
                sig.sig.open()
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
        self.c.drawString(1*mm, 17.5*mm, u'\u2022 I acknowledge that cards, fobs and keys are the property of SFU and are issued for my own use.')
        self.c.drawString(1*mm, 15*mm, u'\u2022 Items issued will not be passed on to another person and will be returned to this office ONLY')
        self.c.drawString(1*mm, 12.5*mm, u'\u2022 Lost or Found cards/fobs/keys must be reported or returned to Campus Security TC 050 (778-782-3100).')
        self.c.drawString(1*mm, 10*mm, u'\u2022 Policy AD 1-4 applies')
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
        self.c.drawString(0*mm, 251*mm, u"SIMON FRASER UNIVERSITY")
        self.c.drawString(0*mm, 246*mm, u"CARD REQUISITION")
        self.c.drawString(118*mm, 258*mm, u"CARD NO.")
        self.c.rect(118*mm, 250*mm, 47*mm, 6.5*mm, fill=0)
        for i in range(1,6):
            self.c.line(118*mm + i*47.0/6*mm, 250*mm, 118*mm + i*47.0/6*mm, 256.5*mm)
        self.check_label(118*mm, 244*mm, u'New Issue', fill=True)
        self.check_label(118*mm, 238*mm, u'Addendum')
        
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
        self.c.drawString(29*mm, 213*mm, unicode(grad.person.emplid))
        
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
        
        self.check_label(0*mm, 182*mm, u'Deposit', fill=True)
        self.check_label(0*mm, 174.5*mm, u'Service Charge')
        self.check_label(50*mm, 182*mm, u'Deposit')
        self.check_label(50*mm, 174.5*mm, u'Service Charge', fill=True)
        self.check_label(110*mm, 182*mm, u'Individual', fill=True)
        self.check_label(110*mm, 174.5*mm, u'Department')
        
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
        for i,c in enumerate(unicode(acct)):
            x = 32*mm + i*68.0/12*mm
            self.c.drawString(x, 163*mm, c)
        
        self.c.line(0, 157*mm, main_width, 157*mm)
        
        # classification
        self.title_font()
        self.c.drawString(0*mm, 148*mm, 'CLASSIFICATION')
        self.check_label(13*mm, 140*mm, u'Staff')
        self.check_label(51*mm, 140*mm, u'Faculty')
        self.check_label(89*mm, 140*mm, u'RA')
        self.check_label(128*mm, 140*mm, u'Visitor')
        self.check_label(13*mm, 133*mm, u'Undergrad')
        self.check_label(51*mm, 133*mm, u'Graduate', fill=True)
        self.check_label(89*mm, 133*mm, u'_____________')

        self.c.drawString(0*mm, 123*mm, 'EMPLOYEE GROUP')
        self.check_label(13*mm, 115*mm, u'CUPE')
        self.check_label(51*mm, 115*mm, u'APSA')
        self.check_label(89*mm, 115*mm, u'Student', fill=True)
        self.check_label(128*mm, 115*mm, u'Polyparty')
        self.check_label(13*mm, 108*mm, u'Contract')
        self.check_label(51*mm, 108*mm, u'TSSU')
        self.check_label(89*mm, 108*mm, u'SFUFA')
        self.check_label(128*mm, 108*mm, u'____________')

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
        signers = list(Role.objects.filter(unit=grad.program.unit, role='ADMN').order_by('-id')) + list(Role.objects.filter(unit=grad.program.unit, role='GRPD').order_by('-id'))
        for role in signers:
            import PIL
            try:
                sig = Signature.objects.get(user=role.person)
                sig.sig.open()
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                hei = 7*mm
                wid = 1.0*width/height * hei
                sig.sig.open()
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
        self.c.drawString(0*mm, 35*mm, u"\u2022 THIS CARD IS FOR MY OWN USE.")
        self.c.drawString(0*mm, 30*mm, u"\u2022 IT REMAINS THE POPERTY OF SFU.")
        self.c.drawString(0*mm, 25*mm, u"\u2022 IT WILL NOT BE PASSED ON TO ANOTHER PERSON")
        self.c.drawString(0*mm, 20*mm, u"\u2022 IT WILL BE RETURNED TO THIS OFFICE ONLY, WHEN NO LONGER OF USE TO MYSELF.")
        
        self.c.setDash(1)
        self.c.line(0, 5*mm, 62*mm, 5*mm)
        self.c.line(69*mm, 5*mm, 136*mm, 5*mm)
        self.c.drawString(0*mm, 0*mm, u"SIGNATURE")
        self.c.drawString(69*mm, 0*mm, u"DATE")

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
        self.label_blank(0*mm, base_y - 3*self.ENTRY_HEIGHT, 'Student Number', unicode(grad.person.emplid))

        self.label_blank(0*mm, base_y - 5*self.ENTRY_HEIGHT, 'Account Type', 'Graduate Student')
        self.label_blank(0*mm, base_y - 6*self.ENTRY_HEIGHT, 'Department', grad.program.unit.informal_name())

        self.label_blank(0*mm, base_y - 7*self.ENTRY_HEIGHT, 'Groups', 'cs_grads group')
        self.label_blank(0*mm, base_y - 8*self.ENTRY_HEIGHT, 'Research Lab(s)', '')
        self.label_blank(0*mm, base_y - 9*self.ENTRY_HEIGHT, 'Home Directory', '/cs/grad1,2,3')
        self.label_blank(0*mm, base_y - 10*self.ENTRY_HEIGHT, 'Platforms', 'Unix & Windows')

        # find a sensible person to sign the form
        signers = list(Role.objects.filter(unit=grad.program.unit, role='GRAD').order_by('-id')) \
                  + list(Role.objects.filter(unit=grad.program.unit, role='ADMN').order_by('-id')) \
                  + list(Role.objects.filter(unit=grad.program.unit, role='GRPD').order_by('-id'))
        for role in signers:
            import PIL
            try:
                sig = Signature.objects.get(user=role.person)
                sig.sig.open()
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                hei = 10*mm
                wid = 1.0*width/height * hei
                sig.sig.open()
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









    
