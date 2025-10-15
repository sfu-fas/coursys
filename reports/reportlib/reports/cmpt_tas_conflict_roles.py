from ..report import Report
from ..table import Table
from coredata.models import Semester, Unit, Member
from ta.models import TACourse as ta_courses
from tacontracts.models import TACourse as tacontracts_courses

class CMPTTAConflictRolesReport(Report):
    title = "CMPT TAs has conflict memberships for the Current Semester"
    description = "A report of all CMPT TAs has memberships (student role) in the current semester"

    def run(self):        
        semesters =[] 
        semesters.append(Semester.current())
        # Include next term as well
        semesters.append(Semester.current().next_semester())

        units = Unit.objects.filter(label__in=['CMPT'])
        
        # - /ta
        tas = ta_courses.objects.filter(contract__posting__semester__in=semesters,                                        
                                        contract__posting__unit__in=units).order_by("course__name", "contract__application__person__emplid")
        # - /tacontracts
        tacontracts = tacontracts_courses.objects.filter(contract__category__hiring_semester__semester__in=semesters, 
                                                         contract__category__hiring_semester__unit__in=units).order_by("course__name")

        results = Table()
        results.append_column('Semester')
        results.append_column('Name of TA')
        results.append_column('SFU ID')
        results.append_column('User ID')
        results.append_column('TA Contract Status')
        results.append_column('TA Course Number')
        results.append_column('Conflict Course Number (Enrolled)')
        results.append_column('Course Name')        
        results.append_column('Instructor UserID(s)')

        for ta in tas:
            m = Member.objects.filter(person=ta.contract.application.person, offering=ta.course, role='STUD').first()
            if m:
                results.append_row([ta.contract.posting.semester, ta.contract.application.person.name_with_pref(), ta.contract.application.person.emplid, ta.contract.application.person.userid, ta.contract.status, ta.course.name(), m.offering.name(), ta.course.title, "; ".join(p.userid for p in ta.course.instructors())])

            # check combined courses as well
            co = ta.course
            joint_with = co.config.get('joint_with')
            if joint_with:
                # array of course offering combos that are joint, making sure to account for multiples
                unique_joint_offerings = set()
                if len(joint_with) > 1:
                    for slug in joint_with:
                        unique_joint_offerings.add(tuple(sorted([co.slug, slug])))
                else:
                    unique_joint_offerings.add(tuple(sorted([co.slug, joint_with[0]])))
                unique_joint_offerings = [list(offering_combo) for offering_combo in unique_joint_offerings]
                for o in unique_joint_offerings:
                    try:
                        m1 = Member.objects.filter(person=ta.contract.application.person, offering__slug=o[0], role='STUD').first()
                        m2 = Member.objects.filter(person=ta.contract.application.person, offering__slug=o[1], role='STUD').first()
                        if m1:
                            results.append_row([ta.contract.posting.semester, ta.contract.application.person.name_with_pref(), ta.contract.application.person.emplid, ta.contract.application.person.userid, ta.contract.status, ta.course.name(), m1.offering.name()+'*', ta.course.title, "; ".join(p.userid for p in ta.course.instructors())])
                        if m2:
                            results.append_row([ta.contract.posting.semester, ta.contract.application.person.name_with_pref(), ta.contract.application.person.emplid, ta.contract.application.person.userid, ta.contract.status, ta.course.name(),  m2.offering.name()+'*', ta.course.title, "; ".join(p.userid for p in ta.course.instructors())])

                    except Member.DoesNotExist:
                        continue    
                    


        for ta in tacontracts:
            m = Member.objects.filter(person=ta.contract.person, offering=ta.course, role='STUD').first()
            # check combined courses as well
            # TBD
            if m:
                results.append_row([ta.contract.posting.semester, ta.contract.person.name_with_pref(), ta.contract.person.emplid, ta.contract.person.userid, ta.contract.status, ta.course.name(), m.offering.name(), ta.course.title, "; ".join(p.userid for p in ta.course.instructors())])
            # check combined courses as well
            co = ta.course
            joint_with = co.config.get('joint_with')
            if joint_with:
                # array of course offering combos that are joint, making sure to account for multiples
                unique_joint_offerings = set()
                if len(joint_with) > 1:
                    for slug in joint_with:
                        unique_joint_offerings.add(tuple(sorted([co.slug, slug])))
                else:
                    unique_joint_offerings.add(tuple(sorted([co.slug, joint_with[0]])))
                unique_joint_offerings = [list(offering_combo) for offering_combo in unique_joint_offerings]
                for o in unique_joint_offerings:
                    try:
                        m1 = Member.objects.filter(person=ta.contract.person, offering__slug=o[0], role='STUD').first()
                        m2 = Member.objects.filter(person=ta.contract.person, offering__slug=o[1], role='STUD').first()
                        if m1:
                            results.append_row([ta.contract.posting.semester, ta.contract.person.name_with_pref(), ta.contract.person.emplid, ta.contract.person.userid, ta.contract.status, ta.course.name(), m1.offering.name()+'*', ta.course.title, "; ".join(p.userid for p in ta.course.instructors())])
                        if m2:
                            results.append_row([ta.contract.posting.semester, ta.contract.person.name_with_pref(), ta.contract.person.emplid, ta.contract.person.userid, ta.contract.status, ta.course.name(), m2.offering.name()+'*', ta.course.title, "; ".join(p.userid for p in ta.course.instructors())])

                    except Member.DoesNotExist:
                        continue

        self.artifacts.append(results)