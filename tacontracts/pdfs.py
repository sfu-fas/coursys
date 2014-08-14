# Python
import datetime

# Third-Party
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Flowable, Paragraph, Spacer, Frame,\
                               KeepTogether, NextPageTemplate, PageBreak, \
                               Image, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import textobject, canvas
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont  
from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
# Local
from dashboard.letters import PAPER_SIZE, black, white, media_path, logofile
from dashboard.models import Signature

class TAPdf(object):
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
        Create TA Appointment Form(s) in the file object 
        (which could be a Django HttpResponse).
        """
        self.c = canvas.Canvas(outfile, pagesize=letter)
    
    def _draw_box(self, x, y, width, label='', label_size=LABEL_SIZE, 
                  content='', content_size=CONTENT_SIZE, right=False):
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
        # origin = lower-left of the main box
        self.c.translate(0.625*inch, 1.25*inch) 
        main_width = 7.25*inch

        # header
        self.c.drawImage(logofile, x=main_width/2 - 0.5*inch, y=227*mm,
                         width=1*inch, height=0.5*inch)
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(main_width/2 + 1*inch, 233*mm,
                          "SIMON FRASER UNIVERSITY")
        self.c.drawRightString(main_width/2 - 1*inch, 233*mm,
                               "Teaching Assistant Appointment Form")
        
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
        self._draw_box(0, 8.625*inch, 43*mm, label="SFU ID #", 
                content=unicode(contract.person.emplid))
        self._draw_box(0, 210*mm, 43*mm, label="CANADA SOCIAL INSURANCE NO.", 
                       content=unicode(contract.sin))
        self._draw_box(46*mm, 210*mm, 74*mm, label="LAST OR FAMILY NAME", 
                       content=unicode(contract.person.last_name))
        self._draw_box(125*mm, 210*mm, 50*mm, label="FIRST NAME",
                       content=unicode(contract.person.first_name))
        self._draw_box(15*mm, 202*mm, 160*mm, 
                       content="c/o " + unicode(contract.category.account.unit.name)) 
        # ADDRESS
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(2, 206*mm, "HOME")
        self.c.drawString(2, 203*mm, "ADDRESS")
        
        # appointment basic info
        self.c.drawString(2, 194*mm, "DEPARTMENT")
        dept = unicode(contract.category.account.unit.informal_name())
        if contract.category.account.unit.deptid():
            dept += " (%s)" % (contract.category.account.unit.deptid())
        self._draw_box(20*mm, 193*mm, 78*mm, content=dept) # DEPARTMENT
        self._draw_box(102*mm, 193*mm, 32*mm, label="APPOINTMENT START DATE", 
                       content=unicode(contract.pay_start))
        self._draw_box(139*mm, 193*mm, 32*mm, label="APPOINTMENT END DATE", 
                       content=unicode(contract.pay_end))
        
        # initial appointment boxes
        
        initial_appointment_fill = 0
        if contract.appointment == "INIT":
            initial_appointment_fill = 1
        reappointment_fill = 0
        if contract.appointment == "REAP":
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
        self._draw_box(60*mm, 176*mm, 37*mm, label="POSITION NUMBER", 
                       content=unicode(contract.category.account.position_number))
        self._draw_box(102*mm, 176*mm, 32*mm, label="PAYROLL START DATE", 
                       content=unicode(contract.pay_start))
        self._draw_box(139*mm, 176*mm, 32*mm, label="PAYROLL END DATE",
                       content=unicode(contract.pay_end))
        
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
        courses = contract.course.filter(bu__gt=0)
        total_bu = 0
        bu = 0
        for i, crs in zip(range(5), list(courses)+[None]*5):
            h = 162*mm - i*6*mm # bottom of this row
            self.c.rect(24*mm, h, 27*mm, 6*mm)
            self.c.rect(51*mm, h, 74*mm, 6*mm)
            self.c.rect(125*mm, h, 23*mm, 6*mm)
            
            self.c.setFont("Helvetica", self.CONTENT_SIZE-2)
            if crs:
                self.c.drawString(25*mm, h + 1*mm, crs.course.subject + ' ' + \
                               crs.course.number + ' ' + crs.course.section[:2])
                description = "Office/Marking"
                if crs.labtut:
                    description = "Office/Marking/Lab"
                self.c.drawString(52*mm, h + 1*mm, description)
                self.c.drawRightString(147*mm, h + 1*mm, "%.2f" % (crs.total_bu))
                bu += crs.bu
                total_bu += crs.total_bu
        
        self.c.rect(125*mm, 132*mm, 23*mm, 6*mm)
        self.c.drawRightString(147*mm, 133*mm, "%.2f" % (total_bu))
        
        self._draw_box(153*mm, 155*mm, 22*mm, label="APPT. CATEGORY", 
                       content=contract.category.code)
            
        # salary/scholarship
        total_pay = contract.total_pay
        biweek_pay = contract.biweekly_pay
        total_schol = contract.scholarship_pay
        biweek_schol = contract.biweekly_scholarship
        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(8*mm, 123*mm, "SALARY")
        self.c.drawString(1*mm, 112*mm, "SCHOLARSHIP")
        self.c.setFont("Helvetica", self.CONTENT_SIZE)
        self.c.drawString(29*mm, 122*mm + self.CONTENT_UP, "$")
        self.c.drawString(75*mm, 122*mm + self.CONTENT_UP, "$")
        self.c.drawString(29*mm, 111*mm + self.CONTENT_UP, "$")
        self.c.drawString(75*mm, 111*mm + self.CONTENT_UP, "$")
        self._draw_box(33*mm, 122*mm, 32*mm, label="BIWEEKLY RATE", right=True,
                       content="%.2f" % (biweek_pay))
        self._draw_box(79*mm, 122*mm, 32*mm, label="SEMESTER RATE", right=True,
                       content="%.2f" % (total_pay))
        self._draw_box(33*mm, 111*mm, 32*mm, label="BIWEEKLY RATE", right=True,
                       content="%.2f" % (biweek_schol))
        self._draw_box(79*mm, 111*mm, 32*mm, label="SEMESTER RATE", right=True,
                       content="%.2f" % (total_schol))

        self._draw_box(139*mm, 122*mm, 32*mm, label="EFF. DATE FOR RATE CHANGES",
                       content=unicode(contract.pay_start))
        self.c.setFont("Helvetica", 5)
        self.c.drawString(114*mm, 125*mm, "THESE RATES INCLUDE 4%")
        self.c.drawString(114*mm, 123*mm, "VACATION PAY")
        
        # remarks
        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(1*mm, 103*mm, "REMARKS")
        f = Frame(3*mm, 82*mm, main_width - 6*mm, 22*mm) #, showBoundary=1 
        notes = []
        notes.append(Paragraph(contract.comments, style=self.NOTE_STYLE))
        f.addFromList(notes, self.c)

        # instructions
        self.c.setFont("Helvetica-Bold", self.LABEL_SIZE)
        self.c.drawString(5*mm, 78*mm, "INSTRUCTIONS TO THE APPOINTEE")
        self.c.setLineWidth(1)
        self.c.line(0, 76*mm+self.BOX_HEIGHT, main_width, 76*mm+self.BOX_HEIGHT)
        self.c.setFont("Helvetica", self.LABEL_SIZE)
        self.c.drawString(100*mm, 78*mm, "DEADLINE FOR ACCEPTANCE")
        self._draw_box(139*mm, 76*mm, 32*mm, label="", 
                       content=unicode(contract.deadline_for_acceptance))
        

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
        fill = 1 if contract.conditional_appointment else 0
        self.c.rect(59*mm, 19*mm, 3*mm, 3*mm, fill=fill)
        self.c.drawString(79*mm, 20*mm, "Appointment in TSSU Bargaining unit")
        fill = 1 if contract.tssu_appointment else 0
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
        self.c.drawString(1*mm, -18*mm, "Updated July 2014 (produced by CourSys TAForm)")

        self.c.showPage()
    
    def save(self):
        self.c.save()

def ta_pdf(contract, outfile):
    """
    Generate TA Appointment Form for this TAContract.
    """
    doc = TAPdf(outfile)
    doc.draw_form(contract)
    doc.save()
