from rest_framework import serializers

class SubmissionsSerializer(serializers.Serializer):
    userid = serializers.SlugField(max_length=8)
    group = serializers.SlugField()
    component = serializers.SlugField()
    submitted_at = serializers.DateTimeField()
    text = serializers.CharField()