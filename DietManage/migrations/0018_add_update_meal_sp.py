from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("DietManage", "0017_fix_delete_meal_record_bug"),
    ]

    operations = [
        # 1. Update meal record main info
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_update_meal_record_safe;
            CREATE PROCEDURE sp_update_meal_record_safe(
                IN p_record_id INT,
                IN p_user_id INT,
                IN p_date DATE,
                IN p_meal VARCHAR(10),
                IN p_source VARCHAR(20)
            )
            BEGIN
                DECLARE v_owner_id INT;
                DECLARE v_status INT DEFAULT 0;
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                    SELECT 3 AS status_code;
                END;

                START TRANSACTION;
                SELECT user_id INTO v_owner_id FROM dietmanage_mealrecord WHERE id = p_record_id FOR UPDATE;

                IF v_owner_id IS NULL THEN
                    SET v_status = 1;
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2;
                ELSE
                    UPDATE dietmanage_mealrecord
                    SET date = COALESCE(p_date, date),
                        meal = COALESCE(p_meal, meal),
                        source = COALESCE(p_source, source)
                    WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;

                IF v_status = 0 THEN COMMIT; ELSE ROLLBACK; END IF;
                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_update_meal_record_safe;"
        ),
        
        # 2. Clear meal items for a record
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_clear_meal_items_safe;
            CREATE PROCEDURE sp_clear_meal_items_safe(
                IN p_record_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_owner_id INT;
                DECLARE v_status INT DEFAULT 0;
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                    SELECT 3 AS status_code;
                END;

                START TRANSACTION;
                SELECT user_id INTO v_owner_id FROM dietmanage_mealrecord WHERE id = p_record_id FOR UPDATE;

                IF v_owner_id IS NULL THEN
                    SET v_status = 1;
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2;
                ELSE
                    DELETE FROM dietmanage_mealitem WHERE meal_record_id = p_record_id;
                    SET v_status = 0;
                END IF;

                IF v_status = 0 THEN COMMIT; ELSE ROLLBACK; END IF;
                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_clear_meal_items_safe;"
        ),
    ]
