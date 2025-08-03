from rest_framework import serializers
from ..models import Friend
from django.contrib.auth.models import User

class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class FriendSerializer(serializers.ModelSerializer):
    from_user = UserInfoSerializer(read_only=True)
    to_user = UserInfoSerializer(read_only=True)
    from_user_id = serializers.PrimaryKeyRelatedField(write_only=True, queryset=User.objects.all(), source='from_user')
    to_user_id = serializers.PrimaryKeyRelatedField(write_only=True, queryset=User.objects.all(), source='to_user')

    class Meta:
        model = Friend
        fields = ['id', 'from_user', 'to_user', 'from_user_id', 'to_user_id', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']

    def validate(self, data):
        # 检查不能添加自己为好友
        if data['from_user'] == data['to_user']:
            raise serializers.ValidationError("不能添加自己为好友")
        # 检查是否已经发送过请求
        if Friend.objects.filter(from_user=data['from_user'], to_user=data['to_user']).exists():
            raise serializers.ValidationError("已经发送过好友请求")
        return data