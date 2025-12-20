from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("SleepManage", "0005_delete_comment"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_sleep_record_duration_insert
            BEFORE INSERT ON sleepmanage_sleeprecord
            FOR EACH ROW
            BEGIN
                DECLARE st DATETIME;
                DECLARE wt DATETIME;
                SET st = CAST(CONCAT(NEW.date, ' ', NEW.sleep_time) AS DATETIME);
                SET wt = CAST(CONCAT(NEW.date, ' ', NEW.wake_time) AS DATETIME);
                IF wt < st THEN
                    SET wt = DATE_ADD(wt, INTERVAL 1 DAY);
                END IF;
                SET NEW.duration = TIMESTAMPDIFF(SECOND, st, wt) / 3600.0;
                IF NEW.created_at IS NULL THEN
                    SET NEW.created_at = NOW();
                END IF;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_sleep_record_duration_insert;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_sleep_record_duration_update
            BEFORE UPDATE ON sleepmanage_sleeprecord
            FOR EACH ROW
            BEGIN
                DECLARE st DATETIME;
                DECLARE wt DATETIME;
                SET st = CAST(CONCAT(NEW.date, ' ', NEW.sleep_time) AS DATETIME);
                SET wt = CAST(CONCAT(NEW.date, ' ', NEW.wake_time) AS DATETIME);
                IF wt < st THEN
                    SET wt = DATE_ADD(wt, INTERVAL 1 DAY);
                END IF;
                SET NEW.duration = TIMESTAMPDIFF(SECOND, st, wt) / 3600.0;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_sleep_record_duration_update;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_sleep_record_cascade_delete
            BEFORE DELETE ON auth_user
            FOR EACH ROW
            BEGIN
                DELETE FROM sleepmanage_sleeprecord WHERE user_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_sleep_record_cascade_delete;",
        ),
    ]
