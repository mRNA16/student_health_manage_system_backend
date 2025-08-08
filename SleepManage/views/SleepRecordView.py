from rest_framework import viewsets, permissions,status
from rest_framework.decorators import action
from SleepManage.models.SleepRecord import SleepRecord
from SleepManage.serializers.SleepRecordSerializer import SleepRecordSerializer
from datetime import timedelta, date, datetime
from rest_framework.response import Response
import numpy as np

class SleepRecordViewSet(viewsets.ModelViewSet):
    serializer_class = SleepRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = SleepRecord.objects.filter(user=user)
        # start_date = self.request.query_params.get('start_date')
        # end_date = self.request.query_params.get('end_date')
        # if start_date and end_date:
            # qs = qs.filter(date__range=[start_date, end_date])
        return qs

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

    @action(detail=False, methods=['get'], url_path='analysis')
    def analysis(self, request):
        user = request.user
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        qs = SleepRecord.objects.filter(user=user)
        if start_date and end_date:
            qs = qs.filter(date__range=[start_date, end_date])
        records = list(qs.order_by('date').values('date', 'sleep_time', 'wake_time', 'duration'))

        # 健康标准
        HEALTHY_SLEEP_DURATION = 7
        HEALTHY_BEDTIME = 23.5
        HEALTHY_WAKETIME = 6.5
        DEPRIVATION_THRESHOLD = 5
        CONTINUOUS_DAYS_THRESHOLD = 4

        # 日聚合
        daily_map = {}
        for r in records:
            date_str = r['date'].strftime('%Y-%m-%d')
            daily_map.setdefault(date_str, 0)
            daily_map[date_str] += r['duration']
        daily_data = [{'date': k, 'totalDuration': round(v, 1)} for k, v in daily_map.items()]
        daily_data.sort(key=lambda x: x['date'])

        # 月聚合
        monthly_map = {}
        for item in daily_data:
            month = item['date'][:7]
            monthly_map.setdefault(month, {'total': 0, 'days': 0})
            monthly_map[month]['total'] += item['totalDuration']
            monthly_map[month]['days'] += 1
        yearly_data = [
            {
                'date': month,
                'avgDuration': round(data['total'] / data['days'], 1),
                'totalDuration': round(data['total'], 1)
            }
            for month, data in monthly_map.items()
        ]
        yearly_data.sort(key=lambda x: x['date'])

        # 睡眠核心指标
        durations = [r['duration'] for r in records if r['duration'] is not None]
        averageTST = round(np.mean(durations), 1) if durations else 0
        stdDuration = round(np.std(durations), 2) if durations else 0

        # 入睡/起床时间转小时
        def time_to_hours(t):
            if isinstance(t, str):
                h, m, *_ = map(int, t.split(':'))
            else:
                h, m = t.hour, t.minute
            return h + m / 60

        sleep_times = [time_to_hours(r['sleep_time']) for r in records if r['sleep_time']]
        wake_times = [time_to_hours(r['wake_time']) for r in records if r['wake_time']]
        stdSleepTime = round(np.std(sleep_times), 2) if sleep_times else 0
        stdWakeTime = round(np.std(wake_times), 2) if wake_times else 0

        # 平均睡眠中点
        midpoints = []
        for i, r in enumerate(records):
            st = time_to_hours(r['sleep_time'])
            dur = r['duration'] if r['duration'] else 0
            mid = (st + dur / 2) % 24
            midpoints.append(mid)
        if midpoints:
            avg_mid = np.mean(midpoints)
            midpoint_hours = int(avg_mid)
            midpoint_minutes = int(round((avg_mid - midpoint_hours) * 60))
            avgSleepMidpoint = f"{str(midpoint_hours).zfill(2)}:{str(midpoint_minutes).zfill(2)}"
        else:
            avgSleepMidpoint = ""

        # 连续睡眠不足天数
        continuous = 0
        max_continuous = 0
        for d in daily_data:
            if d['totalDuration'] < DEPRIVATION_THRESHOLD:
                continuous += 1
                max_continuous = max(max_continuous, continuous)
            else:
                continuous = 0

        # 睡眠问题标签
        sleepIssues = []
        if averageTST < HEALTHY_SLEEP_DURATION:
            sleepIssues.append(f"睡眠时长不足（平均{averageTST:.1f}小时，建议至少7小时）")
        if stdSleepTime > 1.5:
            sleepIssues.append("入睡时间不规律（波动较大）")
        if stdWakeTime > 1.5:
            sleepIssues.append("起床时间不规律（波动较大）")
        if stdDuration > 1.5:
            sleepIssues.append("睡眠时长不稳定（可能存在睡眠中断）")
        if records:
            latest = records[-1]
            if time_to_hours(latest['sleep_time']) > HEALTHY_BEDTIME:
                sleepIssues.append("入睡时间较晚（建议不晚于23:30）")
            if time_to_hours(latest['wake_time']) < HEALTHY_WAKETIME:
                sleepIssues.append("起床时间较早（建议不早于06:00）")

        # 核心建议
        coreAdvice = [
            "1. 锚定起床时间：每天固定同一时间起床。",
            "2. 循序渐进调整：每天提前15分钟入睡。",
            "3. 建立睡前仪式：睡前1小时进行放松活动。"
        ]

        # 针对性建议
        specificAdvice = []
        if max_continuous >= CONTINUOUS_DAYS_THRESHOLD:
            specificAdvice.append(f"• 紧急调整：未来2天尽量保证至少{HEALTHY_SLEEP_DURATION}小时睡眠。")
        if averageTST < HEALTHY_SLEEP_DURATION:
            specificAdvice.append("• 逐步提前入睡时间，每次15分钟，直至达到目标睡眠时长。")
        if stdSleepTime > 1.5 or stdWakeTime > 1.5:
            specificAdvice.append("• 设置“睡前提醒”闹钟，提前1小时准备入睡。")
        if stdDuration > 1.5:
            specificAdvice.append("• 优化睡眠环境，避免夜间易醒。")
        if records and time_to_hours(records[-1]['sleep_time']) > HEALTHY_BEDTIME:
            specificAdvice.append("• 睡前1小时远离电子设备。")
        if not specificAdvice:
            specificAdvice.append("• 保持规律进餐和适度运动。")

        # 睡眠小贴士（随机3条）
        import random
        allTips = [
            "• 试试“478呼吸法”：吸气4秒→屏息7秒→呼气8秒。",
            "• 白天晒10-15分钟太阳，有助于调节生物钟。",
            "• 卧室可放薰衣草，有助于放松入睡。",
            "• 夜间醒来不要看时间，闭眼深呼吸。",
            "• 选择舒适寝具，提升睡眠质量。"
        ]
        sleepTips = random.sample(allTips, 3) if len(allTips) >= 3 else allTips

        return Response({
            'code': 0,
            'message': '分析成功',
            'data': {
                'dailyData': daily_data,
                'yearlyData': yearly_data,
                'averageTST': averageTST,
                'stdSleepTime': stdSleepTime,
                'stdWakeTime': stdWakeTime,
                'stdDuration': stdDuration,
                'avgSleepMidpoint': avgSleepMidpoint,
                'continuousSleepDeprivation': max_continuous,
                'sleepIssues': sleepIssues,
                'coreAdvice': coreAdvice,
                'specificAdvice': specificAdvice,
                'sleepTips': sleepTips,
                'HEALTHY_SLEEP_DURATION': HEALTHY_SLEEP_DURATION,
                'HEALTHY_BEDTIME': HEALTHY_BEDTIME,
                'HEALTHY_WAKETIME': HEALTHY_WAKETIME,
                'DEPRIVATION_THRESHOLD': DEPRIVATION_THRESHOLD,
                'CONTINUOUS_DAYS_THRESHOLD': CONTINUOUS_DAYS_THRESHOLD,
            }
        }, status=status.HTTP_200_OK)