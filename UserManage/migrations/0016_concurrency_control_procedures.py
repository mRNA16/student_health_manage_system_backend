from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("UserManage", "0015_fix_friend_activities_sp"),
    ]

    operations = [
        # 1. Update sp_handle_friend_request with Row Locking
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_handle_friend_request;
            CREATE PROCEDURE sp_handle_friend_request(
                IN p_request_id INT,
                IN p_user_id INT,
                IN p_action VARCHAR(10)
            )
            BEGIN
                DECLARE v_to_user_id INT;
                DECLARE v_status INT DEFAULT 0;
                DECLARE v_current_status VARCHAR(10);

                -- Start Transaction for Concurrency Control
                START TRANSACTION;

                -- Use FOR UPDATE to lock the specific row to prevent race conditions
                SELECT to_user_id, status INTO v_to_user_id, v_current_status 
                FROM usermanage_friend 
                WHERE id = p_request_id 
                FOR UPDATE;

                IF v_to_user_id IS NULL THEN
                    SET v_status = 1; -- Not found
                    ROLLBACK;
                ELSEIF v_to_user_id != p_user_id THEN
                    SET v_status = 2; -- Unauthorized
                    ROLLBACK;
                ELSEIF v_current_status != 'pending' THEN
                    SET v_status = 3; -- Already processed
                    ROLLBACK;
                ELSE
                    IF p_action = 'accept' THEN
                        UPDATE usermanage_friend SET status = 'accepted' WHERE id = p_request_id;
                    ELSEIF p_action = 'reject' THEN
                        UPDATE usermanage_friend SET status = 'rejected' WHERE id = p_request_id;
                    END IF;
                    SET v_status = 0;
                    COMMIT;
                END IF;

                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_handle_friend_request;",
        ),

        # 2. Update sp_send_friend_request with Named Locks (Advanced Concurrency Control)
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_send_friend_request;
            CREATE PROCEDURE sp_send_friend_request(
                IN p_from_user_id INT,
                IN p_to_user_id INT
            )
            BEGIN
                DECLARE v_status INT DEFAULT 0;
                DECLARE v_exists INT;
                DECLARE v_lock_name VARCHAR(100);
                DECLARE v_lock_res INT;

                -- Create a unique lock name for this pair of users (sorted to avoid deadlocks)
                SET v_lock_name = CONCAT('friend_lock_', 
                                         IF(p_from_user_id < p_to_user_id, p_from_user_id, p_to_user_id), 
                                         '_', 
                                         IF(p_from_user_id < p_to_user_id, p_to_user_id, p_from_user_id));

                -- Acquire a named lock to prevent concurrent requests between the same two users
                SELECT GET_LOCK(v_lock_name, 5) INTO v_lock_res;

                IF v_lock_res = 1 THEN
                    START TRANSACTION;
                    
                    IF p_from_user_id = p_to_user_id THEN
                        SET v_status = 1; -- Cannot add self
                    ELSE
                        -- Check for existing relationship in EITHER direction
                        SELECT COUNT(*) INTO v_exists FROM usermanage_friend 
                        WHERE ((from_user_id = p_from_user_id AND to_user_id = p_to_user_id) 
                           OR (from_user_id = p_to_user_id AND to_user_id = p_from_user_id))
                        AND (status = 'pending' OR status = 'accepted');

                        IF v_exists > 0 THEN
                            SET v_status = 2; -- Already exists
                        ELSE
                            INSERT INTO usermanage_friend (from_user_id, to_user_id, status, created_at)
                            VALUES (p_from_user_id, p_to_user_id, 'pending', NOW());
                            SET v_status = 0;
                        END IF;
                    END IF;

                    IF v_status = 0 THEN
                        COMMIT;
                    ELSE
                        ROLLBACK;
                    END IF;
                    
                    -- Release the named lock
                    SELECT RELEASE_LOCK(v_lock_name) INTO v_lock_res;
                ELSE
                    SET v_status = 4; -- Could not acquire lock (timeout)
                END IF;

                SELECT v_status AS status_code;
                IF v_status = 0 THEN
                    SELECT * FROM view_friend_details WHERE id = LAST_INSERT_ID();
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_send_friend_request;",
        ),

        # 3. Procedure for Safe Activity Viewing (Demonstrating Shared Locks)
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_get_friend_activities_safe_v2;
            CREATE PROCEDURE sp_get_friend_activities_safe_v2(
                IN p_user_id INT,
                IN p_friend_id INT
            )
            BEGIN
                DECLARE v_is_friend INT DEFAULT 0;
                DECLARE v_status INT DEFAULT 0;

                START TRANSACTION;

                -- Use LOCK IN SHARE MODE to ensure we read a consistent state 
                -- even if other transactions are trying to modify friendship status
                IF p_user_id = p_friend_id THEN
                    SET v_is_friend = 1;
                ELSE
                    SELECT COUNT(*) INTO v_is_friend FROM usermanage_friend 
                    WHERE ((from_user_id = p_user_id AND to_user_id = p_friend_id) 
                       OR (from_user_id = p_friend_id AND to_user_id = p_user_id))
                    AND status = 'accepted'
                    LOCK IN SHARE MODE;
                END IF;

                IF NOT EXISTS (SELECT 1 FROM auth_user WHERE id = p_friend_id) THEN
                    SET v_status = 1;
                ELSEIF v_is_friend = 0 THEN
                    SET v_status = 2;
                ELSE
                    SET v_status = 0;
                END IF;

                SELECT v_status AS status_code;

                IF v_status = 0 THEN
                    SELECT id, username FROM auth_user WHERE id = p_friend_id;
                    
                    (SELECT id, 'sport' AS type, CAST(sport AS CHAR) AS detail, duration, created_at 
                     FROM view_sport_record_full WHERE user_id = p_friend_id)
                    UNION ALL
                    (SELECT id, 'sleep' AS type, NULL AS detail, duration, created_at 
                     FROM view_sleep_record_full WHERE user_id = p_friend_id)
                    UNION ALL
                    (SELECT id, 'meal' AS type, meal AS detail, total_calories AS duration, created_at 
                     FROM view_meal_record_full WHERE user_id = p_friend_id)
                    ORDER BY created_at DESC;
                END IF;
                
                COMMIT;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_get_friend_activities_safe_v2;",
        ),
    ]
