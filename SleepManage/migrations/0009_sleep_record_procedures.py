from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("SleepManage", "0008_sleep_record_safe_procedures"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_create_sleep_record(
                IN p_user_id INT,
                IN p_date DATE,
                IN p_sleep_time TIME,
                IN p_wake_time TIME
            )
            BEGIN
                INSERT INTO sleepmanage_sleeprecord (user_id, date, sleep_time, wake_time, duration, created_at)
                VALUES (p_user_id, p_date, p_sleep_time, p_wake_time, 0, NOW());
                
                SELECT * FROM sleepmanage_sleeprecord WHERE id = LAST_INSERT_ID();
            END;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_create_sleep_record;",
        )
    ]
