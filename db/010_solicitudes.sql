-- Solicitudes, sus objetivos y aprobaciones, y parámetros de configuración

SET NAMES utf8mb4;
USE a3i;

CREATE TABLE parametro (
    nombre VARCHAR(40) NOT NULL,
    valor  INT         NOT NULL,
    CONSTRAINT pk_parametro PRIMARY KEY (nombre)
) ENGINE = InnoDB;

INSERT INTO parametro (nombre, valor) VALUES
    ('duracion_max_min', 480),
    ('plazo_inicio_min', 60),
    ('porcentaje_aviso', 10);

-- fase solo tiene valor mientras la solicitud está aceptada
-- id_alerta sin FK: la añade 011_alertas.sql
CREATE TABLE solicitud (
    id_solicitud         INT               NOT NULL AUTO_INCREMENT,
    tipo                 ENUM('cambio_equipo', 'mantenimiento', 'revision', 'accion_restringida',
                              'alta_usuario', 'baja_usuario', 'modificacion_usuario',
                              'cambio_nivel', 'acceso_sector') NOT NULL,
    prioridad            ENUM('baja', 'normal', 'alta') NOT NULL DEFAULT 'normal',
    estado               ENUM('pendiente', 'aceptada', 'rechazada', 'cancelada', 'caducada')
                                           NOT NULL DEFAULT 'pendiente',
    fase                 ENUM('autorizada', 'ejecucion', 'cierre') NULL,
    motivo               VARCHAR(255)      NOT NULL,
    id_solicitante       INT               NOT NULL,
    id_ejecutor          INT               NULL,
    id_sector            INT               NOT NULL,
    id_alerta            INT               NULL,
    duracion_min         SMALLINT UNSIGNED NOT NULL,
    fecha_creacion       DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion     DATETIME          NULL,
    fecha_caducidad      DATETIME          NULL,
    fecha_inicio         DATETIME          NULL,
    fecha_cierre         DATETIME          NULL,
    justificacion_cierre TEXT              NULL,
    CONSTRAINT pk_solicitud              PRIMARY KEY (id_solicitud),
    CONSTRAINT ck_solicitud_duracion     CHECK (duracion_min > 0),
    CONSTRAINT ck_solicitud_fase         CHECK ((estado = 'aceptada') = (fase IS NOT NULL)),
    CONSTRAINT fk_solicitud_solicitante  FOREIGN KEY (id_solicitante) REFERENCES usuario (id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_solicitud_ejecutor     FOREIGN KEY (id_ejecutor) REFERENCES usuario (id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_solicitud_sector       FOREIGN KEY (id_sector) REFERENCES sector (id_sector)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB;

-- Cada objetivo es un dispositivo o un usuario, nunca los dos
-- ON UPDATE RESTRICT en esas dos FK: MariaDB no deja usar en un CHECK columnas con CASCADE
CREATE TABLE objetivo_solicitud (
    id_objetivo    INT      NOT NULL AUTO_INCREMENT,
    id_solicitud   INT      NOT NULL,
    id_dispositivo INT      NULL,
    id_usuario     INT      NULL,
    fecha_uso      DATETIME NULL,
    CONSTRAINT pk_objetivo_solicitud   PRIMARY KEY (id_objetivo),
    CONSTRAINT uq_objetivo_dispositivo UNIQUE (id_solicitud, id_dispositivo),
    CONSTRAINT uq_objetivo_usuario     UNIQUE (id_solicitud, id_usuario),
    CONSTRAINT ck_objetivo_uno         CHECK ((id_dispositivo IS NULL) <> (id_usuario IS NULL)),
    CONSTRAINT fk_objetivo_solicitud   FOREIGN KEY (id_solicitud) REFERENCES solicitud (id_solicitud)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_objetivo_dispositivo FOREIGN KEY (id_dispositivo)
        REFERENCES dispositivo (id_dispositivo)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk_objetivo_usuario     FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE aprobacion (
    id_solicitud INT          NOT NULL,
    id_usuario   INT          NOT NULL,
    decision     ENUM('aceptada', 'rechazada') NOT NULL,
    comentario   VARCHAR(255) NULL,
    fecha        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_aprobacion           PRIMARY KEY (id_solicitud, id_usuario),
    CONSTRAINT fk_aprobacion_solicitud FOREIGN KEY (id_solicitud) REFERENCES solicitud (id_solicitud)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_aprobacion_usuario   FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB;
