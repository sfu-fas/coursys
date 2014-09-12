from rest_framework import serializers
from marking.models import ActivityMark

class MarkSerializer(serializers.ModelSerializer):
    components = serializers.SerializerMethodField('get_component_marks', help_text='Grades on each component')

    class Meta:
        model = ActivityMark
        fields = ('components', 'late_penalty', 'mark_adjustment', 'mark_adjustment_reason', 'overall_comment', 'mark')
        # TODO: file attachments?
        # TODO: indicate individual/group marking?

    def get_component_marks(self, m):
        # TODO: make this a sub-serializer on ComponentMarks?
        componentmarks = m.activitycomponentmark_set.all().select_related('activity_component').order_by('activity_component__position')
        marks = []
        for cm in componentmarks:
            cmdata = {
                'title': cm.activity_component.title,
                'description': cm.activity_component.description,
                'max_grade': cm.activity_component.max_mark,
                'grade': cm.value,
                'comment': cm.comment,
            }
            marks.append(cmdata)

        return marks
