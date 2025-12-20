from django.db import connection
import json
import os

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def get_met_value(sport_id):
    met_path = os.path.join(os.path.dirname(__file__), 'met.json')
    try:
        with open(met_path, 'r', encoding='utf-8') as f:
            mets = json.load(f)
        return mets[int(sport_id)]['MET']
    except (IndexError, KeyError, ValueError, FileNotFoundError):
        return 1.0

def get_sport_records(user_id, start_date=None, end_date=None):
    sql = "SELECT * FROM view_sport_record_full WHERE user_id = %s"
    params = [user_id]
    
    if start_date and end_date:
        sql += " AND date BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    
    sql += " ORDER BY date DESC, begin_time DESC"
    
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return dictfetchall(cursor)

def get_sport_record_by_id(record_id):
    sql = "SELECT * FROM view_sport_record_full WHERE id = %s"
    with connection.cursor() as cursor:
        cursor.execute(sql, [record_id])
        rows = dictfetchall(cursor)
        return rows[0] if rows else None

def create_sport_record(user_id, date, sport, begin_time, end_time, note):
    met_value = get_met_value(sport)
    with connection.cursor() as cursor:
        cursor.callproc('sp_create_sport_record', [user_id, date, sport, begin_time, end_time, met_value, note])
        rows = dictfetchall(cursor)
        return rows[0] if rows else None

def update_sport_record_safe(record_id, user_id, date, sport, begin_time, end_time, note):
    met_value = None
    if sport is not None:
        met_value = get_met_value(sport)
    else:
        # 这里不会调用，不过为了完整性保留
        record = get_sport_record_by_id(record_id)
        if record:
            met_value = get_met_value(record['sport'])

    with connection.cursor() as cursor:
        cursor.callproc('sp_update_sport_record_safe', [record_id, user_id, date, sport, begin_time, end_time, met_value, note])
        
        status_row = cursor.fetchone()
        status_code = status_row[0] if status_row else 1
        
        updated_record = None
        if status_code == 0 and cursor.nextset():
            rows = dictfetchall(cursor)
            updated_record = rows[0] if rows else None
            
        return status_code, updated_record

def delete_sport_record_safe(record_id, user_id):
    with connection.cursor() as cursor:
        cursor.callproc('sp_delete_sport_record_safe', [record_id, user_id])
        status_row = cursor.fetchone()
        status_code = status_row[0] if status_row else 1
        return status_code

def get_sport_analysis(user_id, start_date=None, end_date=None):
    with connection.cursor() as cursor:
        cursor.callproc('sp_get_sport_analysis', [user_id, start_date, end_date])
        
        # Result Set 1: Daily Data
        daily_data = dictfetchall(cursor)
        
        # Result Set 2: Sport Details
        details = []
        if cursor.nextset():
            details = dictfetchall(cursor)
            
        # Result Set 3: Monthly Data
        monthly_data = []
        if cursor.nextset():
            monthly_data = dictfetchall(cursor)
            
        # Result Set 4: Metrics
        metrics = {}
        if cursor.nextset():
            metrics_rows = dictfetchall(cursor)
            metrics = metrics_rows[0] if metrics_rows else {}
            
        return daily_data, details, monthly_data, metrics
