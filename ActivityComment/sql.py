from django.db import connection

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def get_comments(activity_type=None, activity_id=None):
    sql = "SELECT * FROM view_activity_comment_full"
    params = []
    
    if activity_type and activity_id:
        sql += " WHERE activity_type = %s AND activity_id = %s"
        params.extend([activity_type, activity_id])
    
    sql += " ORDER BY created_at ASC"
    
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return dictfetchall(cursor)

def create_comment(user_id, activity_type, activity_id, content):
    with connection.cursor() as cursor:
        cursor.callproc('sp_create_activity_comment', [user_id, activity_type, activity_id, content])
        rows = dictfetchall(cursor)
        return rows[0] if rows else None

def delete_comment_safe(comment_id, user_id):
    with connection.cursor() as cursor:
        cursor.callproc('sp_delete_activity_comment_safe', [comment_id, user_id])
        status_row = cursor.fetchone()
        return status_row[0] if status_row else 1
