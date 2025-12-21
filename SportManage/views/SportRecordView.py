from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
import json
import os
import random
from SportManage import sql
from utils.api_utils import (
    success_api_response, failed_api_response, ErrorCode, parse_data
)
from utils.cache_utils import invalidate_health_cache, invalidate_friend_feed_cache

class SportRecordViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user_id = request.user.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        records = sql.get_sport_records(user_id, start_date, end_date)
        return Response(success_api_response(records, message='获取成功'))

    def retrieve(self, request, pk=None):
        record = sql.get_sport_record_by_id(pk)
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
        new_record = sql.create_sport_record(
            user_id,
            data.get('date'),
            data.get('sport'),
            data.get('begin_time'),
            data.get('end_time')
        )
        
        # Invalidate health and friend feed cache
        invalidate_health_cache(user_id)
        invalidate_friend_feed_cache(user_id)
        
        return Response(success_api_response(new_record, message='创建成功'))

    def update(self, request, pk=None):
        return self.partial_update(request, pk)

    def partial_update(self, request, pk=None):
        data = parse_data(request)
        if not data:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS, "无效的请求数据"))
            
        status_code, updated_record = sql.update_sport_record_safe(
            pk,
            request.user.id,
            data.get('date'),
            data.get('sport'),
            data.get('begin_time'),
            data.get('end_time')
        )
        
        if status_code == 1:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "记录不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, "无权修改"))
            
        # Invalidate health and friend feed cache
        invalidate_health_cache(request.user.id)
        invalidate_friend_feed_cache(request.user.id)
            
        return Response(success_api_response(updated_record, message='更新成功'))

    def destroy(self, request, pk=None):
        status_code = sql.delete_sport_record_safe(pk, request.user.id)
        
        if status_code == 1:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "记录不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, "无权删除"))
            
        # Invalidate health and friend feed cache
        invalidate_health_cache(request.user.id)
        invalidate_friend_feed_cache(request.user.id)
            
        return Response(success_api_response(None, message='删除成功'))

    @action(detail=False, methods=['get'], url_path='analysis')
    def analysis(self, request):
        user_id = request.user.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Call the stored procedure for heavy lifting
        daily_raw, details_raw, monthly_data, metrics = sql.get_sport_analysis(user_id, start_date, end_date)

        # Read sport names for mapping
        met_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'met.json')
        with open(met_path, 'r', encoding='utf-8') as f:
            sports = json.load(f)
        sport_id_to_name = {i: s['name'] for i, s in enumerate(sports)}

        # Map sport details
        daily_details = {}
        for d in details_raw:
            date_str = d['date'].strftime('%Y-%m-%d') if hasattr(d['date'], 'strftime') else str(d['date'])
            daily_details.setdefault(date_str, [])
            sport_name = sport_id_to_name.get(d['sport'], f"Sport {d['sport']}")
            daily_details[date_str].append({"name": sport_name, "value": d['calories']})

        # Final daily data assembly
        daily_data = []
        for d in daily_raw:
            date_str = d['date'].strftime('%Y-%m-%d') if hasattr(d['date'], 'strftime') else str(d['date'])
            daily_data.append({
                "date": date_str,
                "totalCalories": d['totalCalories'],
                "totalDuration": d['totalDuration'],
                "sportDetails": daily_details.get(date_str, [])
            })
        
        # Get last 14 days for streak
        recent_dates = [
            (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(13, -1, -1)
        ]
        daily_map = {d['date']: d['totalCalories'] for d in daily_data}
        currentStreak = 0
        maxStreak = 0
        for date_key in recent_dates:
            calories = daily_map.get(date_key, 0)
            if calories < 170:
                currentStreak += 1
                maxStreak = max(maxStreak, currentStreak)
            else:
                currentStreak = 0
        continuousLowActivityDays = maxStreak

        avgDailyDuration = metrics.get('avgDailyDuration', 0)
        avgDailyCalories = metrics.get('avgDailyCalories', 0)

        return Response(success_api_response({
            'dailyData': daily_data,
            'yearlyData': monthly_data,
            'avgDailyDuration': avgDailyDuration,
            'avgDailyCalories': avgDailyCalories,
            'frequencyScore': metrics.get('frequencyScore', 0),
            'durationScore': metrics.get('durationScore', 0),
            'calorieScore': metrics.get('calorieScore', 0),
            'sportScore': metrics.get('sportScore', 0),
            'continuousLowActivityDays': continuousLowActivityDays
        }, message='分析成功'))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sport_list(request):
    met_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'met.json')
    with open(met_path, 'r', encoding='utf-8') as f:
        sports = json.load(f)
    return Response(success_api_response(sports, message='获取成功'))