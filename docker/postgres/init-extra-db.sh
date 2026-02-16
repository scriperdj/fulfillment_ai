#!/bin/bash
# Create a database matching the username so default connections don't fail.
# Postgres defaults to database=username when no DB is specified.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE fulfillment'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'fulfillment')\gexec
EOSQL
