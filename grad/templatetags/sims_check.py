from django import template
from django.utils.html import mark_safe
from django import template
from grad.models import GradStudent, Supervisor

register = template.Library()

class SIMSCheckNode(template.Node):
    def __init__(self, obj):
        self.obj = template.Variable(obj)

    def render(self, context):
        obj = self.obj.resolve(context)
        if isinstance(obj, GradStudent):
            gs = obj
        else:
            gs = obj.student

        if gs.program.unit.slug != 'ensc':
            return ''

        if hasattr(obj, 'config') and 'sims_source' in obj.config and obj.config['sims_source']:
            return mark_safe('<i class="fa fa-check sims_check_yes" title="Found in SIMS"></i>')
        elif isinstance(obj, Supervisor) and obj.supervisor_type == 'POT':
            # these aren't in SIMS ever so don't complain
            return ''
        else:
            return mark_safe('<i class="fa fa-question sims_check_no" title="Not found in SIMS import"></i>')


@register.tag('sims_check')
def do_sims_check(parser, token):
    tag_name, obj = token.split_contents()
    return SIMSCheckNode(obj)

