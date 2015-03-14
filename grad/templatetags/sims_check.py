from django import template
from django.utils.html import mark_safe
from django import template
from grad.models import Supervisor

# who can see these checks?
ALLOWED_USERIDS = {'ggbaker',}

register = template.Library()

class SIMSCheckNode(template.Node):
    def __init__(self, obj):
        self.obj = template.Variable(obj)
        self.grad = template.Variable('grad')
        self.user = template.Variable('user')
    def render(self, context):
        gs = self.grad.resolve(context)
        user = self.user.resolve(context)

        # don't reveal these widely yet
        if not user or user.username not in ALLOWED_USERIDS:
            return ''
        #if gs.program.unit.slug == 'cmpt':
        #    return ''

        obj = self.obj.resolve(context)
        if hasattr(obj, 'config') and 'imported_from' in obj.config and obj.config['imported_from']:
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

