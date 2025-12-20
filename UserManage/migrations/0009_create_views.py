from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("UserManage", "0008_setup_triggers"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE VIEW view_user_full AS
            SELECT 
                u.id, u.username, u.email,
                p.height, p.weight, p.gender, p.birthday, p.`realName`, p.roles,
                p.daily_calories_burn_goal, p.daily_calories_intake_goal, p.daily_sleep_hours_goal
            FROM auth_user u
            LEFT JOIN `usermanage_userprofile` p ON u.id = p.user_id;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_user_full;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE VIEW view_friend_details AS
            SELECT 
                f.id, f.from_user_id, f.to_user_id, f.status, f.created_at,
                u_from.username as from_username, u_to.username as to_username
            FROM `usermanage_friend` f
            JOIN auth_user u_from ON f.from_user_id = u_from.id
            JOIN auth_user u_to ON f.to_user_id = u_to.id;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_friend_details;",
        ),
    ]
