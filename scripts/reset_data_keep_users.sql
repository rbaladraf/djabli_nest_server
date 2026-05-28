-- Reset all application tables to empty, except `users` (and `alembic_version`).
-- Intended for development/staging environments.
-- Usage (docker): docker compose exec -T postgres psql -U djabli -d djablinest < ./scripts/reset_data_keep_users.sql

DO $$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename NOT IN ('users', 'alembic_version')
  LOOP
    EXECUTE format('TRUNCATE TABLE public.%I RESTART IDENTITY CASCADE;', r.tablename);
  END LOOP;
END $$;

