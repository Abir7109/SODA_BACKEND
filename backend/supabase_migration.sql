-- Migration: Add custom_schemas, custom_entries, and camera_photos tables
-- Safe to re-run (checks existence before creating)

-- Custom memory schemas (created by Gemini at runtime)
CREATE TABLE IF NOT EXISTS custom_schemas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    columns JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Custom schema entries
CREATE TABLE IF NOT EXISTS custom_entries (
    id TEXT PRIMARY KEY,
    schema_name TEXT NOT NULL REFERENCES custom_schemas(name) ON DELETE CASCADE,
    data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_custom_entries_schema ON custom_entries(schema_name);

-- Camera photos table (saved via camera_control save action)
CREATE TABLE IF NOT EXISTS camera_photos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    description TEXT DEFAULT '',
    file_path TEXT NOT NULL,
    facing TEXT DEFAULT 'user'
);

-- Add missing created_at columns to tables created without them
ALTER TABLE facts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE people ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE lessons ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE conversation_summaries ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Enable RLS
ALTER TABLE custom_schemas ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE camera_photos ENABLE ROW LEVEL SECURITY;

-- Create policies only if they don't exist yet
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_read_custom_schemas') THEN
    CREATE POLICY "anon_read_custom_schemas" ON custom_schemas FOR SELECT USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_insert_custom_schemas') THEN
    CREATE POLICY "anon_insert_custom_schemas" ON custom_schemas FOR INSERT WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_update_custom_schemas') THEN
    CREATE POLICY "anon_update_custom_schemas" ON custom_schemas FOR UPDATE USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_read_custom_entries') THEN
    CREATE POLICY "anon_read_custom_entries" ON custom_entries FOR SELECT USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_insert_custom_entries') THEN
    CREATE POLICY "anon_insert_custom_entries" ON custom_entries FOR INSERT WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_delete_custom_entries') THEN
    CREATE POLICY "anon_delete_custom_entries" ON custom_entries FOR DELETE USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_read_camera_photos') THEN
    CREATE POLICY "anon_read_camera_photos" ON camera_photos FOR SELECT USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_insert_camera_photos') THEN
    CREATE POLICY "anon_insert_camera_photos" ON camera_photos FOR INSERT WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_delete_camera_photos') THEN
    CREATE POLICY "anon_delete_camera_photos" ON camera_photos FOR DELETE USING (true);
  END IF;
END $$;
