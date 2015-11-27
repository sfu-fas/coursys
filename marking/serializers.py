from rest_framework import serializers
from marking.models import ActivityMark, ActivityComponentMark

class MarkComponentSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='activity_component.title')
    description = serializers.CharField(source='activity_component.description')
    max_grade = serializers.CharField(source='activity_component.max_mark')
    grade = serializers.DecimalField(
        max_digits=ActivityComponentMark._meta.get_field_by_name('value')[0].max_digits,
        decimal_places=ActivityComponentMark._meta.get_field_by_name('value')[0].decimal_places,
        source='value')

    class Meta:
        model = ActivityComponentMark
        fields = ('title', 'description', 'max_grade', 'grade', 'comment')


class MarkDetailSerializer(serializers.ModelSerializer):
    components = MarkComponentSerializer(many=True, read_only=True)
    grade = serializers.DecimalField(
        max_digits=ActivityMark._meta.get_field_by_name('mark')[0].max_digits,
        decimal_places=ActivityMark._meta.get_field_by_name('mark')[0].decimal_places,
        source='mark')

    class Meta:
        model = ActivityMark
        fields = ('components', 'late_penalty', 'mark_adjustment', 'mark_adjustment_reason', 'overall_comment', 'grade')
        # TODO: file attachments?
        # TODO: indicate individual/group marking?

    def to_native(self, m):
        # annotate the activity with its components before starting
        components = m.activitycomponentmark_set.all().select_related('activity_component').order_by('activity_component__position')
        m.components = components

        return super(MarkDetailSerializer, self).to_native(m)
