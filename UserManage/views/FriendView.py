from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.timezone import localtime
from django.core.cache import cache
import os
import json
from utils.api_utils import (
    success_api_response, failed_api_response, ErrorCode, parse_data
)
from UserManage import sql
from utils.cache_utils import invalidate_friend_cache, invalidate_friend_feed_cache

class FriendViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user_id = request.user.id
        cache_key = f'friend_list_all_{user_id}'
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(success_api_response(cached_data, message='获取好友数据成功 (from cache)'))
            
        friends_data = sql.get_user_friends_all(user_id)
        cache.set(cache_key, friends_data, timeout=3600)
        
        return Response(success_api_response(friends_data, message='获取好友数据成功'))

    def retrieve(self, request, pk=None):
        # pk is friend_id (User ID of the friend)
        friend_id = pk
        user_id = request.user.id
        
        # 1. Security Check: Are they friends? 
        # We can use the cached friend list for this to avoid DB hit
        friend_list_cache_key = f'friend_list_{user_id}'
        friends = cache.get(friend_list_cache_key)
        if friends is None:
            friends = sql.get_friend_requests(user_id, direction='both', status='accepted')
            cache.set(friend_list_cache_key, friends, timeout=3600)
        
        is_friend = any(str(f['from_user_id']) == str(friend_id) or str(f['to_user_id']) == str(friend_id) for f in friends)
        
        if not is_friend and str(user_id) != str(friend_id):
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, "无权查看该用户动态"))

        # 2. Cache Check for activities
        cache_key = f'friend_activities_feed_{friend_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(success_api_response(cached_data, message='获取好友详情成功 (from cache)'))

        # 3. DB Fetch (if cache miss)
        status_code, friend_user, raw_activities = sql.get_friend_activities_safe(user_id, friend_id)
        
        if status_code == 1:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "用户不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, "无权查看该用户动态"))

        # Process activities (mapping sport names, etc.)
        activities = []
        
        # Load MET data for sport mapping
        met_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'SportManage', 'met.json')
        try:
            with open(met_path, 'r', encoding='utf-8') as f:
                mets = json.load(f)
        except Exception:
            mets = {}
            
        for record in raw_activities:
            act_type = record['type']
            timestamp = record['created_at'].isoformat() if hasattr(record['created_at'], 'isoformat') else str(record['created_at'])
            
            content = ""
            if act_type == 'sport':
                sport_key = str(record['detail'])
                sport_info = mets[int(sport_key)] if sport_key.isdigit() else None
                sport_name = sport_info['name'] if sport_info else "未知运动"
                duration_min = round(float(record['duration'] or 0) * 60)
                content = f"进行了{sport_name}，持续{duration_min}分钟"
            elif act_type == 'sleep':
                duration_hours = round(float(record['duration'] or 0), 1)
                content = f"睡眠了{duration_hours}小时"
            elif act_type == 'meal':
                meal_names = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐', 'extra': '加餐'}
                meal_name = meal_names.get(record['detail'], record['detail'])
                calories = round(float(record['duration'] or 0))
                content = f"记录了{meal_name}，摄入约{calories}卡路里"
                
            activities.append({
                'id': record['id'],
                'type': act_type,
                'content': content,
                'timestamp': timestamp
            })
        
        response_data = {
            'friendId': friend_id,
            'friendName': friend_user['username'],
            'activities': activities
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, response_data, timeout=600)
        
        return Response(success_api_response(response_data, message='获取好友详情成功'))

    @action(detail=False, methods=['get'])
    def friends(self, request):
        # Accepted friends
        user_id = request.user.id
        cache_key = f'friend_list_{user_id}'
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(success_api_response(cached_data, message='获取好友列表成功 (from cache)'))
            
        friends = sql.get_friend_requests(user_id, direction='both', status='accepted')
        cache.set(cache_key, friends, timeout=3600)
        
        return Response(success_api_response(friends, message='获取好友列表成功'))

    @action(detail=False, methods=['get'])
    def received_requests(self, request):
        user_id = request.user.id
        cache_key = f'friend_requests_received_{user_id}'
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(success_api_response(cached_data, message='获取收到的好友请求成功 (from cache)'))
            
        requests = sql.get_friend_requests_v2(user_id, direction='received')
        cache.set(cache_key, requests, timeout=3600)
        
        return Response(success_api_response(requests, message='获取收到的好友请求成功'))

    @action(detail=False, methods=['get'])
    def sent_requests(self, request):
        user_id = request.user.id
        cache_key = f'friend_requests_sent_{user_id}'
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(success_api_response(cached_data, message='获取发送的好友请求成功 (from cache)'))
            
        requests = sql.get_friend_requests_v2(user_id, direction='sent')
        cache.set(cache_key, requests, timeout=3600)
        
        return Response(success_api_response(requests, message='获取发送的好友请求成功'))

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        status_code = sql.handle_friend_request_safe(pk, request.user.id, 'accept')
        
        if status_code == 1:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "请求不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, '无权接受此请求'))

        # Invalidate cache for both users
        friend_rel = sql.get_friend_relationship(pk)
        if friend_rel:
            invalidate_friend_cache(friend_rel['from_user_id'])
            invalidate_friend_cache(friend_rel['to_user_id'])
            cache.delete(f'friend_list_all_{friend_rel["from_user_id"]}')
            cache.delete(f'friend_list_all_{friend_rel["to_user_id"]}')
            # Also invalidate feed cache just in case
            invalidate_friend_feed_cache(friend_rel['from_user_id'])
            invalidate_friend_feed_cache(friend_rel['to_user_id'])

        return Response(success_api_response(None, message='接受好友请求成功'))

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        status_code = sql.handle_friend_request_safe(pk, request.user.id, 'reject')
        
        if status_code == 1:
             return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "请求不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, '无权拒绝此请求'))

        # Invalidate cache
        friend_rel = sql.get_friend_relationship(pk)
        if friend_rel:
            invalidate_friend_cache(friend_rel['from_user_id'])
            invalidate_friend_cache(friend_rel['to_user_id'])

        return Response(success_api_response(None, message='拒绝好友请求成功'))

    @action(detail=False, methods=['post'])
    def send(self, request):
        data = parse_data(request)
        to_user_id = data.get('to_user')
        if not to_user_id:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS, '缺少 to_user_id'))

        status_code, new_request = sql.send_friend_request_safe(request.user.id, to_user_id)
        
        if status_code == 1:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS, '不能添加自己为好友'))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS, '已存在好友关系或请求'))

        # Invalidate cache
        invalidate_friend_cache(request.user.id)
        invalidate_friend_cache(to_user_id)

        return Response(success_api_response(new_request, message='好友请求已发送'))

    @action(detail=True, methods=['delete'])
    def cancel(self, request, pk=None):
        # Get relationship info before deletion for cache invalidation
        friend_rel = sql.get_friend_relationship(pk)
        
        status_code = sql.cancel_friend_request_safe(pk, request.user.id)
        
        if status_code == 1:
             return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "请求不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, '无权取消该请求'))
        elif status_code == 3:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, '只有待处理的请求才能取消'))

        # Invalidate cache
        if friend_rel:
            invalidate_friend_cache(friend_rel['from_user_id'])
            invalidate_friend_cache(friend_rel['to_user_id'])

        return Response(success_api_response(None, message='取消好友请求成功'))

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        # Get relationship info before deletion for cache invalidation
        friend_rel = sql.get_friend_relationship(pk)
        
        status_code = sql.remove_friend_relationship_safe(pk, request.user.id)

        if status_code == 1:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "请求不存在"))
        elif status_code == 2:
            return Response(failed_api_response(ErrorCode.REFUSE_ACCESS_ERROR, '无权删除该请求'))

        # Invalidate cache
        if friend_rel:
            invalidate_friend_cache(friend_rel['from_user_id'])
            invalidate_friend_cache(friend_rel['to_user_id'])
            cache.delete(f'friend_list_all_{friend_rel["from_user_id"]}')
            cache.delete(f'friend_list_all_{friend_rel["to_user_id"]}')
            # Also invalidate feed cache
            invalidate_friend_feed_cache(friend_rel['from_user_id'])
            invalidate_friend_feed_cache(friend_rel['to_user_id'])

        return Response(success_api_response(None, message='删除好友请求成功'))