from django import template
register = template.Library()

from settings import MEDIA_URL
from django.template import Context, Template
from django.utils.safestring import mark_safe

@register.filter(name='stu_grade')
def stu_grade(Activity,Person):
    return Activity.display_grade_student(Person)
ACTIVITY_FIELD_TEMPLATE = Template("""<li>
                    {{ field.label_tag }}
                    <div class="inputfield">
                        {{ field }} {% if field.help_text %}<span class="helptext">({{field.help_text}})</span>{% endif %}
                        {% if field.errors %}<img src="{{MEDIA_URL}}/icons/error.png" alt="error"/> {{field.errors}}{% endif %}
                    </div>
                </li>
""")

@register.filter
def activity_field(field):
    """
    Convert the field to HTML
    """
    c = Context({"field":field})
    return mark_safe(ACTIVITY_FIELD_TEMPLATE.render(c))

