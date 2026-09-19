ALTER TABLE answers
  ADD COLUMN IF NOT EXISTS catalog_id VARCHAR(64) NOT NULL DEFAULT 'main' AFTER hit_count,
  ADD COLUMN IF NOT EXISTS catalog_version VARCHAR(64) NOT NULL DEFAULT 'legacy' AFTER catalog_id,
  ADD COLUMN IF NOT EXISTS max_spice_level TINYINT NULL AFTER catalog_version,
  ADD COLUMN IF NOT EXISTS shown_item_ids JSON NULL AFTER max_spice_level;

CREATE INDEX IF NOT EXISTS answers_catalog_idx ON answers (catalog_id, catalog_version);
