from cortez_import import TAImport
from coredata.models import CourseOffering, Member

class TAFetcher(TAImport):
    def get_semester_tas(self, strm):
        self.db.execute("SELECT crs.Course_Number, c.Section, "
                        "o.bu, "
                        "i.studNum "
                        "FROM TAOffering o, tasearch.dbo.tainfo i, Offerings c, Courses crs, Resource_Semesters s "
                        "WHERE o.TA_ID=i.appId AND c.Offering_ID=o.Offering_ID AND c.Course_ID=crs.Course_ID AND c.Semester_ID=s.Semester_ID "
                        "AND i.status='accepted' and Semester_Description=%s", (strm,)) # and i.appYear>'109' 
        for subjnum, sec, bu, emplid in self.db:
            print (subjnum, sec, bu, emplid)
            subject, number = subjnum.split()
            o = CourseOffering.objects.filter(subject=subject, number__startswith=number, semester__name=strm, section__startswith=sec)
            m = Member.objects.filter(role='TA', offering=o, person__emplid=emplid)
            print m


TAFetcher().get_semester_tas('1124')
    