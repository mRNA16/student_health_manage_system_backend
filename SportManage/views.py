from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, permissions
from .models import SportRecord
from .serializers import SportRecordSerializer
import json
import os

class SportRecordViewSet(viewsets.ModelViewSet):
    queryset = SportRecord.objects.all()
    serializer_class = SportRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 只返回当前用户的运动记录
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # 序列化数据
        serializer = self.get_serializer(queryset, many=True)

        # 自定义响应结构
        return Response({
            'code': 0,
            'message': '获取成功',
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            'code': 0,
            'message': '创建成功',
            'data': response.data
        })
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({
            'code': 0,
            'message': '更新成功',
            'data': response.data
        })
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 0,
            'message': '删除成功',
            'data': None
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sport_list(request):
    met_path = os.path.join(os.path.dirname(__file__), 'met.json')
    with open(met_path, 'r', encoding='utf-8') as f:
        sports = json.load(f)
    return Response({
            'code': 0,
            'message': '获取成功',
            'data': sports
        })