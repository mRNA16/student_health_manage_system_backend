from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('DietManage', '0010_import_nutrition_data'),
    ]

    operations = [
        # 1. Remove derived fields from MealItem
        migrations.RemoveField(
            model_name='mealitem',
            name='estimated_calories',
        ),
        migrations.RemoveField(
            model_name='mealitem',
            name='estimated_water',
        ),
        # 2. Alter FKs to DO_NOTHING where appropriate
        migrations.AlterField(
            model_name='mealrecord',
            name='user',
            field=models.ForeignKey(on_delete=models.deletion.DO_NOTHING, to='auth.user'),
        ),
        migrations.AlterField(
            model_name='mealitem',
            name='food',
            field=models.ForeignKey(null=True, on_delete=models.deletion.DO_NOTHING, to='DietManage.nutritionfood'),
        ),
        # 3. Alter created_at to be nullable for trigger
        migrations.AlterField(
            model_name='mealrecord',
            name='created_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # 4. Create View for Meal Items (3NF)
        migrations.RunSQL(
            sql="""
            CREATE VIEW view_meal_item_full AS
            SELECT 
                mi.id, 
                mi.meal_record_id, 
                mi.food_id, 
                mi.quantity_in_grams,
                nf.name as food_name,
                CAST(nf.energy_kj * 0.239 * mi.quantity_in_grams / 100.0 AS DOUBLE) AS estimated_calories,
                CAST(nf.water_content * mi.quantity_in_grams / 100.0 AS DOUBLE) AS estimated_water
            FROM dietmanage_mealitem mi
            LEFT JOIN dietmanage_nutritionfood nf ON mi.food_id = nf.id;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_meal_item_full;",
        ),
        # 5. Create View for Meal Records (Aggregated)
        migrations.RunSQL(
            sql="""
            CREATE VIEW view_meal_record_full AS
            SELECT 
                mr.id, 
                mr.user_id, 
                mr.date, 
                mr.meal, 
                mr.source, 
                mr.created_at,
                COALESCE(SUM(vmi.estimated_calories), 0) as total_calories,
                COALESCE(SUM(vmi.estimated_water), 0) as total_water
            FROM dietmanage_mealrecord mr
            LEFT JOIN view_meal_item_full vmi ON mr.id = vmi.meal_record_id
            GROUP BY mr.id;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_meal_record_full;",
        ),
        # 6. Stored Procedures
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_create_meal_record(
                IN p_user_id INT,
                IN p_date DATE,
                IN p_meal VARCHAR(10),
                IN p_source VARCHAR(20)
            )
            BEGIN
                INSERT INTO dietmanage_mealrecord (user_id, date, meal, source, created_at)
                VALUES (p_user_id, p_date, p_meal, p_source, NOW());
                SELECT * FROM view_meal_record_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_meal_record;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_add_meal_item(
                IN p_meal_record_id INT,
                IN p_food_id INT,
                IN p_quantity FLOAT
            )
            BEGIN
                INSERT INTO dietmanage_mealitem (meal_record_id, food_id, quantity_in_grams)
                VALUES (p_meal_record_id, p_food_id, p_quantity);
                SELECT * FROM view_meal_item_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_add_meal_item;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_delete_meal_record_safe(
                IN p_record_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_owner_id INT;
                DECLARE v_status INT DEFAULT 0;
                SELECT user_id INTO v_owner_id FROM dietmanage_mealrecord WHERE id = p_record_id;
                IF v_owner_id IS NULL THEN
                    SET v_status = 1;
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2;
                ELSE
                    -- MealItems will be deleted by DB CASCADE if configured, 
                    -- but we can be explicit if needed.
                    DELETE FROM dietmanage_mealrecord WHERE id = p_record_id;
                    SET v_status = 0;
                END IF;
                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_delete_meal_record_safe;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_get_diet_analysis(
                IN p_user_id INT,
                IN p_start_date DATE,
                IN p_end_date DATE
            )
            BEGIN
                -- Result Set 1: Daily Aggregation
                SELECT 
                    date,
                    ROUND(SUM(IF(meal='breakfast', total_calories, 0)), 1) as breakfast,
                    ROUND(SUM(IF(meal='lunch', total_calories, 0)), 1) as lunch,
                    ROUND(SUM(IF(meal='dinner', total_calories, 0)), 1) as dinner,
                    ROUND(SUM(total_calories), 1) as total
                FROM view_meal_record_full
                WHERE user_id = p_user_id
                  AND (p_start_date IS NULL OR date >= p_start_date)
                  AND (p_end_date IS NULL OR date <= p_end_date)
                GROUP BY date
                ORDER BY date;

                -- Result Set 2: Food Details per Day
                SELECT 
                    mr.date,
                    vmi.food_name as name,
                    ROUND(SUM(vmi.estimated_calories), 1) as value
                FROM dietmanage_mealrecord mr
                JOIN view_meal_item_full vmi ON mr.id = vmi.meal_record_id
                WHERE mr.user_id = p_user_id
                  AND (p_start_date IS NULL OR mr.date >= p_start_date)
                  AND (p_end_date IS NULL OR mr.date <= p_end_date)
                GROUP BY mr.date, vmi.food_name
                ORDER BY mr.date, value DESC;

                -- Result Set 3: Monthly Aggregation
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') as month,
                    ROUND(AVG(daily_total), 1) as avgCalories,
                    ROUND(SUM(daily_total), 1) as totalCalories
                FROM (
                    SELECT date, SUM(total_calories) as daily_total
                    FROM view_meal_record_full
                    WHERE user_id = p_user_id
                      AND (p_start_date IS NULL OR date >= p_start_date)
                      AND (p_end_date IS NULL OR date <= p_end_date)
                    GROUP BY date
                ) t
                GROUP BY month
                ORDER BY month;

                -- Result Set 4: Core Metrics
                SELECT 
                    COALESCE(ROUND(AVG(daily_total), 1), 0) as avgDailyCalories,
                    COALESCE(ROUND(AVG(meal_count), 2), 0) as avgMealsPerDay
                FROM (
                    SELECT date, SUM(total_calories) as daily_total, COUNT(DISTINCT meal) as meal_count
                    FROM view_meal_record_full
                    WHERE user_id = p_user_id
                    GROUP BY date
                ) t;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_get_diet_analysis;",
        ),
        # 7. Triggers
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_meal_record_timestamp_insert
            BEFORE INSERT ON dietmanage_mealrecord
            FOR EACH ROW
            BEGIN
                IF NEW.created_at IS NULL THEN
                    SET NEW.created_at = NOW();
                END IF;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_meal_record_timestamp_insert;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_user_diet_cascade_delete
            BEFORE DELETE ON auth_user
            FOR EACH ROW
            BEGIN
                DELETE FROM dietmanage_mealrecord WHERE user_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_user_diet_cascade_delete;",
        ),
    ]
