from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("UserManage", "0017_transaction_hardening"),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_create_user;
            CREATE PROCEDURE sp_create_user(
                IN p_username VARCHAR(150),
                IN p_password VARCHAR(128),
                IN p_height DOUBLE,
                IN p_weight DOUBLE,
                IN p_gender VARCHAR(10),
                IN p_birthday DATE,
                IN p_realName VARCHAR(50),
                IN p_roles JSON,
                IN p_daily_calories_burn_goal DOUBLE,
                IN p_daily_calories_intake_goal DOUBLE,
                IN p_daily_sleep_hours_goal DOUBLE
            )
            BEGIN
                DECLARE v_user_id INT;
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;
                START TRANSACTION;
                INSERT INTO auth_user (username, password, is_superuser, is_staff, is_active, date_joined)
                VALUES (p_username, p_password, 0, 0, 1, NOW());
                SET v_user_id = LAST_INSERT_ID();
                INSERT INTO usermanage_userprofile (
                    user_id, height, weight, gender, birthday, realName, roles,
                    daily_calories_burn_goal, daily_calories_intake_goal, daily_sleep_hours_goal
                ) VALUES (
                    v_user_id, p_height, p_weight, p_gender, p_birthday, p_realName, p_roles,
                    p_daily_calories_burn_goal, p_daily_calories_intake_goal, p_daily_sleep_hours_goal
                );
                COMMIT;
                SELECT v_user_id;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_user;"
        ),
    ]
