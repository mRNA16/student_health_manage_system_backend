from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("DietManage", "0016_mealrecord_dietmanage__user_id_c2a08e_idx"),
    ]
    operations = [
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
                    -- Return a status code even on error to avoid fetchone() returning None
                    SELECT 3 AS status_code; 
                END;

                START TRANSACTION;
                -- Lock the row for update
                SELECT user_id INTO v_owner_id FROM dietmanage_mealrecord WHERE id = p_record_id FOR UPDATE;

                IF v_owner_id IS NULL THEN
                    SET v_status = 1; -- Not found
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2; -- Unauthorized
                ELSE
                    -- 1. Delete associated meal items first to satisfy foreign key constraints
                    DELETE FROM dietmanage_mealitem WHERE meal_record_id = p_record_id;
                    
                    -- 2. Delete the meal record itself
                    DELETE FROM dietmanage_mealrecord WHERE id = p_record_id;
                    
                    SET v_status = 0; -- Success
                END IF;

                IF v_status = 0 THEN 
                    COMMIT; 
                ELSE 
                    ROLLBACK; 
                END IF;
                
                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_delete_meal_record_safe;"
        ),
    ]
