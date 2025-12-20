from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ActivityComment', '0002_alter_activitycomment_created_at_and_more'),
        ('SleepManage', '0014_sleep_analysis_procedure'),
        ('SportManage', '0006_sport_analysis_procedure'),
        ('DietManage', '0014_fix_meal_record_delete_cascade'),
    ]

    operations = [
        # 1. View for full comment details (including username)
        migrations.RunSQL(
            sql="""
            DROP VIEW IF EXISTS view_activity_comment_full;
            CREATE VIEW view_activity_comment_full AS
            SELECT 
                ac.*,
                u.username as user_name
            FROM ActivityComment_activitycomment ac
            JOIN auth_user u ON ac.user_id = u.id;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_activity_comment_full;"
        ),

        # 2. Stored Procedure: Create Comment
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_create_activity_comment;
            CREATE PROCEDURE sp_create_activity_comment(
                IN p_user_id INT,
                IN p_activity_type VARCHAR(20),
                IN p_activity_id INT,
                IN p_content TEXT
            )
            BEGIN
                INSERT INTO ActivityComment_activitycomment (user_id, activity_type, activity_id, content, created_at)
                VALUES (p_user_id, p_activity_type, p_activity_id, p_content, NOW());
                
                SELECT * FROM view_activity_comment_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_activity_comment;"
        ),

        # 3. Stored Procedure: Delete Comment Safe
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_delete_activity_comment_safe;
            CREATE PROCEDURE sp_delete_activity_comment_safe(
                IN p_comment_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_owner_id INT;
                SELECT user_id INTO v_owner_id FROM ActivityComment_activitycomment WHERE id = p_comment_id;
                
                IF v_owner_id IS NULL THEN
                    SELECT 1 AS status_code; -- Not found
                ELSEIF v_owner_id != p_user_id THEN
                    SELECT 2 AS status_code; -- Unauthorized
                ELSE
                    DELETE FROM ActivityComment_activitycomment WHERE id = p_comment_id;
                    SELECT 0 AS status_code; -- Success
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_delete_activity_comment_safe;"
        ),

        # 4. Trigger: Timestamp on Insert
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS tr_activity_comment_timestamp_insert;
            CREATE TRIGGER tr_activity_comment_timestamp_insert
            BEFORE INSERT ON ActivityComment_activitycomment
            FOR EACH ROW
            BEGIN
                IF NEW.created_at IS NULL THEN
                    SET NEW.created_at = NOW();
                END IF;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_activity_comment_timestamp_insert;"
        ),

        # 5. Trigger: User Cascade Delete
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS tr_user_comment_cascade_delete;
            CREATE TRIGGER tr_user_comment_cascade_delete
            BEFORE DELETE ON auth_user
            FOR EACH ROW
            BEGIN
                DELETE FROM ActivityComment_activitycomment WHERE user_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_user_comment_cascade_delete;"
        ),

        # 6. Trigger: Sleep Record Cascade Delete
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS tr_sleep_comment_cascade_delete;
            CREATE TRIGGER tr_sleep_comment_cascade_delete
            BEFORE DELETE ON SleepManage_sleeprecord
            FOR EACH ROW
            BEGIN
                DELETE FROM ActivityComment_activitycomment 
                WHERE activity_type = 'sleep' AND activity_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_sleep_comment_cascade_delete;"
        ),

        # 7. Trigger: Sport Record Cascade Delete
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS tr_sport_comment_cascade_delete;
            CREATE TRIGGER tr_sport_comment_cascade_delete
            BEFORE DELETE ON SportManage_sportrecord
            FOR EACH ROW
            BEGIN
                DELETE FROM ActivityComment_activitycomment 
                WHERE activity_type = 'sport' AND activity_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_sport_comment_cascade_delete;"
        ),

        # 8. Trigger: Meal Record Cascade Delete
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS tr_meal_comment_cascade_delete;
            CREATE TRIGGER tr_meal_comment_cascade_delete
            BEFORE DELETE ON DietManage_mealrecord
            FOR EACH ROW
            BEGIN
                DELETE FROM ActivityComment_activitycomment 
                WHERE activity_type = 'meal' AND activity_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_meal_comment_cascade_delete;"
        ),
    ]
