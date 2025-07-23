from rest_framework import viewsets, permissions
from .models import SleepRecord
from .serializers import SleepRecordSerializer
from datetime import timedelta, date

class SleepRecordViewSet(viewsets.ModelViewSet):
    serializer_class = SleepRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = SleepRecord.objects.filter(user=user)
        week = self.request.query_params.get('week')
        if week:
            today = date.today()
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            qs = qs.filter(date__range=[start, end])
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)