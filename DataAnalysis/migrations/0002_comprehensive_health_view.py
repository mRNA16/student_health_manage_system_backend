from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('DataAnalysis', '0001_initial'),
        ('SleepManage', '0014_sleep_analysis_procedure'),
        ('SportManage', '0006_sport_analysis_procedure'),
        ('DietManage', '0014_fix_meal_record_delete_cascade'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE VIEW view_health_data_comprehensive AS
            WITH daily_sleep AS (
                SELECT 
                    user_id, 
                    date, 
                    SUM(duration) as total_duration,
                    AVG(
                        CASE 
                            WHEN duration BETWEEN 7 AND 9 THEN 40
                            WHEN duration BETWEEN 6 AND 10 THEN 30
                            WHEN duration BETWEEN 5 AND 11 THEN 20
                            ELSE 10
                        END +
                        CASE 
                            WHEN HOUR(sleep_time) BETWEEN 22 AND 23 THEN 30
                            WHEN HOUR(sleep_time) = 21 OR HOUR(sleep_time) = 0 THEN 20
                            WHEN HOUR(sleep_time) = 20 OR HOUR(sleep_time) = 1 THEN 15
                            ELSE 10
                        END +
                        CASE 
                            WHEN HOUR(wake_time) BETWEEN 6 AND 8 THEN 30
                            WHEN HOUR(wake_time) = 5 OR HOUR(wake_time) = 9 THEN 20
                            WHEN HOUR(wake_time) = 4 OR HOUR(wake_time) = 10 THEN 15
                            ELSE 10
                        END
                    ) as avg_quality_score,
                    AVG(HOUR(sleep_time)) as avg_sleep_hour,
                    AVG(HOUR(wake_time)) as avg_wake_hour,
                    MIN(sleep_time) as earliest_sleep_time,
                    MAX(wake_time) as latest_wake_time
                FROM view_sleep_record_full
                GROUP BY user_id, date
            ),
            daily_sport AS (
                SELECT 
                    user_id, 
                    date, 
                    SUM(duration) as total_duration,
                    SUM(calories) as total_calories,
                    COUNT(*) as sport_count
                FROM view_sport_record_full
                GROUP BY user_id, date
            ),
            daily_diet AS (
                SELECT 
                    user_id, 
                    date, 
                    SUM(total_calories) as total_calories,
                    COUNT(*) as meal_count,
                    COUNT(DISTINCT food_id) as food_variety
                FROM view_meal_record_full vmr
                LEFT JOIN dietmanage_mealitem mi ON vmr.id = mi.meal_record_id
                GROUP BY user_id, date
            ),
            all_dates AS (
                SELECT DISTINCT user_id, date FROM (
                    SELECT user_id, date FROM sleepmanage_sleeprecord
                    UNION SELECT user_id, date FROM sportmanage_sportrecord
                    UNION SELECT user_id, date FROM dietmanage_mealrecord
                ) t
            )
            SELECT 
                ad.user_id,
                ad.date,
                CAST(COALESCE(ds.total_duration, 0) AS DOUBLE) as sleep_duration,
                CAST(COALESCE(ds.avg_quality_score, 0) AS DOUBLE) as sleep_quality_score,
                CAST(COALESCE(ds.avg_sleep_hour, 0) AS DOUBLE) as avg_sleep_hour,
                CAST(COALESCE(ds.avg_wake_hour, 0) AS DOUBLE) as avg_wake_hour,
                ds.earliest_sleep_time,
                ds.latest_wake_time,
                CAST(COALESCE(dsp.total_duration, 0) AS DOUBLE) as sport_duration,
                CAST(COALESCE(dsp.total_calories, 0) AS DOUBLE) as sport_calories,
                CAST(COALESCE(dsp.sport_count, 0) AS DOUBLE) as sport_count,
                CAST(COALESCE(dd.total_calories, 0) AS DOUBLE) as diet_calories,
                CAST(COALESCE(dd.meal_count, 0) AS DOUBLE) as meal_count,
                CAST(COALESCE(dd.food_variety, 0) AS DOUBLE) as food_variety
            FROM all_dates ad
            LEFT JOIN daily_sleep ds ON ad.user_id = ds.user_id AND ad.date = ds.date
            LEFT JOIN daily_sport dsp ON ad.user_id = dsp.user_id AND ad.date = dsp.date
            LEFT JOIN daily_diet dd ON ad.user_id = dd.user_id AND ad.date = dd.date;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_health_data_comprehensive;"
        )
    ]
