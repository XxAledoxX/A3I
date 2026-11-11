-- Esquema de la planta: dispositivos, sensores, actuadores, variables y lecturas

SET NAMES utf8mb4;
USE a3i;

-- visible_todos: lo ven todos sin mirar perfil, sector ni nivel (la llama)
CREATE TABLE dispositivo (
    id_dispositivo INT         NOT NULL AUTO_INCREMENT,
    nombre         VARCHAR(50) NOT NULL,
    estado         ENUM('operativo', 'a_revisar', 'mantenimiento', 'sin_conexion')
                               NOT NULL DEFAULT 'operativo',
    visible_todos  BOOLEAN     NOT NULL DEFAULT FALSE,
    id_sector      INT         NOT NULL,
    CONSTRAINT pk_dispositivo        PRIMARY KEY (id_dispositivo),
    CONSTRAINT uq_dispositivo_nombre UNIQUE (nombre),
    CONSTRAINT fk_dispositivo_sector FOREIGN KEY (id_sector) REFERENCES sector (id_sector)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE sensor (
    id_dispositivo     INT               NOT NULL,
    intervalo_segundos SMALLINT UNSIGNED NOT NULL DEFAULT 5,
    CONSTRAINT pk_sensor             PRIMARY KEY (id_dispositivo),
    CONSTRAINT fk_sensor_dispositivo FOREIGN KEY (id_dispositivo)
        REFERENCES dispositivo (id_dispositivo)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB;

-- consigna y posicion en %; la barrera solo usa 0 (cerrada) o 100 (abierta)
CREATE TABLE actuador (
    id_dispositivo INT              NOT NULL,
    consigna       TINYINT UNSIGNED NOT NULL DEFAULT 0,
    posicion       TINYINT UNSIGNED NOT NULL DEFAULT 0,
    movimiento     ENUM('inmovil', 'en_movimiento') NOT NULL DEFAULT 'inmovil',
    CONSTRAINT pk_actuador             PRIMARY KEY (id_dispositivo),
    CONSTRAINT ck_actuador_porcentaje  CHECK (consigna <= 100 AND posicion <= 100),
    CONSTRAINT fk_actuador_dispositivo FOREIGN KEY (id_dispositivo)
        REFERENCES dispositivo (id_dispositivo)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB;

-- Rango normal NULL cuando no aplica (la llama)
CREATE TABLE variable (
    id_variable   INT          NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(50)  NOT NULL,
    unidad        VARCHAR(10)  NOT NULL,
    minimo_normal DECIMAL(7,2) NULL,
    maximo_normal DECIMAL(7,2) NULL,
    id_sensor     INT          NOT NULL,
    CONSTRAINT pk_variable        PRIMARY KEY (id_variable),
    CONSTRAINT uq_variable_nombre UNIQUE (nombre),
    CONSTRAINT ck_variable_rango  CHECK (minimo_normal < maximo_normal),
    CONSTRAINT fk_variable_sensor FOREIGN KEY (id_sensor) REFERENCES sensor (id_dispositivo)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB;

-- Las lecturas van en su propia BD y no se borran nunca (histórico)
DROP DATABASE IF EXISTS a3i_lecturas;
CREATE DATABASE a3i_lecturas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE a3i_lecturas;

-- El índice sirve para la última lectura de cada variable y para los rangos de fechas
CREATE TABLE lectura (
    id_lectura  BIGINT       NOT NULL AUTO_INCREMENT,
    id_variable INT          NOT NULL,
    valor       DECIMAL(7,2) NOT NULL,
    fecha_hora  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_lectura          PRIMARY KEY (id_lectura),
    CONSTRAINT fk_lectura_variable FOREIGN KEY (id_variable)
        REFERENCES a3i.variable (id_variable)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_lectura_variable_fecha (id_variable, fecha_hora)
) ENGINE = InnoDB;
