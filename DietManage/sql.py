from django.db import connection

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def get_meal_records(user_id, start_date=None, end_date=None):
    sql = "SELECT * FROM view_meal_record_full WHERE user_id = %s"
    params = [user_id]
    if start_date and end_date:
        sql += " AND date BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    sql += " ORDER BY date DESC, created_at DESC"
    
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        records = dictfetchall(cursor)
        
        # Fetch items for each record
        for r in records:
            r['items'] = get_meal_items(r['id'])
        return records

def get_meal_record_by_id(record_id):
    sql = "SELECT * FROM view_meal_record_full WHERE id = %s"
    with connection.cursor() as cursor:
        cursor.execute(sql, [record_id])
        rows = dictfetchall(cursor)
        if rows:
            record = rows[0]
            record['items'] = get_meal_items(record_id)
            return record
        return None

def get_meal_items(meal_record_id):
    sql = "SELECT * FROM view_meal_item_full WHERE meal_record_id = %s"
    with connection.cursor() as cursor:
        cursor.execute(sql, [meal_record_id])
        return dictfetchall(cursor)

def create_meal_record(user_id, date, meal, source, items=None):
    with connection.cursor() as cursor:
        # 1. Create Record
        cursor.callproc('sp_create_meal_record', [user_id, date, meal, source])
        rows = dictfetchall(cursor)
        if not rows:
            return None
        record = rows[0]
        
        # 2. Add Items
        if items:
            for item in items:
                # Clear result sets before next callproc if needed, 
                # but here we use a new cursor or nextset.
                # Actually, callproc might leave unread results.
                while cursor.nextset(): pass 
                cursor.callproc('sp_add_meal_item', [record['id'], item.get('food'), item.get('quantity_in_grams')])
        
        # Fetch full record with items
        return get_meal_record_by_id(record['id'])

def update_meal_record_safe(record_id, user_id, date=None, meal=None, source=None, items=None):
    with connection.cursor() as cursor:
        # 1. Update main record
        cursor.callproc('sp_update_meal_record_safe', [record_id, user_id, date, meal, source])
        status_row = cursor.fetchone()
        status_code = status_row[0] if status_row else 3
        
        if status_code != 0:
            return status_code, None

        # 2. If items are provided, clear and re-add them
        if items is not None:
            while cursor.nextset(): pass
            cursor.callproc('sp_clear_meal_items_safe', [record_id, user_id])
            
            for item in items:
                while cursor.nextset(): pass
                cursor.callproc('sp_add_meal_item', [record_id, item.get('food'), item.get('quantity_in_grams')])
        
        # 3. Return updated record
        return 0, get_meal_record_by_id(record_id)

def delete_meal_record_safe(record_id, user_id):
    with connection.cursor() as cursor:
        cursor.callproc('sp_delete_meal_record_safe', [record_id, user_id])
        status_row = cursor.fetchone()
        return status_row[0] if status_row else 1

def get_diet_analysis(user_id, start_date=None, end_date=None):
    with connection.cursor() as cursor:
        cursor.callproc('sp_get_diet_analysis', [user_id, start_date, end_date])
        
        # Result Set 1: Daily Data
        daily_data = dictfetchall(cursor)
        
        # Result Set 2: Food Details
        details_raw = []
        if cursor.nextset():
            details_raw = dictfetchall(cursor)
            
        # Result Set 3: Monthly Data
        monthly_data = []
        if cursor.nextset():
            monthly_data = dictfetchall(cursor)
            
        # Result Set 4: Metrics
        metrics = {}
        if cursor.nextset():
            metrics_rows = dictfetchall(cursor)
            metrics = metrics_rows[0] if metrics_rows else {}
            
        return daily_data, details_raw, monthly_data, metrics

def get_all_nutrition_foods():
    sql = "SELECT * FROM view_nutrition_food_full ORDER BY name"
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return dictfetchall(cursor)
