from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ActivityComment", "0003_activity_comment_native_sql"),
    ]

    operations = [
        # 1. Update sp_create_activity_comment
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
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;

                START TRANSACTION;
                INSERT INTO ActivityComment_activitycomment (user_id, activity_type, activity_id, content, created_at)
                VALUES (p_user_id, p_activity_type, p_activity_id, p_content, NOW());
                COMMIT;
                
                SELECT * FROM view_activity_comment_full WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_activity_comment;"
        ),

        # 2. Update sp_delete_activity_comment_safe
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_delete_activity_comment_safe;
            CREATE PROCEDURE sp_delete_activity_comment_safe(
                IN p_comment_id INT,
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
                SELECT user_id INTO v_owner_id FROM ActivityComment_activitycomment WHERE id = p_comment_id FOR UPDATE;
                
                IF v_owner_id IS NULL THEN
                    SET v_status = 1; -- Not found
                ELSEIF v_owner_id != p_user_id THEN
                    SET v_status = 2; -- Unauthorized
                ELSE
                    DELETE FROM ActivityComment_activitycomment WHERE id = p_comment_id;
                    SET v_status = 0;
                END IF;

                IF v_status = 0 THEN COMMIT; ELSE ROLLBACK; END IF;
                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_delete_activity_comment_safe;"
        ),
    ]
