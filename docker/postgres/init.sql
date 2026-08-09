-- PostgreSQL initialization script
-- Runs once when the container is first created.
-- Creates required extensions for UUID generation and cryptography.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for password hashing helpers (used as fallback)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pg_stat_statements for query performance monitoring
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Set default timezone to UTC
SET timezone = 'UTC';
