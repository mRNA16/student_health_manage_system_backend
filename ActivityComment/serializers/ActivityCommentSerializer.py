from rest_framework import serializers
from ActivityComment.models.ActivityComment import ActivityComment

class ActivityCommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ActivityComment
        fields = ['id', 'user', 'username', 'activity_type', 'activity_id', 'content', 'created_at']
        read_only_fields = ['user', 'created_at']
