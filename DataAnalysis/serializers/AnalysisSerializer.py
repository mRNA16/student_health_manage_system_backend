from rest_framework import serializers
from ..models.AnalysisResult import AnalysisResult

class AnalysisResultSerializer(serializers.ModelSerializer):
    analysis_type_display = serializers.CharField(source='get_analysis_type_display', read_only=True)
    def to_representation(self, instance):
        data = super().to_representation(instance)
        result_data = data.pop('result_data', {})  # 移除 result_data 并获取其内容
        return {**data, **result_data}  # 合并到外层
    class Meta:
        model = AnalysisResult
        fields = ['id', 'analysis_type', 'analysis_type_display', 'result_data', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class AnalysisRequestSerializer(serializers.Serializer):
    analysis_type = serializers.ChoiceField(choices=AnalysisResult.ANALYSIS_TYPES)
    time_range = serializers.CharField(max_length=10, default='30d', help_text="时间范围: 7d, 30d, 90d")
    include_predictions = serializers.BooleanField(default=True, help_text="是否包含预测数据") 