from django.db import migrations


FORWARD_SQL = """
DO $$
DECLARE
    constraint_name text;
BEGIN
    FOR constraint_name IN
        SELECT tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_name = 'django_admin_log'
          AND tc.constraint_type = 'FOREIGN KEY'
          AND kcu.column_name = 'user_id'
    LOOP
        EXECUTE format(
            'ALTER TABLE django_admin_log DROP CONSTRAINT %I',
            constraint_name
        );
    END LOOP;
END
$$;

ALTER TABLE django_admin_log
ADD CONSTRAINT django_admin_log_user_id_customuser_fk
FOREIGN KEY (user_id) REFERENCES users_customuser (id);
"""

REVERSE_SQL = """
ALTER TABLE django_admin_log
DROP CONSTRAINT IF EXISTS django_admin_log_user_id_customuser_fk;

ALTER TABLE django_admin_log
ADD CONSTRAINT django_admin_log_user_id_auth_user_fk
FOREIGN KEY (user_id) REFERENCES auth_user (id);
"""


class Migration(migrations.Migration):

    dependencies = [
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
