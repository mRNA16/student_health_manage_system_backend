from django.db import connection

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def get_comprehensive_health_data(user_id, days=30):
    sql = """
        SELECT * FROM view_health_data_comprehensive 
        WHERE user_id = %s 
          AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY date ASC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id, days])
        return dictfetchall(cursor)

def get_sleep_data_for_analysis(user_id, days=30):
    sql = """
        SELECT 
            date,
            sleep_duration as duration,
            sleep_quality_score as quality_score,
            avg_sleep_hour as sleep_hour,
            avg_wake_hour as wake_hour,
            earliest_sleep_time as sleep_time,
            latest_wake_time as wake_time
        FROM view_health_data_comprehensive
        WHERE user_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        AND sleep_duration > 0
        ORDER BY date ASC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id, days])
        return dictfetchall(cursor)

def get_sport_data_for_analysis(user_id, days=30):
    sql = """
        SELECT 
            date,
            sport_duration as total_duration,
            sport_calories as total_calories,
            sport_count
        FROM view_health_data_comprehensive
        WHERE user_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        AND sport_duration > 0
        ORDER BY date ASC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id, days])
        return dictfetchall(cursor)

def get_diet_data_for_analysis(user_id, days=30):
    sql = """
        SELECT 
            date,
            diet_calories as total_calories,
            meal_count,
            food_variety
        FROM view_health_data_comprehensive
        WHERE user_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        AND meal_count > 0
        ORDER BY date ASC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id, days])
        return dictfetchall(cursor)
