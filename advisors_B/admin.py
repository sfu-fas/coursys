from courses.advisors_B.models import Note
from django.contrib import admin

class NoteAdmin(admin.ModelAdmin):
    fieldsets = [
        ('CreateInfo', {'fields':['CreateDate','Student', 'Author']}),

        ('Note Detail', {'fields':['Hidden','Content']})
    ]

admin.site.register(Note, NoteAdmin)
