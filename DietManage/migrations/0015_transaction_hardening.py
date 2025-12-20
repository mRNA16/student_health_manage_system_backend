from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("DietManage", "0014_fix_meal_record_delete_cascade"),
    ]

    operations = [
        # 1. Update sp_create_meal_record
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_create_meal_record;
            CREATE PROCEDURE sp_create_meal_record(
                IN p_user_id INT,
                IN p_date DATE,
                IN p_meal VARCHAR(10),
                IN p_source VARCHAR(20)
            )
            BEGIN
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;

                START TRANSACTION;
                INSERT INTO dietmanage_mealrecord (user_id, date, meal, source, created_at)
                VALUES (p_user_id, p_date, p_meal, p_source, NOW());
                COMMIT;
                
                SELECT * FROM view_meal_record_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_meal_record;"
        ),

        # 2. Update sp_add_meal_item
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_add_meal_item;
            CREATE PROCEDURE sp_add_meal_item(
                IN p_meal_record_id INT,
                IN p_food_id INT,
                IN p_quantity FLOAT
            )
            BEGIN
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;

                START TRANSACTION;
                INSERT INTO dietmanage_mealitem (meal_record_id, food_id, quantity_in_grams)
                VALUES (p_meal_record_id, p_food_id, p_quantity);
                COMMIT;
                
                SELECT * FROM view_meal_item_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_add_meal_item;"
        ),

        # 3. Update sp_delete_meal_record_safe
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
                END;

                START TRANSACTION;
                SELECT user_id INTO v_owner_id FROM dietmanage_mealrecord WHERE id = p_record_id FOR UPDATE;

                IF v_owner_id IS NULL THEN
                    SET v_status = 1;
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2;
                ELSE
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
