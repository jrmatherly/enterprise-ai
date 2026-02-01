-- Enterprise AI Platform - Database Initialization
-- This script runs automatically when PostgreSQL container first starts

-- Note: The 'langfuse' database is created by POSTGRES_DB env var in docker-compose
-- This script creates the 'eai' database for our application

-- Create the EAI application database (idempotent)
SELECT 'CREATE DATABASE eai'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'eai')\gexec

-- Connect to the eai database and add extensions
\c eai

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create extension for crypto functions (used by some auth implementations)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create extension for vector operations (if using pgvector later)
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- Add extensions to the langfuse database as well
\c langfuse

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
