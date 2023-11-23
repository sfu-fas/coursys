from django.shortcuts import render
from django.utils.html import conditional_escape

from log.forms import RequestLogForm, EVENT_FORM_TYPES
from log.models import LogEntry, EVENT_LOG_TYPES, RequestLog
from courselib.auth import requires_global_role
from courselib.search import get_query

from django_datatables_view.base_datatable_view import BaseDatatableView


@requires_global_role("SYSA")
def index(request):
    if 'q' in request.GET:
        q = request.GET.get('q')
        query = get_query(q, ['userid', 'description', 'comment'])
        logs = LogEntry.objects.order_by('-datetime').filter(query)[:200]
    else:
        q = ''
        keywords = ""
        logs = None
        reg = ""

    return render(request, "log/index.html",  {"logs": logs, 'q': q})


@requires_global_role("SYSA")
def log_explore(request):
    """
    Interactive EventLogEntry browser
    """
    log_type = request.GET.get('type', 'request')
    if 'tabledata' in request.GET:
        # table data
        if log_type == 'request':
            return _log_data(request)
        else:
            raise NotImplemented

    # actually displaying the page at this point
    ModelClass = EVENT_LOG_TYPES[log_type]
    FormClass = EVENT_FORM_TYPES[log_type]
    form = FormClass()
    context = {
        'log_type': log_type,
        'form': form,
        'display_columns': ModelClass.display_columns,
        'table_column_config': ModelClass.table_column_config,
    }
    return render(request, 'log/log_explore.html', context)


class OfferingDataJson(BaseDatatableView):
    model = RequestLog
    max_display_length = 500
    columns = RequestLog.display_columns
    #order_columns = [COLUMN_ORDERING[col] for col in columns]

    def render_column(self, logentry, column):
        if column == 'FOO':
            col = logentry.path
        else:
            col = getattr(logentry, column)

        return conditional_escape(col)

    def ordering(self, qs):
        return super(OfferingDataJson, self).ordering(qs)

    def filter_queryset(self, qs):
        # use request parameters to filter queryset
        GET = self.request.GET
        print(GET)
        methods = GET.get('method[]', None)
        if methods:
            print(methods)
            qs = qs
        return qs

_log_data = OfferingDataJson.as_view()
