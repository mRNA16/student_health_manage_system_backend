from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
import numpy as np
import random
from DietManage import sql
from utils.api_utils import (
    success_api_response, failed_api_response, ErrorCode, parse_data
)
from utils.cache_utils import invalidate_health_cache

class MealRecordViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user_id = request.user.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        records = sql.get_meal_records(user_id, start_date, end_date)
        return Response(success_api_response(records, message='获取成功'))

    def retrieve(self, request, pk=None):
        record = sql.get_meal_record_by_id(pk)
        if not record:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "记录不存在"))
        if record['user_id'] != request.user.id:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, "无权访问"))
        return Response(success_api_response(record, message='获取成功'))

    def create(self, request):
        data = parse_data(request)
        if not data:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS, "无效的请求数据"))
        
        user_id = request.user.id
        new_record = sql.create_meal_record(
            user_id,
            data.get('date'),
            data.get('meal'),
            data.get('source', 'manual'),
            data.get('items', [])
        )
        
        # Invalidate health cache
        invalidate_health_cache(user_id)
        
        return Response(success_api_response(new_record, message='创建成功'))

    def update(self, request, pk=None):
        return self.partial_update(request, pk)

    def partial_update(self, request, pk=None):
        data = parse_data(request)
        if not data:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS, "无效的请求数据"))
            
        status_code, updated_record = sql.update_meal_record_safe(
            pk,
            request.user.id,
            date=data.get('date'),
            meal=data.get('meal'),
            source=data.get('source'),
            items=data.get('items')
        )
        
        if status_code == 1:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "记录不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, "无权修改"))
        elif status_code == 3:
            return Response(failed_api_response(ErrorCode.SYSTEM_ERROR, "数据库执行错误"))
            
        # Invalidate health cache
        invalidate_health_cache(request.user.id)
            
        return Response(success_api_response(updated_record, message='更新成功'))

    def destroy(self, request, pk=None):
        status_code = sql.delete_meal_record_safe(pk, request.user.id)
        
        if status_code == 1:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "记录不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, "无权删除"))
            
        # Invalidate health cache
        invalidate_health_cache(request.user.id)
            
        return Response(success_api_response(None, message='删除成功'))

    @action(detail=False, methods=['get'], url_path='analysis')
    def analysis(self, request):
        user_id = request.user.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Call the stored procedure for heavy lifting
        daily_raw, details_raw, monthly_data, metrics = sql.get_diet_analysis(user_id, start_date, end_date)

        # Map food details per day
        daily_details = {}
        for d in details_raw:
            date_str = d['date'].strftime('%Y-%m-%d') if hasattr(d['date'], 'strftime') else str(d['date'])
            daily_details.setdefault(date_str, [])
            daily_details[date_str].append({"name": d['name'], "value": d['value']})

        # Final daily data assembly
        daily_data = []
        for d in daily_raw:
            date_str = d['date'].strftime('%Y-%m-%d') if hasattr(d['date'], 'strftime') else str(d['date'])
            daily_data.append({
                "date": date_str,
                "breakfast": d['breakfast'],
                "lunch": d['lunch'],
                "dinner": d['dinner'],
                "total": d['total'],
                "foodDetails": daily_details.get(date_str, [])
            })

        # Core Metrics & Scores
        avgDailyCalories = metrics.get('avgDailyCalories') or 0
        avgMealsPerDay = metrics.get('avgMealsPerDay') or 0

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

        return Response(success_api_response({
            'dailyData': daily_data,
            'yearlyData': monthly_data,
            'avgDailyCalories': avgDailyCalories,
            'avgMealsPerDay': avgMealsPerDay,
            'calorieScore': calorieScore,
            'regularityScore': regularityScore,
            'dietScore': dietScore
        }, message='分析成功'))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def food_list(request):
    foods = sql.get_all_nutrition_foods()
    return Response(success_api_response(foods, message='获取成功'))