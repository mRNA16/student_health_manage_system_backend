from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("UserManage", "0012_friend_activity_procedures"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER tr_auto_self_friend
            AFTER INSERT ON auth_user
            FOR EACH ROW
            BEGIN
                INSERT INTO usermanage_friend (from_user_id, to_user_id, status, created_at)
                VALUES (NEW.id, NEW.id, 'accepted', NOW());
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS tr_auto_self_friend;",
        ),
    ]
