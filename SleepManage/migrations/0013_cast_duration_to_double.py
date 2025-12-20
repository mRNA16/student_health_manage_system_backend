from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("SleepManage", "0012_refactor_to_3nf"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER VIEW view_sleep_record_full AS
            SELECT 
                id, user_id, date, sleep_time, wake_time, created_at,
                CAST(
                    (TIMESTAMPDIFF(SECOND, 
                        CAST(CONCAT(date, ' ', sleep_time) AS DATETIME),
                        IF(wake_time < sleep_time, 
                           DATE_ADD(CAST(CONCAT(date, ' ', wake_time) AS DATETIME), INTERVAL 1 DAY),
                           CAST(CONCAT(date, ' ', wake_time) AS DATETIME)
                        )
                    ) / 3600.0) 
                AS DOUBLE) AS duration
            FROM sleepmanage_sleeprecord;
            """,
            reverse_sql="""
            ALTER VIEW view_sleep_record_full AS
            SELECT 
                id, user_id, date, sleep_time, wake_time, created_at,
                (TIMESTAMPDIFF(SECOND, 
                    CAST(CONCAT(date, ' ', sleep_time) AS DATETIME),
                    IF(wake_time < sleep_time, 
                       DATE_ADD(CAST(CONCAT(date, ' ', wake_time) AS DATETIME), INTERVAL 1 DAY),
                       CAST(CONCAT(date, ' ', wake_time) AS DATETIME)
                    )
                ) / 3600.0) AS duration
            FROM sleepmanage_sleeprecord;
            """,
        ),
    ]
