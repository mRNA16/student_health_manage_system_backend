from django.db import connection
from django.utils import timezone
import datetime
import json

def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def get_user_by_username(username):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM view_user_full WHERE username = %s", [username])
        row = dictfetchall(cursor)
        return row[0] if row else None

def get_user_by_id(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM view_user_full WHERE id = %s", [user_id])
        row = dictfetchall(cursor)
        return row[0] if row else None

def create_user(username, password, profile_data):
    # Prepare roles data: ensure it is a valid JSON string
    roles_data = profile_data.get('roles', [])
    if not isinstance(roles_data, str):
        roles_data = json.dumps(roles_data)

    with connection.cursor() as cursor:
        cursor.callproc('sp_create_user', [
            username,
            password,
            profile_data.get('height'),
            profile_data.get('weight'),
            profile_data.get('gender'),
            profile_data.get('birthday'),
            profile_data.get('realName'),
            roles_data,
            profile_data.get('daily_calories_burn_goal', 500),
            profile_data.get('daily_calories_intake_goal', 2000),
            profile_data.get('daily_sleep_hours_goal', 8)
        ])
        # Fetch the result of the SELECT new_user_id;
        row = cursor.fetchone()
        return row[0] if row else None

def update_user_profile(user_id, profile_data):
    # Construct update query dynamically based on provided fields
    fields = []
    params = []
    
    allowed_fields = [
        'height', 'weight', 'gender', 'birthday', 'realName', 'roles',
        'daily_calories_burn_goal', 'daily_calories_intake_goal', 'daily_sleep_hours_goal'
    ]
    
    for field in allowed_fields:
        if field in profile_data:
            # Handle camelCase to snake_case or quoted identifiers if needed
            # MySQL uses backticks for identifiers
            db_field = f'`{field}`' if field == 'realName' else field
            fields.append(f"{db_field} = %s")
            
            value = profile_data[field]
            # Serialize roles to JSON string if it's being updated
            if field == 'roles' and not isinstance(value, str):
                value = json.dumps(value)
                
            params.append(value)
            
    if not fields:
        return False
        
    params.append(user_id)
    sql = f"""
        UPDATE `usermanage_userprofile`
        SET {', '.join(fields)}
        WHERE user_id = %s
    """
    
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return True

def search_users(username_query=None):
    """
    Search users by username (exact match if provided, otherwise list all).
    Returns a list of users with their profiles nested.
    """
    sql_query = "SELECT * FROM view_user_full"
    params = []
    if username_query:
        sql_query += " WHERE username = %s"
        params.append(username_query)
    
    sql_query += " ORDER BY id"

    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        rows = dictfetchall(cursor)
    
    # Format results to match UserSerializer structure
    results = []
    profile_fields = [
        'height', 'weight', 'gender', 'birthday', 'realName', 'roles',
        'daily_calories_burn_goal', 'daily_calories_intake_goal', 'daily_sleep_hours_goal'
    ]
    
    for row in rows:
        user_dict = {
            'id': row['id'],
            'username': row['username'],
            'profile': {}
        }
        for field in profile_fields:
            if field in row:
                user_dict['profile'][field] = row[field]
        results.append(user_dict)
        
    return results

def get_friend_requests(user_id, direction='received', status='pending'):
    """
    Get friend requests using view_friend_details.
    """
    sql_query = "SELECT * FROM view_friend_details WHERE 1=1"
    params = []
    
    if direction == 'received':
        sql_query += " AND to_user_id = %s"
        params.append(user_id)
    elif direction == 'sent':
        sql_query += " AND from_user_id = %s"
        params.append(user_id)
    elif direction == 'both':
        sql_query += " AND (from_user_id = %s OR to_user_id = %s)"
        params.append(user_id)
        params.append(user_id)
        
    if status:
        sql_query += " AND status = %s"
        params.append(status)
        
    sql_query += " ORDER BY created_at DESC"
    
    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        return dictfetchall(cursor)

def get_friend_requests_v2(user_id, direction):
    """
    Get friend requests (pending and rejected) using stored procedure.
    """
    with connection.cursor() as cursor:
        cursor.callproc('sp_get_friend_requests_v2', [user_id, direction])
        return dictfetchall(cursor)

def get_friend_relationship(id):
    sql = """
        SELECT f.id, f.from_user_id, f.to_user_id, f.status, f.created_at
        FROM `usermanage_friend` f
        WHERE f.id = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [id])
        rows = dictfetchall(cursor)
        return rows[0] if rows else None

def handle_friend_request_safe(request_id, user_id, action):
    with connection.cursor() as cursor:
        cursor.callproc('sp_handle_friend_request', [request_id, user_id, action])
        row = cursor.fetchone()
        return row[0] if row else 1

def send_friend_request_safe(from_user_id, to_user_id):
    with connection.cursor() as cursor:
        cursor.callproc('sp_send_friend_request', [from_user_id, to_user_id])
        status_row = cursor.fetchone()
        status_code = status_row[0] if status_row else 1
        
        new_request = None
        if status_code == 0 and cursor.nextset():
            rows = dictfetchall(cursor)
            new_request = rows[0] if rows else None
            
        return status_code, new_request

def cancel_friend_request_safe(request_id, user_id):
    with connection.cursor() as cursor:
        cursor.callproc('sp_cancel_friend_request', [request_id, user_id])
        row = cursor.fetchone()
        return row[0] if row else 1

def remove_friend_relationship_safe(request_id, user_id):
    with connection.cursor() as cursor:
        cursor.callproc('sp_remove_friend_relationship', [request_id, user_id])
        row = cursor.fetchone()
        return row[0] if row else 1

def get_friend_activities_safe(user_id, friend_id):
    with connection.cursor() as cursor:
        # Use v2 for concurrency control
        cursor.callproc('sp_get_friend_activities_safe_v2', [user_id, friend_id])
        
        # Result Set 1: Status
        status_row = cursor.fetchone()
        status_code = status_row[0] if status_row else 1
        
        user_info = None
        activities = []
        
        if status_code == 0:
            # Result Set 2: User Info
            if cursor.nextset():
                user_rows = dictfetchall(cursor)
                user_info = user_rows[0] if user_rows else None
            
            # Result Set 3: Activities
            if cursor.nextset():
                activities = dictfetchall(cursor)
                
        return status_code, user_info, activities

def get_user_friends_all(user_id):
    with connection.cursor() as cursor:
        cursor.callproc('sp_get_user_friends_all', [user_id])
        return dictfetchall(cursor)
