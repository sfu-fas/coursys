from django import template
register = template.Library()

@register.filter(name='stu_grade')
def stu_grade(Activity,Person):
    return Activity.display_grade_student(Person)
