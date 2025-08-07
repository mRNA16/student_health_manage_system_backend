from django import utils
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from ..services.HealthDataAnalyzer import HealthDataAnalyzer
from ..serializers.AnalysisSerializer import AnalysisRequestSerializer, AnalysisResultSerializer
from ..models.AnalysisResult import AnalysisResult
from utils.response import api_response
import json
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_health_data(request):
    """健康数据分析接口"""
    try:
        serializer = AnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                code=400,
                message='参数错误',
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        analysis_type = serializer.validated_data['analysis_type']
        time_range = serializer.validated_data.get('time_range', '30d')
        include_predictions = serializer.validated_data.get('include_predictions', True)
        
        # 转换时间范围
        days_map = {'7d': 7, '30d': 30, '90d': 90}
        days = days_map.get(time_range, 30)
        
        # 创建分析器
        analyzer = HealthDataAnalyzer(request.user)
        
        # 根据分析类型执行相应的分析
        if analysis_type == 'sleep_prediction':
            result = analyzer.analyze_sleep_prediction(days)
        elif analysis_type == 'sleep_sport_correlation':
            result = analyzer.analyze_sleep_sport_correlation(days)
        elif analysis_type == 'health_trend':
            result = analyzer.analyze_health_trends(days)
        else:
            return api_response(
                code=400,
                message='不支持的分析类型',
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if result['success']:
            # 保存分析结果
            analysis_result, created = AnalysisResult.objects.update_or_create(
                user=request.user,
                analysis_type=analysis_type,
                defaults={'result_data': result['data']}
            )
            
            return api_response(
                message='分析成功',
                data={
                    'data': result['data'],
                    'analysis_id': analysis_result.id,
                    'success': True
                },
                code=0
            )
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"健康数据分析失败: {str(e)}")
        return api_response(
            code=500,
            message=f'分析失败: {str(e)}',
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_results(request):
    """获取分析结果列表"""
    try:
        analysis_type = request.GET.get('analysis_type')
        limit = int(request.GET.get('limit', 10))
        
        queryset = AnalysisResult.objects.filter(user=request.user)
        if analysis_type:
            queryset = queryset.filter(analysis_type=analysis_type)
        
        queryset = queryset.order_by('-created_at')[:limit]
        
        serializer = AnalysisResultSerializer(queryset, many=True)
        
        return api_response(
            message='获取成功',
            data={
                'data':serializer.data,
                'success':True,
            },
            code=0
        )
        
    except Exception as e:
        logger.error(f"获取分析结果失败: {str(e)}")
        return api_response(
            code=500,
            message=f'获取失败: {str(e)}',
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_detail(request, analysis_id):
    """获取分析结果详情"""
    try:
        analysis_result = AnalysisResult.objects.get(
            id=analysis_id,
            user=request.user
        )
        
        serializer = AnalysisResultSerializer(analysis_result)
        
        return api_response(
            message='获取成功',
            data={
                'data':serializer.data,
                'success':True,
            },
            code=0
        )
        
    except AnalysisResult.DoesNotExist:
        return api_response(
            code=404,
            message='分析结果不存在',
            data=None,
            status_code=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"获取分析详情失败: {str(e)}")
        return api_response(
            code=500,
            message=f'获取失败: {str(e)}',
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_health_summary(request):
    """获取健康数据摘要"""
    try:
        time_range = request.GET.get('time_range', '30d')
        days_map = {'7d': 7, '30d': 30, '90d': 90}
        days = days_map.get(time_range, 30)
        
        analyzer = HealthDataAnalyzer(request.user)
        
        # 获取各维度数据
        sleep_df = analyzer.get_sleep_data(days)
        sport_df = analyzer.get_sport_data(days)
        diet_df = analyzer.get_diet_data(days)
        
        summary = {
            'sleep': {
                'total_records': len(sleep_df),
                'avg_quality': sleep_df['quality_score'].mean() if len(sleep_df) > 0 else 0,
                'avg_duration': sleep_df['duration'].mean() if len(sleep_df) > 0 else 0,
                'best_day': sleep_df.loc[sleep_df['quality_score'].idxmax()]['date'] if len(sleep_df) > 0 else None
            },
            'sport': {
                'total_records': len(sport_df),
                'avg_duration': sport_df['total_duration'].mean() if len(sport_df) > 0 else 0,
                'total_calories': sport_df['total_calories'].sum() if len(sport_df) > 0 else 0,
                'active_days': len(sport_df[sport_df['total_duration'] > 0])
            },
            'diet': {
                'total_records': len(diet_df),
                'avg_calories': diet_df['total_calories'].mean() if len(diet_df) > 0 else 0,
                'avg_meals': diet_df['meal_count'].mean() if len(diet_df) > 0 else 0,
                'avg_variety': diet_df['food_variety'].mean() if len(diet_df) > 0 else 0
            }
        }
        
        # 计算综合健康评分
        overall_score = 0
        if summary['sleep']['avg_quality'] > 0:
            overall_score += summary['sleep']['avg_quality'] * 0.4
        if summary['sport']['avg_duration'] > 0:
            sport_score = min(100, summary['sport']['avg_duration'] * 50)
            overall_score += sport_score * 0.3
        if summary['diet']['avg_calories'] > 0:
            diet_score = 100 - abs(summary['diet']['avg_calories'] - 2000) / 20  # 假设理想卡路里为2000
            overall_score += max(0, diet_score) * 0.3
        
        summary['overall_score'] = min(100, max(0, overall_score))
        
        return api_response(
            message='获取成功',
            data={
                'data':summary,
                'success':True,
            },
            code=0
        )
        
    except Exception as e:
        logger.error(f"获取健康摘要失败: {str(e)}")
        return api_response(
            code=500,
            message=f'获取失败: {str(e)}',
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_analysis_result(request, analysis_id):
    """删除分析结果"""
    try:
        analysis_result = AnalysisResult.objects.get(
            id=analysis_id,
            user=request.user
        )
        analysis_result.delete()
        
        return api_response(
            message='删除成功',
            data={
                'data':None,
                'success':True,
            },
            code=0
        )
        
    except AnalysisResult.DoesNotExist:
        return api_response(
            code=404,
            message='分析结果不存在',
            data=None,
            status_code=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"删除分析结果失败: {str(e)}")
        return api_response(
            code=500,
            message=f'删除失败: {str(e)}',
            data=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )