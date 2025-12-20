from django.contrib.auth.hashers import make_password
from rest_framework import permissions, viewsets
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from django.core.cache import cache

from utils.api_utils import (
    success_api_response, failed_api_response, ErrorCode, parse_data, response_wrapper
)
from UserManage import sql

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return Response(success_api_response(response.data))
        except Exception as e:
            return Response(failed_api_response(ErrorCode.UNAUTHORIZED_ERROR, str(e)))

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = parse_data(request)
        if not data:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS, "Invalid JSON"))
        
        username = data.get('username')
        password = data.get('password')
        profile_data = data.get('profile', {})

        if not username or not password:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS, "Username and password required"))

        if sql.get_user_by_username(username):
            return Response(failed_api_response(ErrorCode.DUPLICATED_ERROR, "Username already exists"))


        hashed_password = make_password(password)

        try:
            user_id = sql.create_user(username, hashed_password, profile_data)
            return_data = {
                'username': username,
                'profile': profile_data
            }
            return Response(success_api_response(return_data, message='注册成功'))
        except Exception as e:
            return Response(failed_api_response(ErrorCode.SERVER_ERROR, str(e)))

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        cache_key = f'user_profile_{user_id}'
        
        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(success_api_response(cached_data, message='获取成功 (from cache)'))

        user_data = sql.get_user_by_id(user_id)
        if not user_data:
            return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR, "User not found"))

        profile_fields = [
            'height', 'weight', 'gender', 'birthday', 'realName', 'roles',
            'daily_calories_burn_goal', 'daily_calories_intake_goal', 'daily_sleep_hours_goal'
        ]
        response_data = {k: user_data[k] for k in profile_fields if k in user_data}
        
        # Set to cache
        cache.set(cache_key, response_data, timeout=3600)
        
        return Response(success_api_response(response_data, message='获取成功'))

    def put(self, request):
        return self.update_profile(request)

    def patch(self, request):
        return self.update_profile(request)

    def update_profile(self, request):
        user_id = request.user.id
        data = parse_data(request)
        if not data:
            return Response(failed_api_response(ErrorCode.INVALID_REQUEST_ARGS))

        try:
            sql.update_user_profile(user_id, data)
            
            # Invalidate cache
            cache.delete(f'user_profile_{user_id}')
            
            user_data = sql.get_user_by_id(user_id)
            profile_fields = [
                'height', 'weight', 'gender', 'birthday', 'realName', 'roles',
                'daily_calories_burn_goal', 'daily_calories_intake_goal', 'daily_sleep_hours_goal'
            ]
            response_data = {k: user_data[k] for k in profile_fields if k in user_data}
            return Response(success_api_response(response_data, message='更新成功'))
        except Exception as e:
            return Response(failed_api_response(ErrorCode.SERVER_ERROR, str(e)))

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        return Response(success_api_response(None, message="已注销"))
    
class CodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response(success_api_response([], message="成功"))

class UserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        search_query = request.query_params.get('search')
        
        try:
            users_data = sql.search_users(search_query)
            return Response(success_api_response(users_data, message="获取成功"))
        except Exception as e:
            return Response(failed_api_response(ErrorCode.SERVER_ERROR, str(e)))

    def retrieve(self, request, pk=None):
        user = request.user
        user_data = sql.get_user_by_id(user.id)
        if user_data:
            profile_fields = [
                'height', 'weight', 'gender', 'birthday', 'realName', 'roles',
                'daily_calories_burn_goal', 'daily_calories_intake_goal', 'daily_sleep_hours_goal'
            ]
            nested_data = {
                'id': user_data['id'],
                'username': user_data['username'],
                'profile': {k: user_data[k] for k in profile_fields if k in user_data}
            }
            return Response(success_api_response(nested_data, message='获取成功'))
            
        return Response(failed_api_response(ErrorCode.NOT_FOUND_ERROR))