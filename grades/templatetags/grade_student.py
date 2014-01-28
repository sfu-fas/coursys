from django import template
register = template.Library()

from django.conf import settings
STATIC_URL = settings.STATIC_URL
from django.template import Context, Template
from django.utils.safestring import mark_safe
from django.utils.html import escape 

@register.filter(name='stu_grade')
def stu_grade(Activity,Person):
    return Activity.display_grade_student(Person)
ACTIVITY_FIELD_TEMPLATE = Template('''<li>
                    {{ field.label_tag }}
                    <div class="inputfield" id="div_id_{{field.name}}">
                        {{ field }}
                        {% if field.errors %}<span class="errortext"><img src="''' + STATIC_URL + '''icons/error.png" alt="error"/> {{field.errors.0}}</span>{% endif %}
                        {% if field.help_text %}<div class="helptext">({{field.help_text}})</div>{% endif %}
                    </div>
                    </li>''')

#@register.filter
#def activity_field(field):
#    """
#    Convert the field to HTML
#    """
#    c = Context({"field":field})
#    return mark_safe(ACTIVITY_FIELD_TEMPLATE.render(c))

@register.tag(name="select_grade")
def do_select_grade(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, dictionary, aslug, userid = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires a three arguments: dictionary, activity slug, userid" % token.contents.split()[0]


    return SelectGradeNode(dictionary, aslug, userid)

class SelectGradeNode(template.Node):
    def __init__(self, dictionary, aslug, userid):
        self.dictionary = template.Variable(dictionary)
        self.aslug = template.Variable(aslug)
        self.userid = template.Variable(userid)

    def render(self, context):
        try:
            dictionary = self.dictionary.resolve(context)
            aslug = self.aslug.resolve(context)
            userid = self.userid.resolve(context)
        except template.VariableDoesNotExist:
            return "?"

        grades = dictionary[aslug]
        if userid not in grades:
            return ''

        grade = grades[userid]
        gtext = escape(grade.display_staff_short())

        stext = ''
        if grade.flag not in ['GRAD', 'NOGR', 'CALC']:
            stext = '(' + grade.get_flag_display() + ')'


        if grade.comment:
            ctext = escape(grade.comment)
            stext = '(' + grade.get_flag_display() + ')'
        else:
            ctext = ''
        
        if ctext and stext:
            return mark_safe(gtext + '<span class="more"><span title="' + ctext + '"><img src="/media/icons/information.png" alt="[I]" /></span><br/>' + stext + '</span>')
        elif stext:
            return mark_safe(gtext + '<span class="more"><br/>' + stext + '</span>')
        else:
            return mark_safe(gtext)


