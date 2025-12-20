from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("SleepManage", "0013_cast_duration_to_double"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_get_sleep_analysis(
                IN p_user_id INT,
                IN p_start_date DATE,
                IN p_end_date DATE
            )
            BEGIN
                -- Result Set 1: Daily Aggregation
                SELECT 
                    date, 
                    ROUND(SUM(duration), 1) as totalDuration
                FROM view_sleep_record_full
                WHERE user_id = p_user_id 
                  AND (p_start_date IS NULL OR date >= p_start_date)
                  AND (p_end_date IS NULL OR date <= p_end_date)
                GROUP BY date
                ORDER BY date;

                -- Result Set 2: Monthly Aggregation
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') as month,
                    ROUND(AVG(daily_total), 1) as avgDuration,
                    ROUND(SUM(daily_total), 1) as totalDuration
                FROM (
                    SELECT date, SUM(duration) as daily_total
                    FROM view_sleep_record_full
                    WHERE user_id = p_user_id 
                      AND (p_start_date IS NULL OR date >= p_start_date)
                      AND (p_end_date IS NULL OR date <= p_end_date)
                    GROUP BY date
                ) daily_agg
                GROUP BY month
                ORDER BY month;

                -- Result Set 3: Core Metrics
                SELECT 
                    ROUND(AVG(duration), 1) as averageTST,
                    ROUND(STDDEV_POP(duration), 2) as stdDuration,
                    ROUND(STDDEV_POP(TIME_TO_SEC(sleep_time)/3600.0), 2) as stdSleepTime,
                    ROUND(STDDEV_POP(TIME_TO_SEC(wake_time)/3600.0), 2) as stdWakeTime,
                    AVG((TIME_TO_SEC(sleep_time)/3600.0 + duration/2.0)) as avgSleepMidpointHours
                FROM view_sleep_record_full
                WHERE user_id = p_user_id 
                  AND (p_start_date IS NULL OR date >= p_start_date)
                  AND (p_end_date IS NULL OR date <= p_end_date);
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_get_sleep_analysis;",
        ),
    ]
