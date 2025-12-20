from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("SportManage", "0005_sport_record_native_sql"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_get_sport_analysis(
                IN p_user_id INT,
                IN p_start_date DATE,
                IN p_end_date DATE
            )
            BEGIN
                -- Result Set 1: Daily Aggregation (Basic)
                SELECT 
                    date, 
                    ROUND(SUM(calories), 1) as totalCalories,
                    ROUND(SUM(duration), 1) as totalDuration
                FROM view_sport_record_full
                WHERE user_id = p_user_id 
                  AND (p_start_date IS NULL OR date >= p_start_date)
                  AND (p_end_date IS NULL OR date <= p_end_date)
                GROUP BY date
                ORDER BY date;

                -- Result Set 2: Sport Details per Day (IDs)
                SELECT 
                    date, 
                    sport,
                    ROUND(SUM(calories), 1) as calories
                FROM view_sport_record_full
                WHERE user_id = p_user_id 
                  AND (p_start_date IS NULL OR date >= p_start_date)
                  AND (p_end_date IS NULL OR date <= p_end_date)
                GROUP BY date, sport
                ORDER BY date, calories DESC;

                -- Result Set 3: Monthly Aggregation
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') as month,
                    ROUND(AVG(daily_calories), 1) as avgCalories,
                    ROUND(SUM(daily_calories), 1) as totalCalories,
                    ROUND(AVG(daily_duration), 1) as avgDuration
                FROM (
                    SELECT date, SUM(calories) as daily_calories, SUM(duration) as daily_duration
                    FROM view_sport_record_full
                    WHERE user_id = p_user_id 
                      AND (p_start_date IS NULL OR date >= p_start_date)
                      AND (p_end_date IS NULL OR date <= p_end_date)
                    GROUP BY date
                ) daily_agg
                GROUP BY month
                ORDER BY month;

                -- Result Set 4: Core Metrics & Scores
                BEGIN
                    DECLARE v_days INT;
                    DECLARE v_avg_duration FLOAT;
                    DECLARE v_avg_calories FLOAT;
                    DECLARE v_first_date DATE;
                    DECLARE v_last_date DATE;
                    DECLARE v_time_range INT;
                    DECLARE v_active_per_week FLOAT;
                    DECLARE v_freq_score FLOAT;
                    DECLARE v_dur_score FLOAT;
                    DECLARE v_cal_score FLOAT;
                    DECLARE v_sport_score FLOAT;

                    SELECT COUNT(DISTINCT date), AVG(daily_duration), AVG(daily_calories), MIN(date), MAX(date)
                    INTO v_days, v_avg_duration, v_avg_calories, v_first_date, v_last_date
                    FROM (
                        SELECT date, SUM(duration) as daily_duration, SUM(calories) as daily_calories
                        FROM view_sport_record_full
                        WHERE user_id = p_user_id
                        GROUP BY date
                    ) t;

                    SET v_time_range = DATEDIFF(v_last_date, v_first_date) + 1;
                    IF v_time_range IS NULL OR v_time_range = 0 THEN SET v_time_range = 1; END IF;
                    
                    SET v_active_per_week = (v_days / (v_time_range / 7.0)) * 100.0;
                    SET v_freq_score = LEAST(100.0, v_active_per_week * 1.5);
                    SET v_dur_score = LEAST(100.0, COALESCE(v_avg_duration, 0) * 60.0);
                    SET v_cal_score = LEAST(100.0, COALESCE(v_avg_calories, 0) / 3.0);
                    SET v_sport_score = ROUND((v_freq_score * 0.3 + v_dur_score * 0.35 + v_cal_score * 0.35) / 10.0) * 10.0;

                    SELECT 
                        COALESCE(v_avg_duration, 0) as avgDailyDuration,
                        COALESCE(v_avg_calories, 0) as avgDailyCalories,
                        v_freq_score as frequencyScore,
                        v_dur_score as durationScore,
                        v_cal_score as calorieScore,
                        v_sport_score as sportScore;
                END;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_get_sport_analysis;",
        ),
    ]
