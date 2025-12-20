from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("SportManage", "0004_delete_comment"),
        ("UserManage", "0014_update_activity_sp_for_3nf"), # Ensure UserProfile exists
    ]

    operations = [
        # 1. Remove duration column
        migrations.RemoveField(
            model_name="sportrecord",
            name="duration",
        ),
        # 2. Alter user field to DO_NOTHING (already done in model, but need migration)
        migrations.AlterField(
            model_name="sportrecord",
            name="user",
            field=models.ForeignKey(
                on_delete=models.deletion.DO_NOTHING,
                related_name="sport_records",
                to="auth.user",
            ),
        ),
        # 3. Add created_at if it was auto_now_add (it was, but we want it nullable for trigger)
        migrations.AlterField(
            model_name="sportrecord",
            name="created_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        # 4. Create View for Duration (3NF)
        migrations.RunSQL(
            sql="""
            CREATE VIEW view_sport_record_full AS
            SELECT 
                id, user_id, date, sport, begin_time, end_time, calories, note, created_at,
                CAST(
                    (TIMESTAMPDIFF(SECOND, 
                        CAST(CONCAT(date, ' ', begin_time) AS DATETIME),
                        IF(end_time < begin_time, 
                           DATE_ADD(CAST(CONCAT(date, ' ', end_time) AS DATETIME), INTERVAL 1 DAY),
                           CAST(CONCAT(date, ' ', end_time) AS DATETIME)
                        )
                    ) / 3600.0) 
                AS DOUBLE) AS duration
            FROM sportmanage_sportrecord;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_sport_record_full;",
        ),
        # 5. Create Stored Procedures
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_create_sport_record(
                IN p_user_id INT,
                IN p_date DATE,
                IN p_sport INT,
                IN p_begin_time TIME,
                IN p_end_time TIME,
                IN p_met_value FLOAT,
                IN p_note VARCHAR(255)
            )
            BEGIN
                DECLARE v_weight FLOAT;
                DECLARE v_gender VARCHAR(10);
                DECLARE v_factor FLOAT;
                DECLARE v_duration FLOAT;
                DECLARE v_calories FLOAT;
                DECLARE v_st DATETIME;
                DECLARE v_et DATETIME;

                -- Get user profile info
                SELECT weight, gender INTO v_weight, v_gender FROM usermanage_userprofile WHERE user_id = p_user_id;
                
                -- Default values if profile not found
                IF v_weight IS NULL THEN SET v_weight = 70.0; END IF;
                IF v_gender IS NULL THEN SET v_gender = 'male'; END IF;

                -- Calculate duration
                SET v_st = CAST(CONCAT(p_date, ' ', p_begin_time) AS DATETIME);
                SET v_et = CAST(CONCAT(p_date, ' ', p_end_time) AS DATETIME);
                IF v_et < v_st THEN
                    SET v_et = DATE_ADD(v_et, INTERVAL 1 DAY);
                END IF;
                SET v_duration = TIMESTAMPDIFF(SECOND, v_st, v_et) / 3600.0;

                -- Calculate calories
                SET v_factor = IF(v_gender = 'male', 3.5, 3.1);
                SET v_calories = (p_met_value * v_weight * v_factor / 200.0) * v_duration * 60.0;

                INSERT INTO sportmanage_sportrecord (user_id, date, sport, begin_time, end_time, calories, note, created_at)
                VALUES (p_user_id, p_date, p_sport, p_begin_time, p_end_time, v_calories, p_note, NOW());
                
                SELECT * FROM view_sport_record_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_sport_record;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_update_sport_record_safe(
                IN p_record_id INT,
                IN p_user_id INT,
                IN p_date DATE,
                IN p_sport INT,
                IN p_begin_time TIME,
                IN p_end_time TIME,
                IN p_met_value FLOAT,
                IN p_note VARCHAR(255)
            )
            BEGIN
                DECLARE v_owner_id INT;
                DECLARE v_status INT DEFAULT 0;
                DECLARE v_weight FLOAT;
                DECLARE v_gender VARCHAR(10);
                DECLARE v_factor FLOAT;
                DECLARE v_duration FLOAT;
                DECLARE v_calories FLOAT;
                DECLARE v_st DATETIME;
                DECLARE v_et DATETIME;
                
                -- Current values for COALESCE
                DECLARE curr_date DATE;
                DECLARE curr_sport INT;
                DECLARE curr_begin TIME;
                DECLARE curr_end TIME;

                SELECT user_id, date, sport, begin_time, end_time 
                INTO v_owner_id, curr_date, curr_sport, curr_begin, curr_end 
                FROM sportmanage_sportrecord WHERE id = p_record_id;

                IF v_owner_id IS NULL THEN
                    SET v_status = 1; -- Not found
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2; -- Unauthorized
                ELSE
                    -- Recalculate calories if needed
                    SELECT weight, gender INTO v_weight, v_gender FROM usermanage_userprofile WHERE user_id = p_user_id;
                    IF v_weight IS NULL THEN SET v_weight = 70.0; END IF;
                    IF v_gender IS NULL THEN SET v_gender = 'male'; END IF;

                    SET v_st = CAST(CONCAT(COALESCE(p_date, curr_date), ' ', COALESCE(p_begin_time, curr_begin)) AS DATETIME);
                    SET v_et = CAST(CONCAT(COALESCE(p_date, curr_date), ' ', COALESCE(p_end_time, curr_end)) AS DATETIME);
                    IF v_et < v_st THEN
                        SET v_et = DATE_ADD(v_et, INTERVAL 1 DAY);
                    END IF;
                    SET v_duration = TIMESTAMPDIFF(SECOND, v_st, v_et) / 3600.0;

                    SET v_factor = IF(v_gender = 'male', 3.5, 3.1);
                    -- If p_met_value is null, we might need to know the old MET value. 
                    -- But since we don't have a MET table, we assume p_met_value is always provided if sport changes, 
                    -- or we just use the provided one.
                    SET v_calories = (COALESCE(p_met_value, 1.0) * v_weight * v_factor / 200.0) * v_duration * 60.0;

                    UPDATE sportmanage_sportrecord 
                    SET date = COALESCE(p_date, date),
                        sport = COALESCE(p_sport, sport),
                        begin_time = COALESCE(p_begin_time, begin_time),
                        end_time = COALESCE(p_end_time, end_time),
                        calories = v_calories,
                        note = COALESCE(p_note, note)
                    WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;

                SELECT v_status AS status_code;
                IF v_status = 0 THEN
                    SELECT * FROM view_sport_record_full WHERE id = p_record_id;
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_update_sport_record_safe;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_delete_sport_record_safe(
                IN p_record_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_owner_id INT;
                DECLARE v_status INT DEFAULT 0;

                SELECT user_id INTO v_owner_id FROM sportmanage_sportrecord WHERE id = p_record_id;

                IF v_owner_id IS NULL THEN
                    SET v_status = 1;
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2;
                ELSE
                    DELETE FROM sportmanage_sportrecord WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;

                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_delete_sport_record_safe;",
        ),
        # 6. Triggers
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_sport_record_timestamp_insert
            BEFORE INSERT ON sportmanage_sportrecord
            FOR EACH ROW
            BEGIN
                IF NEW.created_at IS NULL THEN
                    SET NEW.created_at = NOW();
                END IF;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_sport_record_timestamp_insert;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_sport_record_cascade_delete
            BEFORE DELETE ON auth_user
            FOR EACH ROW
            BEGIN
                DELETE FROM sportmanage_sportrecord WHERE user_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_sport_record_cascade_delete;",
        ),
    ]
