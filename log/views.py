import datetime

from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from log.forms import RequestLogForm, EVENT_FORM_TYPES
from log.models import LogEntry, EVENT_LOG_TYPES, RequestLog, CeleryTaskLog
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
    if log_type not in EVENT_DATA_VIEWS:
        raise Http404()

    if 'tabledata' in request.GET:
        # table data
        return _log_data(log_type, request)

    # actually displaying the page at this point
    ModelClass = EVENT_LOG_TYPES[log_type]
    FormClass = EVENT_FORM_TYPES[log_type]
    form = FormClass()
    context = {
        'log_types': list(EVENT_LOG_TYPES.keys()),
        'log_type': log_type,
        'form': form,
        'display_columns': ModelClass.display_columns,
        'table_column_config': ModelClass.table_column_config,
    }
    return render(request, 'log/log_explore.html', context)


class RequestLogDataJson(BaseDatatableView):
    model = RequestLog
    max_display_length = 500
    columns = RequestLog.display_columns

    def render_column(self, logentry, column):
        if column == 'time':
            txt = logentry.time
            url = reverse('sysadmin:log_view', kwargs={'log_type': 'request', 'log_id': str(logentry.id)})
            col = mark_safe(f'<a href="{ conditional_escape(url) }">{ conditional_escape(txt) }</a>')
        elif column == 'status_code':
            col = logentry.data.get('status_code', None)
        elif column == 'path':
            col = conditional_escape(logentry.path)
            qs = logentry.data.get('query_string', '')
            if qs:
                col += f'?<span title="{ conditional_escape(qs) }">...</span>'
            col = mark_safe(col)
        else:
            col = getattr(logentry, column)

        if col is None:
            return '&mdash;'
        else:
            return conditional_escape(col)

    def ordering(self, qs):
        return super(RequestLogDataJson, self).ordering(qs)

    def filter_queryset(self, qs):
        # use request parameters to filter queryset
        GET = self.request.GET
        data_filter = {}

        duration = GET.get('duration[]', None)
        if duration:
            try:
                secs = float(duration)
            except ValueError:
                pass
            else:
                d = datetime.timedelta(seconds=secs)
                qs = qs.filter(duration__gte=d)

        method = GET.get('method[]', None)
        if method:
            qs = qs.filter(method=method)

        username = GET.get('username[]', None)
        if username:
            qs = qs.filter(username__contains=username)

        path = GET.get('path[]', None)
        if path:
            qs = qs.filter(path__contains=path)

        ip = GET.get('ip[]', None)
        if ip:
            data_filter['ip'] = ip

        session_key = GET.get('session_key[]', None)
        if session_key:
            data_filter['session_key'] = session_key

        status_code = GET.get('status_code[]', None)
        if status_code and status_code.isnumeric():
            data_filter['status_code'] = int(status_code)

        if data_filter:
            qs = qs.data_contains(data_filter)

        return qs


class CeleryTaskDataJson(BaseDatatableView):
    model = CeleryTaskLog
    max_display_length = 500
    columns = CeleryTaskLog.display_columns

    def render_column(self, logentry, column):
        if column == 'time':
            txt = logentry.time
            url = reverse('sysadmin:log_view', kwargs={'log_type': 'task', 'log_id': str(logentry.id)})
            col = mark_safe(f'<a href="{conditional_escape(url)}">{conditional_escape(txt)}</a>')
        else:
            col = getattr(logentry, column)

        if col is None:
            return '&mdash;'
        else:
            return conditional_escape(col)

    def ordering(self, qs):
        return super(CeleryTaskDataJson, self).ordering(qs)

    def filter_queryset(self, qs):
        # use request parameters to filter queryset
        GET = self.request.GET

        duration = GET.get('duration[]', None)
        if duration:
            try:
                secs = float(duration)
            except ValueError:
                pass
            else:
                d = datetime.timedelta(seconds=secs)
                qs = qs.filter(duration__gte=d)

        task = GET.get('task[]', None)
        if task:
            qs = qs.filter(task__contains=task)

        exception = GET.get('exception[]', None)
        if exception:
            if exception == 'YES':
                qs = qs.filter(data__has_key='exception')
            elif exception == 'NO':
                qs = qs.exclude(data__has_key='exception')

        return qs


def _log_data(log_type, request):
    return EVENT_DATA_VIEWS[log_type].as_view()(request)


EVENT_DATA_VIEWS = {
    'request': RequestLogDataJson,
    'task': CeleryTaskDataJson,
}


@requires_global_role("SYSA")
def log_view(request, log_type: str, log_id: str):
    """
    View to inspect a single EventLog
    """
    try:
        ModelClass = EVENT_LOG_TYPES[log_type]
    except KeyError:
        raise Http404

    logentry = get_object_or_404(ModelClass, id=log_id)
    display_data = {
        field.name: getattr(logentry, field.name)
        for field in ModelClass._meta.get_fields()
        if field.name != 'data'
    }
    display_data.update(logentry.data)
    context = {
        'log_type': log_type,
        'logentry': logentry,
        'display_data': display_data,
    }
    return render(request, 'log/log_view.html', context)