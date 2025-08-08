from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from DietManage.models.MealRecord import MealRecord
from DietManage.models.MealItem import MealItem
from DietManage.models.NutritionFood import NutritionFood
from DietManage.serializers.DietRecordSerializer import MealRecordSerializer, MealItemSerializer, NutritionFoodSerializer
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

class MealRecordViewSet(viewsets.ModelViewSet):
    serializer_class = MealRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MealRecord.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
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
        qs = MealRecord.objects.filter(user=user)
        if start_date and end_date:
            qs = qs.filter(date__range=[start_date, end_date])
        # 用序列化器获取完整结构
        serializer = MealRecordSerializer(qs, many=True)
        records = serializer.data

        # 食物名称映射
        food_map = {f.id: f.name for f in NutritionFood.objects.all()}

        # 日聚合
        daily_map = {}
        food_details_map = {}
        for r in records:
            date_str = r['date']
            if date_str not in daily_map:
                daily_map[date_str] = {'breakfast': 0, 'lunch': 0, 'dinner': 0, 'total': 0}
                food_details_map[date_str] = defaultdict(float)
            meal = r['meal']
            items = r['items'] or []
            meal_calories = 0
            for item in items:
                food_id = item.get('food')
                cal = item.get('estimated_calories', 0)
                meal_calories += cal
                food_name = food_map.get(food_id, f"食物{food_id}")
                food_details_map[date_str][food_name] += cal
            daily_map[date_str][meal] += meal_calories
            daily_map[date_str]['total'] += meal_calories

        daily_data = []
        for k, v in daily_map.items():
            food_details = [
                {"name": name, "value": value}
                for name, value in food_details_map[k].items()
            ]
            daily_data.append({
                "date": k,
                "breakfast": round(v['breakfast'], 1),
                "lunch": round(v['lunch'], 1),
                "dinner": round(v['dinner'], 1),
                "total": round(v['total'], 1),
                "foodDetails": food_details
            })
        daily_data.sort(key=lambda x: x['date'])

        # 月聚合
        monthly_map = {}
        for item in daily_data:
            month = item['date'][:7]
            if month not in monthly_map:
                monthly_map[month] = {'total': 0, 'days': 0}
            monthly_map[month]['total'] += item['total']
            monthly_map[month]['days'] += 1
        yearly_data = [
            {
                'date': month,
                'avgCalories': round(data['total'] / data['days'], 1) if data['days'] else 0,
                'totalCalories': round(data['total'], 1),
            }
            for month, data in monthly_map.items()
        ]
        yearly_data.sort(key=lambda x: x['date'])

        # 饮食核心指标
        days = len(daily_map)
        avgDailyCalories = round(np.mean([v['total'] for v in daily_map.values()]), 1) if days else 0
        avgMealsPerDay = round(np.mean([
            sum(1 for m in ['breakfast', 'lunch', 'dinner'] if v[m] > 0)
            for v in daily_map.values()
        ]), 2) if days else 0

        # 卡路里得分
        calorieScore = 0
        if 1800 <= avgDailyCalories <= 2500:
            calorieScore = 100
        elif 1500 <= avgDailyCalories < 1800 or 2500 < avgDailyCalories <= 2800:
            calorieScore = 70
        elif 1200 <= avgDailyCalories < 1500 or 2800 < avgDailyCalories <= 3100:
            calorieScore = 40
        # 规律性得分
        regularityScore = min(100, 100 - abs(avgMealsPerDay - 3) * 30)
        # 综合饮食得分
        dietScore = round((calorieScore * 0.6 + regularityScore * 0.4) / 10) * 10

        # 饮食问题标签
        dietIssues = []
        if not (1800 <= avgDailyCalories <= 2500):
            dietIssues.append("平均每日热量不在推荐区间（1800-2500kcal）")
        if abs(avgMealsPerDay - 3) > 0.5:
            dietIssues.append("每日餐次不规律（建议每天3餐）")

        # 核心建议
        coreAdvice = [
            "1. 保持三餐规律，避免暴饮暴食。",
            "2. 每餐均衡摄入主食、蛋白、蔬菜。",
            "3. 控制高油高糖食物摄入。"
        ]
        # 针对性建议
        specificAdvice = []
        if avgDailyCalories < 1800:
            specificAdvice.append("• 适当增加主食、蛋白质摄入，避免能量不足。")
        if avgDailyCalories > 2500:
            specificAdvice.append("• 控制高热量食物摄入，减少油炸、甜食。")
        if abs(avgMealsPerDay - 3) > 0.5:
            specificAdvice.append("• 规律用餐，尽量做到每天三餐定时定量。")
        if not specificAdvice:
            specificAdvice.append("• 保持良好饮食习惯，继续加油！")
        # 饮食小贴士（随机3条）
        import random
        allTips = [
            "• 多喝水，少饮含糖饮料。",
            "• 每天至少吃400克蔬菜水果。",
            "• 细嚼慢咽，帮助消化。",
            "• 晚餐不宜过晚，避免影响睡眠。",
            "• 适量摄入坚果，有益心脑健康。"
        ]
        dietTips = random.sample(allTips, 3) if len(allTips) >= 3 else allTips

        return Response({
            'code': 0,
            'message': '分析成功',
            'data': {
                'dailyData': daily_data,
                'yearlyData': yearly_data,
                'avgDailyCalories': avgDailyCalories,
                'avgMealsPerDay': avgMealsPerDay,
                'calorieScore': calorieScore,
                'regularityScore': regularityScore,
                'dietScore': dietScore,
                'dietIssues': dietIssues,
                'coreAdvice': coreAdvice,
                'specificAdvice': specificAdvice,
                'dietTips': dietTips,
                'CALORIE_RANGE': [1800, 2500],
                'MEALS_TARGET': 3,
            }
        }, status=status.HTTP_200_OK)

class MealItemViewSet(viewsets.ModelViewSet):
    serializer_class = MealItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MealItem.objects.filter(meal_record__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
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
def food_list(request):
    foods = NutritionFood.objects.all()
    serializer = NutritionFoodSerializer(foods, many=True)
    return Response({
        'code': 0,
        'message': '获取成功',
        'data': serializer.data
    })