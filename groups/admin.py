from courses.groups.models import *
from django.contrib import admin


class GMemberInline(admin.TabularInline):
    model = GroupMember
    fk_name = "group"
    #extra = 2

class GAdmin(admin.ModelAdmin):
    list_display = ('name', 'courseoffering')
    search_fields = ('name', 'courseoffering')
    #list_filter = ('name', 'courseoffering')
    inlines = [GMemberInline]

class GMAdmin(admin.ModelAdmin):
    list_display = ('activity', 'group', 'student')
    search_fields = ('activity', 'group', 'student')
    #list_filter = ('activity', 'group')
    


admin.site.register(Group, GAdmin)
admin.site.register(GroupMember, GMAdmin)
