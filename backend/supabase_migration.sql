-- Migration: Add custom_schemas and custom_entries tables
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
CREATE POLICY "anon_read_custom_schemas" ON custom_schemas FOR SELECT USING (true);
CREATE POLICY "anon_insert_custom_schemas" ON custom_schemas FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_update_custom_schemas" ON custom_schemas FOR UPDATE USING (true);
CREATE POLICY "anon_read_custom_entries" ON custom_entries FOR SELECT USING (true);
CREATE POLICY "anon_insert_custom_entries" ON custom_entries FOR INSERT WITH CHECK (true);
CREATE POLICY "anon_delete_custom_entries" ON custom_entries FOR DELETE USING (true);
