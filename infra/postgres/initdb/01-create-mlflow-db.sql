-- Create the MLflow backend-store database on the shared Timescale
-- Postgres instance (add-ops-stack task 5.2 — "separate database").
--
-- Runs via the postgres image's /docker-entrypoint-initdb.d hook, which
-- only executes on a *fresh* data volume. Existing deployments must
-- create the database manually:
--     docker exec -it noether-timescaledb \
--       psql -U "$POSTGRES_USER" -c 'CREATE DATABASE mlflow;'
--
-- The \gexec guard keeps this idempotent if it is ever re-run by hand.
SELECT 'CREATE DATABASE mlflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec
