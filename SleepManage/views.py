from rest_framework import viewsets, permissions
from .models import SleepRecord
from .serializers import SleepRecordSerializer
from datetime import timedelta, date
from rest_framework.response import Response

class SleepRecordViewSet(viewsets.ModelViewSet):
    serializer_class = SleepRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = SleepRecord.objects.filter(user=user)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            qs = qs.filter(date__range=[start_date, end_date])
        return qs

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