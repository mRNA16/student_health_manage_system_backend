from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("SleepManage", "0015_transaction_hardening"),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_create_sleep_record;
            CREATE PROCEDURE sp_create_sleep_record(
                IN p_user_id INT,
                IN p_date DATE,
                IN p_sleep_time TIME,
                IN p_wake_time TIME
            )
            BEGIN
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;
                START TRANSACTION;
                INSERT INTO sleepmanage_sleeprecord (user_id, date, sleep_time, wake_time, created_at)
                VALUES (p_user_id, p_date, p_sleep_time, p_wake_time, NOW());
                COMMIT;
                SELECT * FROM view_sleep_record_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_sleep_record;"
        ),
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_update_sleep_record_safe;
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
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;
                START TRANSACTION;
                SELECT user_id INTO v_owner_id FROM sleepmanage_sleeprecord WHERE id = p_record_id FOR UPDATE;
                IF v_owner_id IS NULL THEN
                    SET v_status = 1;
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2;
                ELSE
                    UPDATE sleepmanage_sleeprecord 
                    SET date = COALESCE(p_date, date),
                        sleep_time = COALESCE(p_sleep_time, sleep_time),
                        wake_time = COALESCE(p_wake_time, wake_time)
                    WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;
                IF v_status = 0 THEN COMMIT; ELSE ROLLBACK; END IF;
                SELECT v_status AS status_code;
                IF v_status = 0 THEN
                    SELECT * FROM view_sleep_record_full WHERE id = p_record_id;
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_update_sleep_record_safe;"
        ),
    ]
