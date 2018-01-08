'''
Created on Jan 27, 2012

@author: jord
'''
from django.forms.forms import BoundField, conditional_escape
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

def html_output_alt(self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row,
        extra_css_class_attr = "manual_css_classes"):
    "Helper function for outputting HTML. Used by as_table(), as_ul(), as_p()."
    top_errors = self.non_field_errors() # Errors that should be displayed above all fields.
    output, hidden_fields = [], []

    for name, field in list(self.fields.items()):
        html_class_attr = ''
        bf = BoundField(self, field, name)
        bf_errors = self.error_class([conditional_escape(error) for error in bf.errors]) # Escape and cache in local variable.
        if bf.is_hidden:
            if bf_errors:
                top_errors.extend(['(Hidden field %s) extra_css_class_attr%s' % (name, force_unicode(e)) for e in bf_errors])
            hidden_fields.append(str(bf))
        else:
            # Create a 'class="..."' atribute if the row should have any
            # CSS classes applied.
            css_classes = bf.css_classes(getattr(field, extra_css_class_attr, None))
            if css_classes:
                html_class_attr = ' class="%s"' % css_classes

            if errors_on_separate_row and bf_errors:
                output.append(error_row % force_unicode(bf_errors))

            if bf.label:
                label = conditional_escape(force_unicode(bf.label))
                # Only add the suffix if the label does not end in
                # punctuation.
                if self.label_suffix:
                    if label[-1] not in ':?.!':
                        label += self.label_suffix
                label = bf.label_tag(label) or ''
            else:
                label = ''

            if field.help_text:
                help_text = help_text_html % force_unicode(field.help_text)
            else:
                help_text = ''

            output.append(normal_row % {
                'errors': force_unicode(bf_errors),
                'label': force_unicode(label),
                'field': str(bf),
                'help_text': help_text,
                'html_class_attr': html_class_attr
            })

    #if top_errors:
    #    output.insert(0, error_row % force_unicode(top_errors))

    if hidden_fields: # Insert any hidden fields in the last row.
        str_hidden = ''.join(hidden_fields)
        if output:
            last_row = output[-1]
            # Chop off the trailing row_ender (e.g. '</td></tr>') and
            # insert the hidden fields.
            if not last_row.endswith(row_ender):
                # This can happen in the as_p() case (and possibly others
                # that users write): if there are only top errors, we may
                # not be able to conscript the last row for our purposes,
                # so insert a new, empty row.
                last_row = (normal_row % {'errors': '', 'label': '',
                                          'field': '', 'help_text':'',
                                          'html_class_attr': html_class_attr})
                output.append(last_row)
            output[-1] = last_row[:-len(row_ender)] + str_hidden + row_ender
        else:
            # If there aren't any rows in the output, just append the
            # hidden fields.
            output.append(str_hidden)
    return mark_safe('\n'.join(output))
# this function could be moved into some utility module
def table_row__Form(klass):
    #assert(issubclass(klass, forms.BaseForm))
    #assert hasattr(klass, '_html_output')
    def as_table_row(self):
        "Returns this form rendered as HTML <td>s -- excluding the <tr></tr>."
        return html_output_alt(self,
            normal_row = '<td%(html_class_attr)s>%(field)s%(errors)s%(help_text)s</td>',
            error_row = '',
            row_ender = '</td>',
            help_text_html = '<br /><span class="helptext">%s</span>',
            errors_on_separate_row = False)
    klass.as_table_row = as_table_row
    return klass

def update_and_return(d, *others):
    for other in others:
        d.update(other)
    return d
