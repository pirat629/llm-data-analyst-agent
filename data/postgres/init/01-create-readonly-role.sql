DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analytics_reader') THEN
        CREATE ROLE analytics_reader LOGIN PASSWORD 'analytics_reader';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE analytics_db TO analytics_reader;
GRANT USAGE ON SCHEMA public TO analytics_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT ON TABLES TO analytics_reader;
ALTER ROLE analytics_reader SET default_transaction_read_only = on;
ALTER ROLE analytics_reader SET statement_timeout = '10s';
