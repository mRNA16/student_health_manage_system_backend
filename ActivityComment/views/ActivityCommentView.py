from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from ActivityComment.models.ActivityComment import ActivityComment
from ActivityComment.serializers.ActivityCommentSerializer import ActivityCommentSerializer

class ActivityCommentViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        activity_type = self.request.query_params.get('activity_type')
        activity_id = self.request.query_params.get('activity_id')
        queryset = ActivityComment.objects.all()
        if activity_type and activity_id:
            queryset = queryset.filter(activity_type=activity_type, activity_id=activity_id)
        return queryset.order_by('created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'data': serializer.data,
            'message': '获取评论列表成功'
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'code': 0,
            'data': serializer.data,
            'message': '评论发布成功'
        }, status=status.HTTP_201_CREATED)