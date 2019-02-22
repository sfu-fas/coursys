from django.utils.html import mark_safe, conditional_escape
from django import template
from grad.models import GradStudent, Supervisor
import json
register = template.Library()

SIMS_SOURCE = 'sims_source'

class SIMSCheckNode(template.Node):
    def __init__(self, obj):
        self.obj = template.Variable(obj)
        #self.user = template.Variable('user')

    def render(self, context):
        obj = self.obj.resolve(context)
        #user = self.user.resolve(context)
        debug = False
        #if user and user.username == 'ggbaker':
        #    debug = True

        if isinstance(obj, GradStudent):
            gs = obj
        else:
            gs = obj.student

        # if gs.program.unit.slug == 'cmpt' and not debug:
        #    return ''

        if hasattr(obj, 'config') and SIMS_SOURCE in obj.config and obj.config[SIMS_SOURCE]:
            tag = '<i class="fa fa-check sims_check_yes" title="Found in SIMS"></i>'
            if debug:
                tag += ' <span style="font-size: 65%%;">%s</span>' % \
                       (conditional_escape(json.dumps(obj.config[SIMS_SOURCE])))
        elif isinstance(obj, Supervisor) and obj.supervisor_type == 'POT':
            # these aren't in SIMS ever so don't complain
            tag = ''
        else:
            tag = '<i class="fa fa-question sims_check_no" title="Not found in SIMS import"></i>'

        return mark_safe(tag)


@register.tag('sims_check')
def do_sims_check(parser, token):
    tag_name, obj = token.split_contents()
    return SIMSCheckNode(obj)

