from advisors_B.models import Note
from advisors_B import Person
from django.contrib import admin

class NoteAdmin(admin.ModelAdmin):
    fieldsets = [
        ('CreateInfo', {'fields':['CreateDate','Student', 'Author']}),

        ('Note Detail', {'fields':['Content','Hidden']})
    ]
    
admin.site.register(Note,NoteAdmin)
