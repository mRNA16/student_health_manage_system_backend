from rest_framework import serializers
from SportManage.models import SportRecord

class SportRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SportRecord
        fields = '__all__'
        read_only_fields = ['user','duration', 'calories']