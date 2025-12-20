from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("SleepManage", "0007_alter_sleeprecord_created_at_and_more"),
    ]

    operations = [
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
                    SELECT * FROM sleepmanage_sleeprecord WHERE id = p_record_id;
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_update_sleep_record_safe;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_delete_sleep_record_safe(
                IN p_record_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_owner_id INT;
                DECLARE v_status INT DEFAULT 0;

                SELECT user_id INTO v_owner_id FROM sleepmanage_sleeprecord WHERE id = p_record_id;

                IF v_owner_id IS NULL THEN
                    SET v_status = 1; -- 不存在
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2; -- 无权删除
                ELSE
                    DELETE FROM sleepmanage_sleeprecord WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;

                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_delete_sleep_record_safe;",
        ),
    ]
