from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Enable RLS and revoke public Data API roles on Supabase public tables."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write(self.style.WARNING("lockdown_db skipped: database is not PostgreSQL."))
            return

        with connection.cursor() as cursor:
            cursor.execute(
                """
                select tablename
                from pg_tables
                where schemaname = 'public'
                """
            )
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                cursor.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')

            cursor.execute("select rolname from pg_roles where rolname in ('anon', 'authenticated')")
            roles = [row[0] for row in cursor.fetchall()]
            for role in roles:
                cursor.execute(f'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM "{role}"')
                cursor.execute(f'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM "{role}"')
                cursor.execute(f'REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM "{role}"')

        self.stdout.write(self.style.SUCCESS(f"Locked down {len(tables)} public tables."))
