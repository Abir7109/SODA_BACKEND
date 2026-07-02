-- Supabase Schema for SODA Memory System
-- Run this in the Supabase SQL Editor to set up the tables.
-- Uses UUID primary keys, timestamptz, and jsonb for flexibility.

-- 1. Profiles — one row per user
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL DEFAULT 'Sir',
  creator TEXT DEFAULT '',
  nationality TEXT DEFAULT '',
  language TEXT DEFAULT 'en',
  preferences JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Allow anon access (single-user app)
CREATE POLICY "Allow all on profiles"
  ON profiles FOR ALL
  USING (true)
  WITH CHECK (true);

-- 2. Facts — key-value memory entries with optional category
CREATE TABLE IF NOT EXISTS facts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  category TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE facts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on facts"
  ON facts FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_facts_key ON facts (key);
CREATE INDEX IF NOT EXISTS idx_facts_category ON facts (category);

-- 3. People — information about people the user knows
CREATE TABLE IF NOT EXISTS people (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  relationship TEXT DEFAULT '',
  traits TEXT DEFAULT '',
  preferences TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE people ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on people"
  ON people FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_people_name ON people (name);

-- 4. Lessons — learned corrections from feedback
CREATE TABLE IF NOT EXISTS lessons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  situation TEXT NOT NULL UNIQUE,
  correction TEXT NOT NULL,
  count INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on lessons"
  ON lessons FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_lessons_situation ON lessons (situation);

-- 5. Conversation summaries — per-session takeaways
CREATE TABLE IF NOT EXISTS conversation_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL,
  summary JSONB DEFAULT '{}',
  topics TEXT[] DEFAULT '{}',
  exchange_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on conversation_summaries"
  ON conversation_summaries FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_summaries_session ON conversation_summaries (session_id);

-- 6. Custom schemas — dynamically created memory structures by Gemini
CREATE TABLE IF NOT EXISTS custom_schemas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT DEFAULT '',
  columns JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE custom_schemas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on custom_schemas"
  ON custom_schemas FOR ALL
  USING (true)
  WITH CHECK (true);

-- 7. Custom entries — data stored in custom schemas
CREATE TABLE IF NOT EXISTS custom_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_name TEXT NOT NULL REFERENCES custom_schemas(name) ON DELETE CASCADE,
  data JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE custom_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on custom_entries"
  ON custom_entries FOR ALL
  USING (true)
  WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_custom_entries_schema ON custom_entries (schema_name);
CREATE INDEX IF NOT EXISTS idx_custom_entries_data ON custom_entries USING gin (data);
