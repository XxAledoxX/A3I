-- Esquema de la BD a3i (Sprint 1): tablas role y user

SET NAMES utf8mb4;

DROP DATABASE IF EXISTS a3i;
CREATE DATABASE a3i CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE a3i;

-- Perfiles de usuario
CREATE TABLE `role` (
    `id_role` INT         NOT NULL AUTO_INCREMENT,
    `name`    VARCHAR(20) NOT NULL,
    CONSTRAINT pk_role      PRIMARY KEY (`id_role`),
    CONSTRAINT uq_role_name UNIQUE (`name`)
) ENGINE = InnoDB;

INSERT INTO `role` (`name`) VALUES ('scientist'), ('security'), ('tech');

-- Usuarios. failed_attempts y state son para el bloqueo de cuenta
CREATE TABLE `user` (
    `id_user`         INT              NOT NULL AUTO_INCREMENT,
    `name`            VARCHAR(50)      NOT NULL,
    `login`           VARCHAR(30)      NOT NULL,
    `password_hash`   VARCHAR(255)     NOT NULL,
    `failed_attempts` TINYINT UNSIGNED NOT NULL DEFAULT 0,
    `state`           ENUM('active', 'blocked', 'deactivated') NOT NULL DEFAULT 'active',
    `rank`            ENUM('worker', 'sector_manager', 'sector_submanager',
                           'profile_manager', 'profile_submanager') NOT NULL,
    `sec_level`       TINYINT          NOT NULL DEFAULT 1,
    `id_role`         INT              NOT NULL,
    CONSTRAINT pk_user           PRIMARY KEY (`id_user`),
    CONSTRAINT uq_user_login     UNIQUE (`login`),
    CONSTRAINT ck_user_sec_level CHECK (`sec_level` BETWEEN 1 AND 4),
    CONSTRAINT fk_user_role      FOREIGN KEY (`id_role`) REFERENCES `role` (`id_role`)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB;
