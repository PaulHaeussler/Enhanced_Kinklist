ALTER TABLE answers
  ADD COLUMN IF NOT EXISTS answer_context VARCHAR(64) NOT NULL DEFAULT 'realistic_adult_partner' AFTER shown_item_ids,
  ADD COLUMN IF NOT EXISTS partner_personas JSON NULL AFTER answer_context;
