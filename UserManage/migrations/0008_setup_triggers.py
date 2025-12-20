from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("UserManage", "0007_alter_friend_created_at_alter_friend_from_user_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER set_friend_created_at
            BEFORE INSERT ON usermanage_friend
            FOR EACH ROW
            BEGIN
                IF NEW.created_at IS NULL THEN
                    SET NEW.created_at = NOW();
                END IF;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS set_friend_created_at;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER user_cascade_delete
            BEFORE DELETE ON auth_user
            FOR EACH ROW
            BEGIN
                DELETE FROM usermanage_friend 
                WHERE from_user_id = OLD.id OR to_user_id = OLD.id;
                
                DELETE FROM usermanage_userprofile 
                WHERE user_id = OLD.id;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS user_cascade_delete;",
        ),
    ]
