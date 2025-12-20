from django.db import connection

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def get_sleep_records(user_id, start_date=None, end_date=None):
    sql = "SELECT * FROM view_sleep_record_full WHERE user_id = %s"
    params = [user_id]
    
    if start_date and end_date:
        sql += " AND date BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    
    sql += " ORDER BY date DESC, sleep_time DESC"
    
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return dictfetchall(cursor)

def get_sleep_record_by_id(record_id):
    sql = "SELECT * FROM view_sleep_record_full WHERE id = %s"
    with connection.cursor() as cursor:
        cursor.execute(sql, [record_id])
        rows = dictfetchall(cursor)
        return rows[0] if rows else None

def create_sleep_record(user_id, date, sleep_time, wake_time):
    with connection.cursor() as cursor:
        cursor.callproc('sp_create_sleep_record', [user_id, date, sleep_time, wake_time])
        rows = dictfetchall(cursor)
        return rows[0] if rows else None

def update_sleep_record_safe(record_id, user_id, date, sleep_time, wake_time):
    with connection.cursor() as cursor:
        cursor.callproc('sp_update_sleep_record_safe', [record_id, user_id, date, sleep_time, wake_time])
        # First result set: status_code
        status_row = cursor.fetchone()
        status_code = status_row[0] if status_row else 1
        
        updated_record = None
        if status_code == 0 and cursor.nextset():
            # Second result set: updated record
            rows = dictfetchall(cursor)
            updated_record = rows[0] if rows else None
            
        return status_code, updated_record

def delete_sleep_record_safe(record_id, user_id):
    with connection.cursor() as cursor:
        cursor.callproc('sp_delete_sleep_record_safe', [record_id, user_id])
        status_row = cursor.fetchone()
        status_code = status_row[0] if status_row else 1
        return status_code

def get_sleep_analysis(user_id, start_date=None, end_date=None):
    with connection.cursor() as cursor:
        cursor.callproc('sp_get_sleep_analysis', [user_id, start_date, end_date])
        
        # Result Set 1: Daily Data
        daily_data = dictfetchall(cursor)
        
        # Result Set 2: Monthly Data
        monthly_data = []
        if cursor.nextset():
            monthly_data = dictfetchall(cursor)
            
        # Result Set 3: Core Metrics
        metrics = {}
        if cursor.nextset():
            metrics_rows = dictfetchall(cursor)
            metrics = metrics_rows[0] if metrics_rows else {}
            
        return daily_data, monthly_data, metrics
