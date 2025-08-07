import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db.models import Q, Avg, Count
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error
import json
import logging

logger = logging.getLogger(__name__)

class HealthDataAnalyzer:
    def __init__(self, user):
        self.user = user
        
    def get_sleep_data(self, days=30):
        """获取睡眠数据"""
        from SleepManage.models.SleepRecord import SleepRecord
        from collections import defaultdict
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        sleep_records = SleepRecord.objects.filter(
            user=self.user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')

        grouped = defaultdict(list)
        for record in sleep_records:
            grouped[record.date].append(record)
        data = []
        for date, records in grouped.items():
            durations = [r.duration for r in records]
            quality_scores = [self._calculate_sleep_quality(r) for r in records]
            sleep_hours = [r.sleep_time.hour for r in records]
            wake_hours = [r.wake_time.hour for r in records]
            sleep_times = [r.sleep_time for r in records]
            wake_times = [r.wake_time for r in records]

            data.append({
                'date': date.isoformat(),
                'duration': sum(durations),
                'quality_score': np.mean(quality_scores),
                'sleep_hour': int(np.mean(sleep_hours)),
                'wake_hour': int(np.mean(wake_hours)),
                'sleep_time': min(sleep_times).isoformat(),  # 最早入睡时间
                'wake_time': max(wake_times).isoformat(),    # 最晚起床时间
            })

        return pd.DataFrame(data)
    
    def get_sport_data(self, days=30):
        """获取运动数据"""
        from SportManage.models.SportRecord import SportRecord
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        sport_records = SportRecord.objects.filter(
            user=self.user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        # 按日期聚合运动数据
        daily_sport = {}
        for record in sport_records:
            date_str = record.date.isoformat()
            if date_str not in daily_sport:
                daily_sport[date_str] = {
                    'total_duration': 0,
                    'total_calories': 0,
                    'sport_count': 0,
                    'avg_intensity': 0
                }
            daily_sport[date_str]['total_duration'] += record.duration
            daily_sport[date_str]['total_calories'] += record.calories
            daily_sport[date_str]['sport_count'] += 1
        
        # 计算平均强度
        for date_str in daily_sport:
            if daily_sport[date_str]['total_duration'] > 0:
                daily_sport[date_str]['avg_intensity'] = (
                    daily_sport[date_str]['total_calories'] / 
                    daily_sport[date_str]['total_duration']
                )
        
        return pd.DataFrame(list(daily_sport.values()), index=list(daily_sport.keys()))
    
    def get_diet_data(self, days=30):
        """获取饮食数据"""
        from DietManage.models.MealRecord import MealRecord
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        meal_records = MealRecord.objects.filter(
            user=self.user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        # 按日期聚合饮食数据
        daily_diet = {}
        for record in meal_records:
            date_str = record.date.isoformat()
            if date_str not in daily_diet:
                daily_diet[date_str] = {
                    'total_calories': 0,
                    'meal_count': 0,
                    'food_variety': set()
                }
            
            # 计算该餐的总卡路里
            meal_calories = sum(item.estimated_calories for item in record.items.all())
            daily_diet[date_str]['total_calories'] += meal_calories
            daily_diet[date_str]['meal_count'] += 1
            daily_diet[date_str]['food_variety'].update(
                item.food for item in record.items.all()
            )
        
        # 转换set为长度
        for date_str in daily_diet:
            daily_diet[date_str]['food_variety'] = len(daily_diet[date_str]['food_variety'])
        
        return pd.DataFrame(list(daily_diet.values()), index=list(daily_diet.keys()))
    
    def _calculate_sleep_quality(self, sleep_record):
        """计算睡眠质量评分 (0-100)"""
        # 基础评分：睡眠时长 (理想7-9小时)
        duration_score = 0
        if 7 <= sleep_record.duration <= 9:
            duration_score = 40
        elif 6 <= sleep_record.duration <= 10:
            duration_score = 30
        elif 5 <= sleep_record.duration <= 11:
            duration_score = 20
        else:
            duration_score = 10
        
        # 睡眠时间规律性评分 (理想22:00-23:00)
        sleep_hour = sleep_record.sleep_time.hour
        if 22 <= sleep_hour <= 23:
            regularity_score = 30
        elif 21 <= sleep_hour <= 24:
            regularity_score = 20
        elif 20 <= sleep_hour <= 1:
            regularity_score = 15
        else:
            regularity_score = 10
        
        # 起床时间规律性评分 (理想6:00-8:00)
        wake_hour = sleep_record.wake_time.hour
        if 6 <= wake_hour <= 8:
            wake_score = 30
        elif 5 <= wake_hour <= 9:
            wake_score = 20
        elif 4 <= wake_hour <= 10:
            wake_score = 15
        else:
            wake_score = 10
        
        return duration_score + regularity_score + wake_score
    
    def analyze_sleep_prediction(self, days=30):
        """基于线性回归预测睡眠质量变化"""
        try:
            sleep_df = self.get_sleep_data(days)
            if len(sleep_df) < 7:  # 至少需要7天数据
                return {
                    'success': False,
                    'message': '数据不足，至少需要7天的睡眠记录',
                    'data': None
                }
            
            # 准备特征数据
            sleep_df['date_num'] = pd.to_datetime(sleep_df['date']).dt.dayofyear
            sleep_df['day_of_week'] = pd.to_datetime(sleep_df['date']).dt.dayofweek
            
            # 创建特征矩阵
            X = sleep_df[['date_num', 'day_of_week', 'duration']].values
            y = sleep_df['quality_score'].values
            
            # 标准化特征
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 训练线性回归模型
            model = LinearRegression()
            model.fit(X_scaled, y)
            
            # 预测未来7天
            future_dates = []
            future_features = []
            last_date = pd.to_datetime(sleep_df['date'].iloc[-1])
            
            for i in range(1, 8):
                future_date = last_date + timedelta(days=i)
                future_dates.append(future_date.strftime('%Y-%m-%d'))
                future_features.append([
                    future_date.dayofyear,
                    future_date.dayofweek,
                    sleep_df['duration'].mean()  # 使用平均睡眠时长
                ])
            
            future_features = np.array(future_features)
            future_features_scaled = scaler.transform(future_features)
            predictions = model.predict(future_features_scaled)
            
            # 计算模型性能
            y_pred = model.predict(X_scaled)
            r2 = r2_score(y, y_pred)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            
            # 历史趋势
            historical_trend = {
                'dates': sleep_df['date'].tolist(),
                'quality_scores': sleep_df['quality_score'].tolist(),
                'durations': sleep_df['duration'].tolist()
            }
            
            # 预测结果
            prediction_data = {
                'dates': future_dates,
                'predicted_scores': predictions.tolist(),
                'confidence': min(0.95, max(0.5, r2))  # 基于R²的置信度
            }
            
            # 分析建议
            avg_quality = sleep_df['quality_score'].mean()
            recommendations = self._generate_sleep_recommendations(avg_quality, predictions)
            
            return {
                'success': True,
                'data': {
                    'historical_trend': historical_trend,
                    'prediction': prediction_data,
                    'model_performance': {
                        'r2_score': r2,
                        'rmse': rmse,
                        'feature_importance': {
                            'date_trend': abs(model.coef_[0]),
                            'day_of_week': abs(model.coef_[1]),
                            'duration': abs(model.coef_[2])
                        }
                    },
                    'recommendations': recommendations
                }
            }
            
        except Exception as e:
            logger.error(f"睡眠预测分析失败: {str(e)}")
            return {
                'success': False,
                'message': f'分析失败: {str(e)}',
                'data': None
            }
    
    def analyze_sleep_sport_correlation(self, days=30):
        def safe_mean(series):
            m = series.mean()
            return 0 if pd.isna(m) else m
        """分析运动时长与睡眠质量关联性"""
        try:
            sleep_df = self.get_sleep_data(days)
            sport_df = self.get_sport_data(days)
            
            if len(sleep_df) < 5 or len(sport_df) < 5:
                return {
                    'success': False,
                    'message': '数据不足，至少需要5天的睡眠和运动记录',
                    'data': None
                }
            
            # 合并数据
            sleep_df['date'] = pd.to_datetime(sleep_df['date'])
            sport_df.index = pd.to_datetime(sport_df.index)
            
            # 创建完整的时间序列
            all_dates = pd.date_range(
                start=min(sleep_df['date'].min(), sport_df.index.min()),
                end=max(sleep_df['date'].max(), sport_df.index.max()),
                freq='D'
            )
            
            # 填充缺失数据
            sleep_filled = sleep_df.set_index('date').reindex(all_dates).ffill()
            sport_filled = sport_df.reindex(all_dates).fillna(0)
            
            # 计算相关性
            correlation_data = []
            for i in range(len(all_dates)):
                if i > 0:  # 分析前一天运动对当天睡眠的影响
                    prev_sport_duration = sport_filled.iloc[i-1]['total_duration'] if i > 0 else 0
                    current_sleep_quality = sleep_filled.iloc[i]['quality_score']
                    
                    if not pd.isna(current_sleep_quality):
                        correlation_data.append({
                            'date': all_dates[i].strftime('%Y-%m-%d'),
                            'prev_sport_duration': prev_sport_duration,
                            'sleep_quality': current_sleep_quality
                        })
            
            if len(correlation_data) < 3:
                return {
                    'success': False,
                    'message': '有效数据不足，无法进行关联性分析',
                    'data': None
                }
            
            corr_df = pd.DataFrame(correlation_data)
            print(corr_df)
            
            # 计算相关系数
            correlation = corr_df['prev_sport_duration'].corr(corr_df['sleep_quality'])
            # 分组分析
            sport_groups = {
                '无运动': safe_mean(corr_df[corr_df['prev_sport_duration'] == 0]['sleep_quality']),
                '轻度运动(0-1h)': safe_mean(corr_df[(corr_df['prev_sport_duration'] > 0) & (corr_df['prev_sport_duration'] <= 1)]['sleep_quality']),
                '中度运动(1-2h)': safe_mean(corr_df[(corr_df['prev_sport_duration'] > 1) & (corr_df['prev_sport_duration'] <= 2)]['sleep_quality']),
                '重度运动(>2h)': safe_mean(corr_df[corr_df['prev_sport_duration'] > 2]['sleep_quality']),
            }
            
            # 生成建议
            recommendations = self._generate_sport_sleep_recommendations(correlation, sport_groups)
            
            return {
                'success': True,
                'data': {
                    'correlation_coefficient': correlation,
                    'correlation_strength': self._interpret_correlation(correlation),
                    'group_analysis': sport_groups,
                    'detailed_data': correlation_data,
                    'recommendations': recommendations
                }
            }
            
        except Exception as e:
            logger.error(f"运动睡眠关联性分析失败: {str(e)}")
            return {
                'success': False,
                'message': f'分析失败: {str(e)}',
                'data': None
            }
    
    def analyze_health_trends(self, days=30):
        """分析整体健康趋势"""
        try:
            sleep_df = self.get_sleep_data(days)
            sport_df = self.get_sport_data(days)
            diet_df = self.get_diet_data(days)
            
            # 计算各维度趋势
            trends = {}
            
            # 睡眠趋势
            if len(sleep_df) > 0:
                sleep_trend = self._calculate_trend(sleep_df['quality_score'])
                trends['sleep'] = {
                    'trend': sleep_trend,
                    'avg_score': sleep_df['quality_score'].mean(),
                    'improvement': bool(sleep_trend > 0)
                }
            
            # 运动趋势
            if len(sport_df) > 0:
                sport_trend = self._calculate_trend(sport_df['total_duration'])
                trends['sport'] = {
                    'trend': sport_trend,
                    'avg_duration': sport_df['total_duration'].mean(),
                    'improvement': bool(sport_trend > 0)
                }
            
            # 饮食趋势
            if len(diet_df) > 0:
                diet_trend = self._calculate_trend(diet_df['total_calories'])
                trends['diet'] = {
                    'trend': diet_trend,
                    'avg_calories': diet_df['total_calories'].mean(),
                    'improvement': bool(abs(diet_trend) < 0.1)  # 卡路里应该相对稳定
                }
            
            # 综合健康评分
            overall_score = self._calculate_overall_health_score(trends)
            
            return {
                'success': True,
                'data': {
                    'trends': trends,
                    'overall_score': overall_score,
                    'recommendations': self._generate_health_trend_recommendations(trends)
                }
            }
            
        except Exception as e:
            logger.error(f"健康趋势分析失败: {str(e)}")
            return {
                'success': False,
                'message': f'分析失败: {str(e)}',
                'data': None
            }
    
    def _calculate_trend(self, series):
        """计算趋势斜率"""
        if len(series) < 2:
            return 0
        
        x = np.arange(len(series))
        y = series.values
        slope = np.polyfit(x, y, 1)[0]
        return slope
    
    def _calculate_overall_health_score(self, trends):
        """计算综合健康评分"""
        score = 50  # 基础分
        
        if 'sleep' in trends:
            score += trends['sleep']['avg_score'] * 0.4
        if 'sport' in trends:
            # 运动时长转换为评分 (0-2小时为理想)
            sport_score = min(100, trends['sport']['avg_duration'] * 50)
            score += sport_score * 0.3
        if 'diet' in trends:
            # 饮食评分 (基于卡路里稳定性)
            diet_score = 100 - abs(trends['diet']['trend']) * 100
            score += max(0, diet_score) * 0.3
        
        return min(100, max(0, score))
    
    def _interpret_correlation(self, correlation):
        """解释相关系数强度"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.7:
            return "强相关"
        elif abs_corr >= 0.4:
            return "中等相关"
        elif abs_corr >= 0.2:
            return "弱相关"
        else:
            return "无显著相关"
    
    def _generate_sleep_recommendations(self, avg_quality, predictions):
        """生成睡眠建议"""
        recommendations = []
        
        if avg_quality < 60:
            recommendations.append("睡眠质量较低，建议：")
            recommendations.append("- 保持规律的睡眠时间，建议22:00-23:00入睡")
            recommendations.append("- 确保睡眠环境安静、黑暗、凉爽")
            recommendations.append("- 避免睡前使用电子设备")
        elif avg_quality < 80:
            recommendations.append("睡眠质量良好，可以进一步改善：")
            recommendations.append("- 尝试增加睡眠时长至7-9小时")
            recommendations.append("- 保持运动习惯，但避免睡前剧烈运动")
        else:
            recommendations.append("睡眠质量优秀，继续保持！")
        
        # 基于预测趋势的建议
        if len(predictions) > 0:
            trend = np.mean(np.diff(predictions))
            if trend < -5:
                recommendations.append("⚠️ 预测显示睡眠质量可能下降，建议及时调整作息")
            elif trend > 5:
                recommendations.append("✅ 预测显示睡眠质量将改善，继续保持良好习惯")
        
        return recommendations
    
    def _generate_sport_sleep_recommendations(self, correlation, sport_groups):
        """生成运动睡眠关联性建议"""
        recommendations = []
        
        if correlation > 0.3:
            recommendations.append("✅ 运动与睡眠质量呈正相关，建议：")
            recommendations.append("- 保持规律运动习惯")
            recommendations.append("- 选择中等强度运动，避免睡前剧烈运动")
        elif correlation < -0.3:
            recommendations.append("⚠️ 运动可能影响睡眠质量，建议：")
            recommendations.append("- 避免睡前2小时内剧烈运动")
            recommendations.append("- 选择瑜伽、散步等轻度运动")
        else:
            recommendations.append("运动与睡眠质量关联性不强，建议：")
            recommendations.append("- 根据个人情况调整运动时间")
            recommendations.append("- 观察运动对睡眠的具体影响")
        
        # 基于分组分析的建议
        best_group = max(sport_groups.items(), key=lambda x: x[1] if not pd.isna(x[1]) else 0)
        recommendations.append(f"最佳运动时长：{best_group[0]} (平均睡眠质量: {best_group[1]:.1f})")
        
        return recommendations
    
    def _generate_health_trend_recommendations(self, trends):
        """生成健康趋势建议"""
        recommendations = []
        
        for dimension, trend_data in trends.items():
            if dimension == 'sleep' and not trend_data['improvement']:
                recommendations.append("睡眠质量呈下降趋势，建议调整作息时间")
            elif dimension == 'sport' and not trend_data['improvement']:
                recommendations.append("运动量呈下降趋势，建议增加运动频率")
            elif dimension == 'diet' and not trend_data['improvement']:
                recommendations.append("饮食不够规律，建议保持均衡饮食")
        
        if not recommendations:
            recommendations.append("整体健康趋势良好，继续保持！")
        
        return recommendations 