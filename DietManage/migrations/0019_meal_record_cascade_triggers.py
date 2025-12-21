from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("DietManage", "0018_add_update_meal_sp"),
    ]

    operations = [
        # 1. Trigger to delete meal items and comments when a meal record is deleted
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS tr_meal_record_cascade_delete;
            CREATE TRIGGER tr_meal_record_cascade_delete
            BEFORE DELETE ON dietmanage_mealrecord
            FOR EACH ROW
            BEGIN
                -- Delete associated meal items
                DELETE FROM dietmanage_mealitem WHERE meal_record_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_meal_record_cascade_delete;"
        ),
        
        # 3. Simplify sp_delete_meal_record_safe since triggers now handle cascade
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_delete_meal_record_safe;
            CREATE PROCEDURE sp_delete_meal_record_safe(
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
                    -- Now we only need to delete the main record, 
                    -- the trigger tr_meal_record_cascade_delete will handle items and comments.
                    DELETE FROM dietmanage_mealrecord WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;

                IF v_status = 0 THEN COMMIT; ELSE ROLLBACK; END IF;
                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_delete_meal_record_safe;"
        ),
    ]
