-- Aviso del bloqueo de una cuenta (RF-006). Lo crea un trigger al pasar la
-- cuenta a bloqueado y cada destinatario lo ve en su app hasta marcarlo leído.
-- El 011 queda para las alertas (ver 010_solicitudes.sql)

SET NAMES utf8mb4;
USE a3i;

CREATE TABLE notificacion (
    id_notificacion     INT                       NOT NULL AUTO_INCREMENT,
    id_destinatario     INT                       NOT NULL,
    tipo                ENUM('bloqueo_cuenta')    NOT NULL,
    id_usuario_afectado INT                       NOT NULL,
    fecha               DATETIME                  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    leida               BOOLEAN                   NOT NULL DEFAULT FALSE,
    CONSTRAINT pk_notificacion           PRIMARY KEY (id_notificacion),
    CONSTRAINT fk_notificacion_destino   FOREIGN KEY (id_destinatario) REFERENCES usuario (id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_notificacion_afectado  FOREIGN KEY (id_usuario_afectado) REFERENCES usuario (id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX ix_notificacion_destino (id_destinatario, leida)
) ENGINE = InnoDB;

-- Quién se entera del bloqueo de cada cuenta: jefe y subjefe de Seguridad y
-- del perfil de la cuenta, sin la propia cuenta. Cada destinatario sale una vez
CREATE VIEW destinatarios_bloqueo AS
SELECT a.id_usuario AS id_afectado, d.id_usuario AS id_destinatario
FROM usuario a
JOIN usuario d ON d.rango IN ('jefe_perfil', 'subjefe_perfil')
              AND d.perfil IN ('seguridad', a.perfil)
              AND d.id_usuario <> a.id_usuario;

DELIMITER //

CREATE TRIGGER notificar_bloqueo AFTER UPDATE ON usuario
FOR EACH ROW
BEGIN
    IF OLD.estado <> 'bloqueado' AND NEW.estado = 'bloqueado' THEN
        INSERT INTO notificacion (id_destinatario, tipo, id_usuario_afectado)
        SELECT id_destinatario, 'bloqueo_cuenta', id_afectado
        FROM destinatarios_bloqueo
        WHERE id_afectado = NEW.id_usuario;
    END IF;
END //

-- Las no leídas del usuario. Misma comprobación que los procedimientos de
-- datos: usuario activo y usuario de BD de su perfil
CREATE PROCEDURE mis_notificaciones(IN p_id_usuario INT)
BEGIN
    SELECT n.id_notificacion, n.tipo, n.fecha,
           a.nombre AS nombre_afectado, a.login AS login_afectado
    FROM usuario u
    JOIN notificacion n ON n.id_destinatario = u.id_usuario
    JOIN usuario a ON a.id_usuario = n.id_usuario_afectado
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)
      AND NOT n.leida
    ORDER BY n.fecha DESC, n.id_notificacion DESC;
END //

-- Solo marca la notificación si es de ese usuario
CREATE PROCEDURE marcar_notificacion_leida(IN p_id_usuario INT, IN p_id_notificacion INT)
BEGIN
    UPDATE notificacion n
    JOIN usuario u ON u.id_usuario = n.id_destinatario
    SET n.leida = TRUE
    WHERE n.id_notificacion = p_id_notificacion
      AND u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1);
END //

DELIMITER ;

-- Las cuentas que ya estaban bloqueadas antes de este script también avisan
INSERT INTO notificacion (id_destinatario, tipo, id_usuario_afectado)
SELECT b.id_destinatario, 'bloqueo_cuenta', b.id_afectado
FROM destinatarios_bloqueo b
JOIN usuario u ON u.id_usuario = b.id_afectado
WHERE u.estado = 'bloqueado';

GRANT EXECUTE ON PROCEDURE a3i.mis_notificaciones TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.marcar_notificacion_leida TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';

FLUSH PRIVILEGES;
