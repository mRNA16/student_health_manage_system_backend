from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, permissions, status
from SportManage.models import SportRecord
from SportManage.serializers.SportRecordSerializer import SportRecordSerializer
from datetime import datetime, timedelta
import numpy as np
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

    @action(detail=False, methods=['get'], url_path='analysis')
    def analysis(self, request):
        user = request.user
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        qs = SportRecord.objects.filter(user=user)
        if start_date and end_date:
            qs = qs.filter(date__range=[start_date, end_date])
        records = list(qs.order_by('date').values('date', 'duration', 'calories', 'sport'))

        # 读取运动类型映射
        met_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'met.json')
        with open(met_path, 'r', encoding='utf-8') as f:
            sports = json.load(f)
        sport_id_to_name = {i: s['name'] for i, s in enumerate(sports)}

        # 健康标准
        LOW_ACTIVITY_THRESHOLD = 170
        CONTINUOUS_DAYS_THRESHOLD = 3

        # 日聚合
        daily_map = {}
        sport_details_map = {}
        for r in records:
            date_str = r['date'].strftime('%Y-%m-%d')
            if date_str not in daily_map:
                daily_map[date_str] = {'calories': 0, 'duration': 0}
                sport_details_map[date_str] = {}
            daily_map[date_str]['calories'] += r['calories'] or 0
            daily_map[date_str]['duration'] += r['duration'] or 0
            # 统计每种运动类型的卡路里
            sport_name = sport_id_to_name.get(r['sport'], f"r['sport']")
            sport_details_map[date_str][sport_name] = sport_details_map[date_str].get(sport_name, 0) + (r['calories'] or 0)

        daily_data = []
        for k, v in daily_map.items():
            sport_details = [
                {"name": name, "value": value}
                for name, value in sport_details_map[k].items()
            ]
            daily_data.append({
                "date": k,
                "totalCalories": round(v['calories'], 1),
                "totalDuration": round(v['duration'], 1),
                "sportDetails": sport_details
            })
        daily_data.sort(key=lambda x: x['date'])

        # 月聚合
        monthly_map = {}
        for item in daily_data:
            month = item['date'][:7]
            if month not in monthly_map:
                monthly_map[month] = {'calories': 0, 'duration': 0, 'days': 0}
            monthly_map[month]['calories'] += item['totalCalories']
            monthly_map[month]['duration'] += item['totalDuration']
            monthly_map[month]['days'] += 1
        yearly_data = [
            {
                'date': month,
                'avgCalories': round(data['calories'] / data['days'], 1) if data['days'] else 0,
                'totalCalories': round(data['calories'], 1),
                'avgDuration': round(data['duration'] / data['days'], 1) if data['days'] else 0,
            }
            for month, data in monthly_map.items()
        ]
        yearly_data.sort(key=lambda x: x['date'])

        # 运动核心指标
        days = len(daily_map)
        avgDailyDuration = round(np.mean([v['duration'] for v in daily_map.values()]), 1) if days else 0
        avgDailyCalories = round(np.mean([v['calories'] for v in daily_map.values()]), 1) if days else 0

        # 活动频率得分（每周至少3天）
        time_range_days = (qs.last().date - qs.first().date).days + 1 if qs.exists() else 1
        activeDaysPerWeek = (days / (time_range_days / 7)) * 100 if time_range_days else 0
        frequencyScore = min(100, activeDaysPerWeek * 1.5)
        durationScore = min(100, avgDailyDuration * 60)  # 目标30分钟/天
        calorieScore = min(100, avgDailyCalories / 3)    # 目标300千卡/天
        sportScore = round((frequencyScore * 0.3 + durationScore * 0.35 + calorieScore * 0.35) / 10) * 10

        # 连续低运动量天数
        recent_dates = [
            (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(13, -1, -1)
        ]
        currentStreak = 0
        maxStreak = 0
        for date in recent_dates:
            calories = daily_map.get(date, {}).get('calories', 0)
            if calories < LOW_ACTIVITY_THRESHOLD:
                currentStreak += 1
                maxStreak = max(maxStreak, currentStreak)
            else:
                currentStreak = 0
        continuousLowActivityDays = maxStreak

        # 运动问题标签
        activityIssues = []
        if avgDailyDuration < 0.5:
            activityIssues.append("平均每日运动时长不足（建议≥30分钟）")
        if avgDailyCalories < 300:
            activityIssues.append("平均每日消耗热量偏低（建议≥300千卡）")
        if continuousLowActivityDays >= CONTINUOUS_DAYS_THRESHOLD:
            activityIssues.append(f"连续{continuousLowActivityDays}天运动量偏低")

        # 核心建议
        coreAdvice = [
            "1. 每天坚持30分钟中等强度运动。",
            "2. 多样化运动类型，避免单一。",
            "3. 运动前做好热身，运动后拉伸。"
        ]

        # 针对性建议
        specificAdvice = []
        if avgDailyDuration < 0.5:
            specificAdvice.append("• 增加每日运动时长，逐步达到30分钟。")
        if avgDailyCalories < 300:
            specificAdvice.append("• 提高运动强度或延长运动时间。")
        if continuousLowActivityDays >= CONTINUOUS_DAYS_THRESHOLD:
            specificAdvice.append(f"• 避免连续{CONTINUOUS_DAYS_THRESHOLD}天运动量过低，适当安排锻炼。")
        if not specificAdvice:
            specificAdvice.append("• 保持良好运动习惯，继续加油！")

        # 运动小贴士（随机3条）
        import random
        allTips = [
            "• 运动时保持补水，避免脱水。",
            "• 选择适合自己的运动项目。",
            "• 运动后适当补充蛋白质。",
            "• 合理安排运动与休息，避免过度训练。",
            "• 运动时注意安全，量力而行。"
        ]
        activityTips = random.sample(allTips, 3) if len(allTips) >= 3 else allTips

        return Response({
            'code': 0,
            'message': '分析成功',
            'data': {
                'dailyData': daily_data,
                'yearlyData': yearly_data,
                'avgDailyDuration': avgDailyDuration,
                'avgDailyCalories': avgDailyCalories,
                'frequencyScore': frequencyScore,
                'durationScore': durationScore,
                'calorieScore': calorieScore,
                'sportScore': sportScore,
                'continuousLowActivityDays': continuousLowActivityDays,
                'activityIssues': activityIssues,
                'coreAdvice': coreAdvice,
                'specificAdvice': specificAdvice,
                'activityTips': activityTips,
                'LOW_ACTIVITY_THRESHOLD': LOW_ACTIVITY_THRESHOLD,
                'CONTINUOUS_DAYS_THRESHOLD': CONTINUOUS_DAYS_THRESHOLD,
            }
        }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sport_list(request):
    met_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'met.json')
    with open(met_path, 'r', encoding='utf-8') as f:
        sports = json.load(f)
    return Response({
            'code': 0,
            'message': '获取成功',
            'data': sports
        })