from django import template
register = template.Library()

from settings import MEDIA_URL
from django.template import Context, Template
from django.utils.safestring import mark_safe

@register.filter(name='stu_grade')
def stu_grade(Activity,Person):
    return Activity.display_grade_student(Person)
ACTIVITY_FIELD_TEMPLATE = Template('''<li>
                    {{ field.label_tag }}
                    <div class="inputfield">
                        {{ field }}
                        {% if field.errors %}<span class="errortext"><img src="''' + MEDIA_URL + '''icons/error.png" alt="error"/> {{field.errors.0}}</span>{% endif %}
                        {% if field.help_text %}<div class="helptext">({{field.help_text}})</div>{% endif %}
                    </div>
                    </li>''')

@register.filter
def activity_field(field):
    """
    Convert the field to HTML
    """
    c = Context({"field":field})
    return mark_safe(ACTIVITY_FIELD_TEMPLATE.render(c))

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
            return u'\u2014'

        return grades[userid].display_staff()


