CREATE SCHEMA IF NOT EXISTS kl COLLATE utf8mb4_unicode_ci;
USE kl;

CREATE TABLE IF NOT EXISTS users (
  id INT NOT NULL AUTO_INCREMENT,
  user VARCHAR(36) NULL,
  username VARCHAR(200) NULL,
  sex VARCHAR(15) NULL,
  age INT NULL,
  fap_freq VARCHAR(100) NULL,
  sex_freq VARCHAR(100) NULL,
  body_count VARCHAR(45) NULL,
  ip VARCHAR(45) NULL,
  created VARCHAR(45) NULL,
  PRIMARY KEY (id),
  KEY users_user_idx (user)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS choices (
  id INT NOT NULL,
  name VARCHAR(60) NOT NULL,
  PRIMARY KEY (id)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

INSERT IGNORE INTO choices(id, name) VALUES
  (-1, "Confused"),
  (0, "Not applicable/entered"),
  (1, "Have tried - Favorite"),
  (2, "Have tried - Liked"),
  (3, "Have tried - Was okay"),
  (4, "Have tried - Didn't like"),
  (5, "Have tried - Hated"),
  (6, "Haven't tried - Would love to try"),
  (7, "Haven't tried - Would want to try"),
  (8, "Haven't tried - Indifferent to it"),
  (9, "Haven't tried - Might try"),
  (10, "Haven't tried - Won't ever try");

CREATE TABLE IF NOT EXISTS answers (
  user_id INT NOT NULL,
  timestamp BIGINT NOT NULL,
  token VARCHAR(36) NOT NULL,
  choices_json JSON NOT NULL,
  hit_count INT NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, timestamp),
  UNIQUE KEY answers_token_idx (token),
  KEY answers_user_id_idx (user_id),
  CONSTRAINT answers_user_id_fk FOREIGN KEY (user_id) REFERENCES users (id)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hits (
  id BIGINT NOT NULL AUTO_INCREMENT,
  ip VARCHAR(45) NULL,
  timestamp BIGINT NULL,
  url VARCHAR(200) NULL,
  sec_ch_ua VARCHAR(255) NULL,
  sec_ch_ua_mobile VARCHAR(32) NULL,
  sec_ch_ua_platform VARCHAR(64) NULL,
  user_agent VARCHAR(512) NULL,
  accept_language VARCHAR(255) NULL,
  path VARCHAR(255) NULL,
  query VARCHAR(2048) NULL,
  PRIMARY KEY (id),
  KEY hits_timestamp_idx (timestamp),
  KEY hits_path_idx (path)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS suggestions (
  timestamp BIGINT NOT NULL,
  suggestion TEXT NOT NULL,
  ip VARCHAR(45) NULL
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stats (
  id BIGINT NOT NULL AUTO_INCREMENT,
  data JSON NOT NULL,
  created DOUBLE NOT NULL,
  PRIMARY KEY (id),
  KEY stats_created_idx (created)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS error_logs (
  id BIGINT NOT NULL AUTO_INCREMENT,
  timestamp BIGINT NOT NULL,
  error_type VARCHAR(64) NOT NULL,
  message TEXT NOT NULL,
  ip VARCHAR(45) NULL,
  user_agent VARCHAR(512) NULL,
  data JSON NULL,
  PRIMARY KEY (id),
  KEY error_logs_timestamp_idx (timestamp),
  KEY error_logs_type_idx (error_type)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;
