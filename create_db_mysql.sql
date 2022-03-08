CREATE SCHEMA kl COLLATE utf8mb4_unicode_ci;

CREATE TABLE `kl`.`users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user` VARCHAR(36) NULL,
  `username` VARCHAR(200) NULL,
  `sex` VARCHAR(15) NULL,
  `age` INT NULL,
  `fap_freq` VARCHAR(100) NULL,
  `sex_freq` VARCHAR(100) NULL,
  `body_count` VARCHAR(45) NULL,
  `ip` VARCHAR(45) NULL,
  `created` VARCHAR(45) NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


CREATE TABLE `kl`.`choices` (
  `id` INT NOT NULL,
  `name` VARCHAR(60) NOT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

INSERT INTO kl.choices(id, name) VALUES(-1, "Confused"),(0, "Not applicable/entered"),(1, "Have tried - Favorite"),(2, "Have tried - Liked"),(3, "Have tried - Was okay"),(4, "Have tried - Didn't like"),(5, "Have tried - Hated"),(6, "Haven't tried - Would love to try"),(7, "Haven't tried - Would want to try"),(8, "Haven't tried - Indifferent to it"),(9, "Haven't tried - Might try"),(10, "Haven't tried - Won't ever try");


CREATE TABLE `kl`.`answers` (
  `user_id` INT NOT NULL,
  `timestamp` BIGINT NOT NULL,
  `token` VARCHAR(36) NOT NULL,
  `choices_json` JSON NOT NULL,
  PRIMARY KEY (`user_id`, `timestamp`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;
