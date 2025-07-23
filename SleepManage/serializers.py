from rest_framework import serializers
from .models import SleepRecord

class SleepRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SleepRecord
        fields = '__all__'
        read_only_fields = ['user', 'duration']