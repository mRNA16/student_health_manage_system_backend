from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DietManage', '0012_fix_diet_analysis_nulls'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_get_diet_analysis;
            CREATE PROCEDURE sp_get_diet_analysis(
                IN p_user_id INT,
                IN p_start_date DATE,
                IN p_end_date DATE
            )
            BEGIN
                -- Result Set 1: Daily Aggregation
                SELECT 
                    date,
                    CAST(ROUND(SUM(IF(meal='breakfast', total_calories, 0)), 1) AS DOUBLE) as breakfast,
                    CAST(ROUND(SUM(IF(meal='lunch', total_calories, 0)), 1) AS DOUBLE) as lunch,
                    CAST(ROUND(SUM(IF(meal='dinner', total_calories, 0)), 1) AS DOUBLE) as dinner,
                    CAST(ROUND(SUM(total_calories), 1) AS DOUBLE) as total
                FROM view_meal_record_full
                WHERE user_id = p_user_id
                  AND (p_start_date IS NULL OR date >= p_start_date)
                  AND (p_end_date IS NULL OR date <= p_end_date)
                GROUP BY date
                ORDER BY date;

                -- Result Set 2: Food Details per Day
                SELECT 
                    mr.date,
                    vmi.food_name as name,
                    CAST(ROUND(SUM(vmi.estimated_calories), 1) AS DOUBLE) as value
                FROM dietmanage_mealrecord mr
                JOIN view_meal_item_full vmi ON mr.id = vmi.meal_record_id
                WHERE mr.user_id = p_user_id
                  AND (p_start_date IS NULL OR mr.date >= p_start_date)
                  AND (p_end_date IS NULL OR mr.date <= p_end_date)
                GROUP BY mr.date, vmi.food_name
                ORDER BY mr.date, value DESC;

                -- Result Set 3: Monthly Aggregation
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') as month,
                    CAST(ROUND(AVG(daily_total), 1) AS DOUBLE) as avgCalories,
                    CAST(ROUND(SUM(daily_total), 1) AS DOUBLE) as totalCalories
                FROM (
                    SELECT date, SUM(total_calories) as daily_total
                    FROM view_meal_record_full
                    WHERE user_id = p_user_id
                      AND (p_start_date IS NULL OR date >= p_start_date)
                      AND (p_end_date IS NULL OR date <= p_end_date)
                    GROUP BY date
                ) t
                GROUP BY month
                ORDER BY month;

                -- Result Set 4: Core Metrics
                SELECT 
                    CAST(COALESCE(ROUND(AVG(daily_total), 1), 0) AS DOUBLE) as avgDailyCalories,
                    CAST(COALESCE(ROUND(AVG(meal_count), 2), 0) AS DOUBLE) as avgMealsPerDay
                FROM (
                    SELECT date, SUM(total_calories) as daily_total, COUNT(DISTINCT meal) as meal_count
                    FROM view_meal_record_full
                    WHERE user_id = p_user_id
                    GROUP BY date
                ) t;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_get_diet_analysis;",
        ),
    ]
