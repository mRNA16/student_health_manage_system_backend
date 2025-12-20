from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta, date, datetime
import numpy as np
import random
import os
import json
from SleepManage import sql
from utils.api_utils import (
    success_api_response, failed_api_response, ErrorCode, parse_data
)
from utils.cache_utils import invalidate_health_cache

class SleepRecordViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user_id = request.user.id
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        records = sql.get_sleep_records(user_id, start_date, end_date)
        return Response(success_api_response(records, message='获取成功'))

    def retrieve(self, request, pk=None):
        record = sql.get_sleep_record_by_id(pk)
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
        new_record = sql.create_sleep_record(
            user_id,
            data.get('date'),
            data.get('sleep_time'),
            data.get('wake_time')
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
            
        status_code, updated_record = sql.update_sleep_record_safe(
            pk,
            request.user.id,
            data.get('date'),
            data.get('sleep_time'),
            data.get('wake_time')
        )
        
        if status_code == 1:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "记录不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, "无权修改"))
            
        # Invalidate health cache
        invalidate_health_cache(request.user.id)
            
        return Response(success_api_response(updated_record, message='更新成功'))

    def destroy(self, request, pk=None):
        status_code = sql.delete_sleep_record_safe(pk, request.user.id)
        
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
        daily_data, monthly_data, metrics = sql.get_sleep_analysis(user_id, start_date, end_date)

        # 1. Format avgSleepMidpoint (HH:MM)
        avg_mid_hours = metrics.get('avgSleepMidpointHours')
        avgSleepMidpoint = ""
        if avg_mid_hours is not None:
            avg_mid_hours = avg_mid_hours % 24
            h = int(avg_mid_hours)
            m = int(round((avg_mid_hours - h) * 60))
            avgSleepMidpoint = f"{str(h).zfill(2)}:{str(m).zfill(2)}"

        # 2. Calculate continuous sleep deprivation (still easier in Python)
        continuous = 0
        max_continuous = 0
        for d in daily_data:
            if float(d['totalDuration']) < 5:
                continuous += 1
                max_continuous = max(max_continuous, continuous)
            else:
                continuous = 0

        return Response(success_api_response({
            'dailyData': daily_data,
            'yearlyData': monthly_data, # Frontend expects 'yearlyData' for monthly stats
            'averageTST': metrics.get('averageTST', 0),
            'stdSleepTime': metrics.get('stdSleepTime', 0),
            'stdWakeTime': metrics.get('stdWakeTime', 0),
            'stdDuration': metrics.get('stdDuration', 0),
            'avgSleepMidpoint': avgSleepMidpoint,
            'continuousSleepDeprivation': max_continuous
        }, message='分析成功'))