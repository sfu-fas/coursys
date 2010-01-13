from advisors_B.models import *
from django.contrib import admin

class NoteAdmin(admin.ModelAdmin):
    fieldsets = [
        ('CreateInfo', {'fields':['create_date','student', 'author']}),

        ('Note Detail', {'fields':['content','hidden','file']})
    ]
    
admin.site.register(Note,NoteAdmin)
