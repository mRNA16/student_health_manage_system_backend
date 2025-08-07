from django.db import models
from django.contrib.auth.models import User

class AnalysisResult(models.Model):
    ANALYSIS_TYPES = [
        ('sleep_prediction', '睡眠质量预测'),
        ('sleep_sport_correlation', '睡眠运动关联性'),
        ('health_trend', '健康趋势分析'),
        ('calorie_analysis', '卡路里分析'),
        ('sleep_quality_score', '睡眠质量评分'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analysis_results')
    analysis_type = models.CharField(max_length=50, choices=ANALYSIS_TYPES)
    result_data = models.JSONField(help_text="分析结果数据")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'analysis_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_analysis_type_display()} - {self.created_at}" 