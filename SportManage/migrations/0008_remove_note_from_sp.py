from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("SportManage", "0007_transaction_hardening"),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_create_sport_record;
            CREATE PROCEDURE sp_create_sport_record(
                IN p_user_id INT,
                IN p_date DATE,
                IN p_sport INT,
                IN p_begin_time TIME,
                IN p_end_time TIME,
                IN p_met_value DOUBLE
            )
            BEGIN
                DECLARE v_weight DOUBLE;
                DECLARE v_calories DOUBLE;
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;
                START TRANSACTION;
                SELECT weight INTO v_weight FROM usermanage_userprofile WHERE user_id = p_user_id LOCK IN SHARE MODE;
                SET v_calories = p_met_value * v_weight * (TIMESTAMPDIFF(SECOND, p_begin_time, p_end_time) / 3600.0);
                INSERT INTO sportmanage_sportrecord (user_id, date, sport, begin_time, end_time, calories, created_at)
                VALUES (p_user_id, p_date, p_sport, p_begin_time, p_end_time, v_calories, NOW());
                COMMIT;
                SELECT * FROM view_sport_record_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_sport_record;"
        ),
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_update_sport_record_safe;
            CREATE PROCEDURE sp_update_sport_record_safe(
                IN p_record_id INT,
                IN p_user_id INT,
                IN p_date DATE,
                IN p_sport INT,
                IN p_begin_time TIME,
                IN p_end_time TIME,
                IN p_met_value DOUBLE
            )
            BEGIN
                DECLARE v_owner_id INT;
                DECLARE v_status INT DEFAULT 0;
                DECLARE v_weight DOUBLE;
                DECLARE v_calories DOUBLE;
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;
                START TRANSACTION;
                SELECT user_id INTO v_owner_id FROM sportmanage_sportrecord WHERE id = p_record_id FOR UPDATE;
                IF v_owner_id IS NULL THEN
                    SET v_status = 1;
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2;
                ELSE
                    SELECT weight INTO v_weight FROM usermanage_userprofile WHERE user_id = p_user_id LOCK IN SHARE MODE;
                    SET v_calories = p_met_value * v_weight * (TIMESTAMPDIFF(SECOND, p_begin_time, p_end_time) / 3600.0);
                    UPDATE sportmanage_sportrecord 
                    SET date = COALESCE(p_date, date),
                        sport = COALESCE(p_sport, sport),
                        begin_time = COALESCE(p_begin_time, begin_time),
                        end_time = COALESCE(p_end_time, end_time),
                        calories = v_calories
                    WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;
                IF v_status = 0 THEN COMMIT; ELSE ROLLBACK; END IF;
                SELECT v_status AS status_code;
                IF v_status = 0 THEN
                    SELECT * FROM view_sport_record_full WHERE id = p_record_id;
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_update_sport_record_safe;"
        ),
    ]
