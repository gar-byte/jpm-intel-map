-- init_db.sql

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id text UNIQUE NOT NULL,
  title text,
  description text,
  event_type text,
  timestamp timestamptz,
  latitude double precision,
  longitude double precision,
  source text,
  confidence double precision
);
