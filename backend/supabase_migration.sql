-- Migration: Add custom_schemas, custom_entries, and camera_photos tables
-- Run this in Supabase SQL Editor to complete the Supabase setup

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

-- Enable RLS
ALTER TABLE custom_schemas ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_entries ENABLE ROW LEVEL SECURITY;

-- Public read/write for anon key (service_role already has full access)
CREATE POLICY IF NOT EXISTS "anon_read_custom_schemas" ON custom_schemas FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "anon_insert_custom_schemas" ON custom_schemas FOR INSERT WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "anon_update_custom_schemas" ON custom_schemas FOR UPDATE USING (true);
CREATE POLICY IF NOT EXISTS "anon_read_custom_entries" ON custom_entries FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "anon_insert_custom_entries" ON custom_entries FOR INSERT WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "anon_delete_custom_entries" ON custom_entries FOR DELETE USING (true);

-- Camera photos table (saved via camera_control save action)
CREATE TABLE IF NOT EXISTS camera_photos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    description TEXT DEFAULT '',
    file_path TEXT NOT NULL,
    facing TEXT DEFAULT 'user'
);

ALTER TABLE camera_photos ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "anon_read_camera_photos" ON camera_photos FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "anon_insert_camera_photos" ON camera_photos FOR INSERT WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "anon_delete_camera_photos" ON camera_photos FOR DELETE USING (true);
