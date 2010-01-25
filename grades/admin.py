from courses.grades.models import *
from django.contrib import admin

admin.site.register(Activity)
admin.site.register(NumericActivity)
admin.site.register(LetterActivity)
admin.site.register(CalNumericActivity)
admin.site.register(CalLetterActivity)
admin.site.register(NumericGrade)
admin.site.register(LetterGrade)

