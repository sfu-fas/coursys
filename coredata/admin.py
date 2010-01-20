from coredata.models import *

from django.contrib import admin

class SemesterWeekInline(admin.TabularInline):
    model = SemesterWeek
    fk_name = "semester"
    extra = 2
class SemesterAdmin(admin.ModelAdmin):
    inlines = [SemesterWeekInline]

class MemberInline(admin.TabularInline):
    model = Member
    fk_name = "person"
    extra = 2
class PersonAdmin(admin.ModelAdmin):
    inlines = [MemberInline]
    list_display = ('last_name', 'pref_first_name', 'userid')
    search_fields = ('last_name', 'pref_first_name', 'first_name', 'userid')

class MemberAdmin(admin.ModelAdmin):
    list_display = ('person', 'offering')
    list_filter = ('role',)

class MemberOInline(admin.TabularInline):
    model = Member
    extra = 2
class OfferingAdmin(admin.ModelAdmin):
    list_display = ('subject', 'number', 'section', 'semester', 'class_nbr', 'slug')
    list_filter = ('semester', 'subject', 'number')
    search_fields = ('subject', 'number', 'section', 'class_nbr')
    inlines = [MemberOInline]


admin.site.register(CourseOffering, OfferingAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Semester, SemesterAdmin)
admin.site.register(MeetingTime)
admin.site.register(Member, MemberAdmin)
admin.site.register(Role)

