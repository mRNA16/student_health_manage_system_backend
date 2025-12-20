from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("UserManage", "0016_concurrency_control_procedures"),
    ]

    operations = [
        # 1. Update sp_create_user with Transaction (Multi-table)
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_create_user;
            CREATE PROCEDURE sp_create_user(
                IN p_username VARCHAR(150),
                IN p_password VARCHAR(128),
                IN p_height DOUBLE,
                IN p_weight DOUBLE,
                IN p_gender VARCHAR(10),
                IN p_birthday DATE,
                IN p_realName VARCHAR(150),
                IN p_roles JSON,
                IN p_burn_goal DOUBLE,
                IN p_intake_goal DOUBLE,
                IN p_sleep_goal DOUBLE
            )
            BEGIN
                DECLARE new_user_id INT;
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;

                START TRANSACTION;

                INSERT INTO auth_user 
                (password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
                VALUES (p_password, NULL, 0, p_username, '', '', '', 0, 1, NOW());
                
                SET new_user_id = LAST_INSERT_ID();

                INSERT INTO `usermanage_userprofile`
                (user_id, height, weight, gender, birthday, `realName`, roles, 
                 daily_calories_burn_goal, daily_calories_intake_goal, daily_sleep_hours_goal)
                VALUES (new_user_id, p_height, p_weight, p_gender, p_birthday, p_realName, p_roles, p_burn_goal, p_intake_goal, p_sleep_goal);

                COMMIT;
                
                SELECT new_user_id;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_user;"
        ),

        # 2. Update sp_cancel_friend_request
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_cancel_friend_request;
            CREATE PROCEDURE sp_cancel_friend_request(
                IN p_request_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_from_user_id INT;
                DECLARE v_current_status VARCHAR(20);
                DECLARE v_status INT DEFAULT 0;
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;

                START TRANSACTION;

                SELECT from_user_id, status INTO v_from_user_id, v_current_status 
                FROM usermanage_friend WHERE id = p_request_id FOR UPDATE;

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

                IF v_status = 0 THEN COMMIT; ELSE ROLLBACK; END IF;
                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_cancel_friend_request;"
        ),

        # 3. Update sp_remove_friend_relationship
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_remove_friend_relationship;
            CREATE PROCEDURE sp_remove_friend_relationship(
                IN p_request_id INT,
                IN p_user_id INT
            )
            BEGIN
                DECLARE v_from_user_id INT;
                DECLARE v_to_user_id INT;
                DECLARE v_status INT DEFAULT 0;
                DECLARE EXIT HANDLER FOR SQLEXCEPTION
                BEGIN
                    ROLLBACK;
                END;

                START TRANSACTION;

                SELECT from_user_id, to_user_id INTO v_from_user_id, v_to_user_id 
                FROM usermanage_friend WHERE id = p_request_id FOR UPDATE;

                IF v_from_user_id IS NULL THEN
                    SET v_status = 1; -- 不存在
                ELSEIF v_from_user_id != p_user_id AND v_to_user_id != p_user_id THEN
                    SET v_status = 2; -- 无权删除
                ELSE
                    DELETE FROM usermanage_friend WHERE id = p_request_id;
                    SET v_status = 0;
                END IF;

                IF v_status = 0 THEN COMMIT; ELSE ROLLBACK; END IF;
                SELECT v_status AS status_code;
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_remove_friend_relationship;"
        ),
    ]
