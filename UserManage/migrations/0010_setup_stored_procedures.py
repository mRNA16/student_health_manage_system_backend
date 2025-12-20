from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("UserManage", "0009_create_views"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_create_user(
                IN p_username VARCHAR(150),
                IN p_password VARCHAR(128),
                IN p_height DOUBLE,
                IN p_weight DOUBLE,
                IN p_gender VARCHAR(10),
                IN p_birthday DATE,
                IN p_realName VARCHAR(150),
                IN p_roles JSON,
                IN p_burn_goal DOUBLE,
                IN p_intake_goal DOUBLE,
                IN p_sleep_goal DOUBLE
            )
            BEGIN
                DECLARE new_user_id INT;

                INSERT INTO auth_user 
                (password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
                VALUES (p_password, NULL, 0, p_username, '', '', '', 0, 1, NOW());
                
                SET new_user_id = LAST_INSERT_ID();

                INSERT INTO `usermanage_userprofile`
                (user_id, height, weight, gender, birthday, `realName`, roles, 
                 daily_calories_burn_goal, daily_calories_intake_goal, daily_sleep_hours_goal)
                VALUES (new_user_id, p_height, p_weight, p_gender, p_birthday, p_realName, p_roles, p_burn_goal, p_intake_goal, p_sleep_goal);

                SELECT new_user_id;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_user;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_get_friend_requests_v2(
                IN p_user_id INT,
                IN p_direction VARCHAR(20)
            )
            BEGIN
                IF p_direction = 'received' THEN
                    SELECT * FROM view_friend_details 
                    WHERE to_user_id = p_user_id AND status IN ('pending', 'rejected')
                    ORDER BY created_at DESC;
                ELSEIF p_direction = 'sent' THEN
                    SELECT * FROM view_friend_details 
                    WHERE from_user_id = p_user_id AND status IN ('pending', 'rejected')
                    ORDER BY created_at DESC;
                ELSE
                    SELECT * FROM view_friend_details 
                    WHERE (from_user_id = p_user_id OR to_user_id = p_user_id) AND status IN ('pending', 'rejected')
                    ORDER BY created_at DESC;
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_get_friend_requests_v2;",
        ),
    ]
