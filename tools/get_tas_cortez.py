import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from coredata.cortez_import import TAImport
from coredata.models import CourseOffering, Member

lab_bu = ['2.17', '4.17', '6.17', '4.67', '6.67', '4.92', '3.42', '1.17', '3.67', '3.17', '3.42', '3.92', '4.42', '2.67', '2.92', ]

class TAFetcher(TAImport):
    def get_semester_tas(self, strm):
        self.db.execute("SELECT crs.Course_Number, c.Section, "
                        "o.bu, "
                        "i.studNum "
                        "FROM TAOffering o, tasearch.dbo.tainfo i, Offerings c, Courses crs, Resource_Semesters s "
                        "WHERE o.TA_ID=i.appId AND c.Offering_ID=o.Offering_ID AND c.Course_ID=crs.Course_ID AND c.Semester_ID=s.Semester_ID "
                        "AND i.status='accepted' and Semester_Description=%s", (strm,)) # and i.appYear>'109' 
        for subjnum, sec, bu, emplid in self.db:
            print((subjnum, sec, bu, emplid, str(bu) in lab_bu))
            subject, number = subjnum.split()
            o = CourseOffering.objects.get(subject=subject, number__startswith=number, semester__name=strm, section__startswith=sec)
            try:
                m = Member.objects.get(role='TA', offering=o, person__emplid=emplid)
            except Member.DoesNotExist:
                continue

            m.set_bu(float(bu))
            m.save()
            if str(bu) in lab_bu:
                o.set_labtas(True)
                o.save()

            #print m, m.config
            #print o, o.config


TAFetcher().get_semester_tas('1127')
    
