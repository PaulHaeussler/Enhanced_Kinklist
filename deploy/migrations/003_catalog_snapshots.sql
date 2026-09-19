CREATE TABLE IF NOT EXISTS catalog_snapshots (
  catalog_id VARCHAR(64) NOT NULL,
  catalog_version VARCHAR(64) NOT NULL,
  data JSON NOT NULL,
  created BIGINT NOT NULL,
  PRIMARY KEY (catalog_id, catalog_version)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;
