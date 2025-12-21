from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("UserManage", "0018_revert_sp_create_user_signature"),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_update_user_profile;
            CREATE PROCEDURE sp_update_user_profile(
                IN p_user_id INT,
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
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;

                START TRANSACTION;
                -- 显式锁定行，确保更新期间的一致性，并防止与其他模块（如 SportManage）产生冲突
                SELECT user_id FROM usermanage_userprofile WHERE user_id = p_user_id FOR UPDATE;

                UPDATE usermanage_userprofile
                SET height = COALESCE(p_height, height),
                    weight = COALESCE(p_weight, weight),
                    gender = COALESCE(p_gender, gender),
                    birthday = COALESCE(p_birthday, birthday),
                    realName = COALESCE(p_realName, realName),
                    roles = COALESCE(p_roles, roles),
                    daily_calories_burn_goal = COALESCE(p_daily_calories_burn_goal, daily_calories_burn_goal),
                    daily_calories_intake_goal = COALESCE(p_daily_calories_intake_goal, daily_calories_intake_goal),
                    daily_sleep_hours_goal = COALESCE(p_daily_sleep_hours_goal, daily_sleep_hours_goal)
                WHERE user_id = p_user_id;
                
                COMMIT;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_update_user_profile;"
        ),
    ]
