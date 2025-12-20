from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("SleepManage", "0011_remove_sleeprecord_duration"),
    ]

    operations = [
        # 1. Drop old triggers that reference duration
        migrations.RunSQL(
            sql="DROP TRIGGER IF EXISTS tr_sleep_record_duration_insert;",
            reverse_sql="",
        ),
        migrations.RunSQL(
            sql="DROP TRIGGER IF EXISTS tr_sleep_record_duration_update;",
            reverse_sql="",
        ),
        # 2. Create new trigger for timestamp only
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_sleep_record_timestamp_insert
            BEFORE INSERT ON sleepmanage_sleeprecord
            FOR EACH ROW
            BEGIN
                IF NEW.created_at IS NULL THEN
                    SET NEW.created_at = NOW();
                END IF;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_sleep_record_timestamp_insert;",
        ),
        # 3. Create the View for 3NF compliance
        migrations.RunSQL(
            sql="""
            CREATE VIEW view_sleep_record_full AS
            SELECT 
                id, user_id, date, sleep_time, wake_time, created_at,
                (TIMESTAMPDIFF(SECOND, 
                    CAST(CONCAT(date, ' ', sleep_time) AS DATETIME),
                    IF(wake_time < sleep_time, 
                       DATE_ADD(CAST(CONCAT(date, ' ', wake_time) AS DATETIME), INTERVAL 1 DAY),
                       CAST(CONCAT(date, ' ', wake_time) AS DATETIME)
                    )
                ) / 3600.0) AS duration
            FROM sleepmanage_sleeprecord;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_sleep_record_full;",
        ),
        # 4. Update sp_create_sleep_record (Remove duration from INSERT, SELECT from view)
        migrations.RunSQL(
            sql="DROP PROCEDURE IF EXISTS sp_create_sleep_record;",
            reverse_sql="",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_create_sleep_record(
                IN p_user_id INT,
                IN p_date DATE,
                IN p_sleep_time TIME,
                IN p_wake_time TIME
            )
            BEGIN
                INSERT INTO sleepmanage_sleeprecord (user_id, date, sleep_time, wake_time, created_at)
                VALUES (p_user_id, p_date, p_sleep_time, p_wake_time, NOW());
                
                SELECT * FROM view_sleep_record_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_sleep_record;",
        ),
        # 5. Update sp_update_sleep_record_safe (SELECT from view)
        migrations.RunSQL(
            sql="DROP PROCEDURE IF EXISTS sp_update_sleep_record_safe;",
            reverse_sql="",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_update_sleep_record_safe(
                IN p_record_id INT,
                IN p_user_id INT,
                IN p_date DATE,
                IN p_sleep_time TIME,
                IN p_wake_time TIME
            )
            BEGIN
                DECLARE v_owner_id INT;
                DECLARE v_status INT DEFAULT 0;

                SELECT user_id INTO v_owner_id FROM sleepmanage_sleeprecord WHERE id = p_record_id;

                IF v_owner_id IS NULL THEN
                    SET v_status = 1; -- 不存在
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2; -- 无权修改
                ELSE
                    UPDATE sleepmanage_sleeprecord 
                    SET date = COALESCE(p_date, date),
                        sleep_time = COALESCE(p_sleep_time, sleep_time),
                        wake_time = COALESCE(p_wake_time, wake_time)
                    WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;

                SELECT v_status AS status_code;
                IF v_status = 0 THEN
                    SELECT * FROM view_sleep_record_full WHERE id = p_record_id;
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_update_sleep_record_safe;",
        ),
    ]
