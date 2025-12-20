from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("UserManage", "0014_update_activity_sp_for_3nf"),
        ("SportManage", "0005_sport_record_native_sql"),
        ("DietManage", "0011_diet_record_native_sql"),
        ("SleepManage", "0012_refactor_to_3nf"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP PROCEDURE IF EXISTS sp_get_friend_activities_safe;",
            reverse_sql="",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_get_friend_activities_safe(
                IN p_user_id INT,
                IN p_friend_id INT
            )
            BEGIN
                DECLARE v_is_friend INT DEFAULT 0;
                DECLARE v_status INT DEFAULT 0;

                -- 1. Check if user exists
                IF NOT EXISTS (SELECT 1 FROM auth_user WHERE id = p_friend_id) THEN
                    SET v_status = 1; -- 用户不存在
                ELSE
                    -- 2. Check friendship (allow if self or accepted friends)
                    IF p_user_id = p_friend_id THEN
                        SET v_is_friend = 1;
                    ELSE
                        SELECT COUNT(*) INTO v_is_friend FROM usermanage_friend 
                        WHERE ((from_user_id = p_user_id AND to_user_id = p_friend_id) 
                           OR (from_user_id = p_friend_id AND to_user_id = p_user_id))
                        AND status = 'accepted';
                    END IF;

                    IF v_is_friend = 0 THEN
                        SET v_status = 2; -- 非好友，无权查看
                    ELSE
                        SET v_status = 0;
                    END IF;
                END IF;

                -- Return status
                SELECT v_status AS status_code;

                IF v_status = 0 THEN
                    -- Result Set 2: User Info
                    SELECT id, username FROM auth_user WHERE id = p_friend_id;

                    -- Result Set 3: Unified Activities
                    (SELECT id, 'sport' AS type, CAST(sport AS CHAR) AS detail, duration, created_at 
                     FROM view_sport_record_full WHERE user_id = p_friend_id)
                    UNION ALL
                    (SELECT id, 'sleep' AS type, NULL AS detail, duration, created_at 
                     FROM view_sleep_record_full WHERE user_id = p_friend_id)
                    UNION ALL
                    (SELECT id, 'meal' AS type, meal AS detail, total_calories AS duration, created_at 
                     FROM view_meal_record_full WHERE user_id = p_friend_id)
                    ORDER BY created_at DESC;
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_get_friend_activities_safe;",
        ),
    ]
