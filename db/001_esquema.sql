-- Esquema de la BD a3i (Sprint 1): tablas perfil y usuario

SET NAMES utf8mb4;

DROP DATABASE IF EXISTS a3i;
CREATE DATABASE a3i CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE a3i;

CREATE TABLE perfil (
    id_perfil INT         NOT NULL AUTO_INCREMENT,
    nombre    VARCHAR(20) NOT NULL,
    CONSTRAINT pk_perfil        PRIMARY KEY (id_perfil),
    CONSTRAINT uq_perfil_nombre UNIQUE (nombre)
) ENGINE = InnoDB;

INSERT INTO perfil (nombre) VALUES ('cientificos'), ('seguridad'), ('tech');

-- intentos_fallidos y estado son para el bloqueo de cuenta
CREATE TABLE usuario (
    id_usuario        INT              NOT NULL AUTO_INCREMENT,
    nombre            VARCHAR(50)      NOT NULL,
    login             VARCHAR(30)      NOT NULL,
    hash_contrasena   VARCHAR(255)     NOT NULL,
    intentos_fallidos TINYINT UNSIGNED NOT NULL DEFAULT 0,
    estado            ENUM('activo', 'bloqueado', 'desactivado') NOT NULL DEFAULT 'activo',
    rango             ENUM('empleado', 'jefe_sector', 'subjefe_sector',
                           'jefe_perfil', 'subjefe_perfil') NOT NULL,
    nivel             TINYINT          NOT NULL DEFAULT 1,
    id_perfil         INT              NOT NULL,
    CONSTRAINT pk_usuario       PRIMARY KEY (id_usuario),
    CONSTRAINT uq_usuario_login UNIQUE (login),
    CONSTRAINT ck_usuario_nivel CHECK (nivel BETWEEN 1 AND 4),
    CONSTRAINT fk_usuario_perfil FOREIGN KEY (id_perfil) REFERENCES perfil (id_perfil)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB;
