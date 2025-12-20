from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("UserManage", "0010_setup_stored_procedures"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_handle_friend_request(
                IN p_request_id INT,
                IN p_user_id INT,
                IN p_action VARCHAR(10)
            )
            BEGIN
                DECLARE v_to_user_id INT;
                DECLARE v_status INT DEFAULT 0;

                SELECT to_user_id INTO v_to_user_id FROM usermanage_friend WHERE id = p_request_id;

                IF v_to_user_id IS NULL THEN
                    SET v_status = 1; -- 不存在
                ELSEIF v_to_user_id != p_user_id THEN
                    SET v_status = 2; -- 无权操作
                ELSE
                    IF p_action = 'accept' THEN
                        UPDATE usermanage_friend SET status = 'accepted' WHERE id = p_request_id;
                    ELSEIF p_action = 'reject' THEN
                        UPDATE usermanage_friend SET status = 'rejected' WHERE id = p_request_id;
                    END IF;
                    SET v_status = 0;
                END IF;

                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_handle_friend_request;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_send_friend_request(
                IN p_from_user_id INT,
                IN p_to_user_id INT
            )
            BEGIN
                DECLARE v_status INT DEFAULT 0;
                DECLARE v_exists INT;

                IF p_from_user_id = p_to_user_id THEN
                    SET v_status = 1; -- 不能添加自己
                ELSE
                    SELECT COUNT(*) INTO v_exists FROM usermanage_friend 
                    WHERE ((from_user_id = p_from_user_id AND to_user_id = p_to_user_id) 
                       OR (from_user_id = p_to_user_id AND to_user_id = p_from_user_id))
                    AND (status = 'pending' OR status = 'accepted');

                    IF v_exists > 0 THEN
                        SET v_status = 2; -- 已存在关系
                    ELSE
                        INSERT INTO usermanage_friend (from_user_id, to_user_id, status, created_at)
                        VALUES (p_from_user_id, p_to_user_id, 'pending', NOW());
                        SET v_status = 0;
                    END IF;
                END IF;

                SELECT v_status AS status_code;
                IF v_status = 0 THEN
                    SELECT * FROM view_friend_details WHERE id = LAST_INSERT_ID();
                END IF;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_send_friend_request;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_cancel_friend_request(
                IN p_request_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_from_user_id INT;
                DECLARE v_current_status VARCHAR(20);
                DECLARE v_status INT DEFAULT 0;

                SELECT from_user_id, status INTO v_from_user_id, v_current_status FROM usermanage_friend WHERE id = p_request_id;

                IF v_from_user_id IS NULL THEN
                    SET v_status = 1; -- 不存在
                ELSEIF v_from_user_id != p_user_id THEN
                    SET v_status = 2; -- 无权取消
                ELSEIF v_current_status != 'pending' THEN
                    SET v_status = 3; -- 非待处理状态
                ELSE
                    DELETE FROM usermanage_friend WHERE id = p_request_id;
                    SET v_status = 0;
                END IF;

                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_cancel_friend_request;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_remove_friend_relationship(
                IN p_request_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_from_user_id INT;
                DECLARE v_to_user_id INT;
                DECLARE v_status INT DEFAULT 0;

                SELECT from_user_id, to_user_id INTO v_from_user_id, v_to_user_id FROM usermanage_friend WHERE id = p_request_id;

                IF v_from_user_id IS NULL THEN
                    SET v_status = 1; -- 不存在
                ELSEIF v_from_user_id != p_user_id AND v_to_user_id != p_user_id THEN
                    SET v_status = 2; -- 无权删除
                ELSE
                    DELETE FROM usermanage_friend WHERE id = p_request_id;
                    SET v_status = 0;
                END IF;

                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_remove_friend_relationship;",
        ),
    ]
