from gpaconvert.models import GradeSource
from gpaconvert.utils import render_to


@render_to('gpaconvert/grade_source_list.html')
def list_grade_sources(request):
    grade_sources = GradeSource.objects.filter(status='ACTI')

    return {
        'grade_sources': grade_sources,
    }
