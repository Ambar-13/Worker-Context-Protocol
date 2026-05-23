-- WCP coordinator initial Postgres schema bootstrap.
--
-- Idempotent: safe to apply on a fresh DB or on a DB the coordinator
-- has already initialised. The coordinator process itself runs proper
-- migrations on startup; this file exists so the DB has the database,
-- roles, and extensions ready when the coordinator first connects.

-- Required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Read-only role for Grafana / external dashboards
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'wcp_readonly') THEN
        CREATE ROLE wcp_readonly LOGIN PASSWORD 'wcp_readonly_placeholder';
        GRANT CONNECT ON DATABASE wcp TO wcp_readonly;
    END IF;
END
$$;

-- Permissions tightening: the coordinator's app user owns its tables;
-- wcp_readonly gets SELECT on the public schema once the coordinator
-- creates its tables. This block is run as a no-op pre-flight; the
-- coordinator's own migration grants the actual privileges.

-- Marker row so operators can verify the bootstrap ran
CREATE TABLE IF NOT EXISTS _bootstrap_marker (
    id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    applied_at  timestamptz NOT NULL DEFAULT now(),
    version     text NOT NULL
);
INSERT INTO _bootstrap_marker (version) VALUES ('hosted-test-coordinator-v0.85');
