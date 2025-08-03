from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Friend
from ..serializers.FriendSerializer import FriendSerializer
from django.contrib.auth.models import User
from django.db.models import Q
from SportManage.models.SportRecord import SportRecord
from SleepManage.models.SleepRecord import SleepRecord
from DietManage.models.MealRecord import MealRecord
from django.utils.timezone import localtime
import os
import json

class FriendViewSet(viewsets.ModelViewSet):
    queryset = Friend.objects.all()
    serializer_class = FriendSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 默认返回当前用户相关的好友关系
        user = self.request.user
        return Friend.objects.filter(
            Q(from_user=user) | Q(to_user=user)
        )

    def perform_create(self, serializer):
        # 确保from_user是当前用户
        serializer.save(from_user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'data': serializer.data,
            'message': '获取好友数据成功'
        })

    def retrieve(self, request, *args, **kwargs):
        # instance = self.get_object()
        # serializer = self.get_serializer(instance)
        friend_id = self.kwargs.get('pk')
        user = User.objects.get(pk = friend_id)
        activities = []
        sport_records = SportRecord.objects.filter(user=user)
        met_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'SportManage', 'met.json')
        with open(met_path, 'r', encoding='utf-8') as f:
            mets = json.load(f)
        for record in sport_records:
            activities.append({
                'id': record.id,
                'type': 'sport',
                'content': f"进行了{mets[record.sport]['name']}，持续{record.duration}分钟",
                'timestamp': localtime(record.created_at).isoformat()
            })
        sleep_records = SleepRecord.objects.filter(user=user)
        for record in sleep_records:
            activities.append({
                'id': record.id,
                'type': 'sleep',
                'content': f"睡眠了{record.duration}小时",
                'timestamp': localtime(record.created_at).isoformat()
            })

        meal_records = MealRecord.objects.filter(user=user)
        for record in meal_records:
            activities.append({
                'id': record.id,
                'type': 'meal',
                'content': f"记录了{record.meal}",
                'timestamp': localtime(record.created_at).isoformat()
            })
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return Response({
            'code': 0,
            'data': {
                # **serializer.data,
                'activities': activities
            },
            'message': '获取好友详情成功'
        })

    @action(detail=False, methods=['get'])
    def friends(self, request):
        # 获取当前用户的好友列表（已接受的）
        user = request.user
        friends = Friend.objects.filter(
            Q(from_user=user) | Q(to_user=user),
            status='accepted'
        )
        serializer = self.get_serializer(friends, many=True)
        return Response({
            'code': 0,
            'data': serializer.data,
            'message': '获取好友列表成功'
        })

    @action(detail=False, methods=['get'])
    def received_requests(self, request):
        # 获取当前用户收到的好友请求
        user = request.user
        requests = Friend.objects.filter(to_user=user, status='pending')
        serializer = self.get_serializer(requests, many=True)
        return Response({
            'code': 0,
            'data': serializer.data,
            'message': '获取收到的好友请求成功'
        })

    @action(detail=False, methods=['get'])
    def sent_requests(self, request):
        # 获取当前用户发送的好友请求
        user = request.user
        requests = Friend.objects.filter(from_user=user, status='pending')
        serializer = self.get_serializer(requests, many=True)
        return Response({
            'code': 0,
            'data': serializer.data,
            'message': '获取发送的好友请求成功'
        })

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        # 接受好友请求
        friend_request = self.get_object()
        if friend_request.to_user != request.user:
            return Response({
                'code': 1,
                'message': '无权接受此请求'
            }, status=status.HTTP_403_FORBIDDEN)

        friend_request.status = 'accepted'
        friend_request.save()
        return Response({
            'code': 0,
            'message': '接受好友请求成功'
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        # 拒绝好友请求
        friend_request = self.get_object()
        if friend_request.to_user != request.user:
            return Response({
                'code': 1,
                'message': '无权拒绝此请求'
            }, status=status.HTTP_403_FORBIDDEN)

        friend_request.status = 'rejected'
        friend_request.save()
        return Response({
            'code': 0,
            'message': '拒绝好友请求成功'
        })

    @action(detail=False, methods=['post'])
    def send(self, request):
        to_user_id = request.data.get('to_user')
        if not to_user_id:
            return Response({'code': 1, 'message': '缺少 to_user_id'}, status=status.HTTP_400_BAD_REQUEST)

        from_user = request.user

        if str(from_user.id) == str(to_user_id):
            return Response({'code': 1, 'message': '不能添加自己为好友'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查是否已有请求或已是好友
        if Friend.objects.filter(
            (Q(from_user=from_user, to_user_id=to_user_id) |
            Q(from_user_id=to_user_id, to_user=from_user)) &
            (Q(status = 'pending') | Q(status = 'accepted'))
        ).exists():
            return Response({'code': 1, 'message': '已存在好友关系或请求'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建好友请求
        friend_request = Friend.objects.create(from_user=from_user, to_user_id=to_user_id)
        serializer = self.get_serializer(friend_request)
        return Response({'code': 0, 'message': '好友请求已发送', 'data': serializer.data})

    @action(detail=True, methods=['delete'])
    def cancel(self, request, pk=None):
        friend_request = self.get_object()
        if friend_request.from_user != request.user:
            return Response({'code': 1, 'message': '无权取消该请求'}, status=status.HTTP_403_FORBIDDEN)
        if friend_request.status != 'pending':
            return Response({'code': 1, 'message': '只有待处理的请求才能取消'}, status=status.HTTP_400_BAD_REQUEST)
        friend_request.delete()
        return Response({'code': 0, 'message': '好友请求已取消'})


    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        # 移除好友
        friend = self.get_object()
        if friend.from_user != request.user and friend.to_user != request.user:
            return Response({
                'code': 1,
                'message': '无权移除此好友'
            }, status=status.HTTP_403_FORBIDDEN)

        friend.delete()
        return Response({
            'code': 0,
            'message': '移除好友成功'
        })