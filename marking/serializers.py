from rest_framework import views, serializers
from rest_framework import generics
from marking.models import ActivityMark, ActivityComponentMark

from .models import ActivityMark, COMMENT_LENGTH

class MarkingDetails(serializers.ModelSerializer):
    # rename some fields in the API so they're more meaningful
    mark_penalty = serializers.DecimalField(max_digits=8, decimal_places=2, source='mark_adjustment')
    mark_penalty_reason = serializers.CharField(max_length=COMMENT_LENGTH, source='mark_adjustment_reason')
    late_percent = serializers.DecimalField(max_digits=5, decimal_places=2, source='late_penalty')
    the_mark = serializers.DecimalField(max_digits=5, decimal_places=2, source='mark', read_only=True)

    # read-only fields
    created_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)

    # additional fields beyond the model itself
    userid = serializers.CharField(max_length=8)

    class Meta:
        model = ActivityMark
        #fields = ('slug', 'name', 'short_name', 'due_date', 'percent', 'group', 'url', 'max_grade', 'is_numeric', 'is_calculated')
        exclude = ('mark_adjustment', 'late_penalty', 'mark_adjustment_reason', 'mark',
                   'file_attachment', 'file_mediatype', 'activity', 'id')


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

