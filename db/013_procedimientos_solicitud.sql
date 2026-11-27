-- Crear, ver y cancelar solicitudes. Las escrituras dan error si no se cumple
-- una regla; las lecturas, como las de 007, devuelven vacío

SET NAMES utf8mb4;
USE a3i;

-- Cada solicitud tiene como mucho un objetivo
ALTER TABLE objetivo_solicitud ADD CONSTRAINT uq_objetivo_solicitud UNIQUE (id_solicitud);

DELIMITER //

-- Tipos, duración y motivo llegan sin restringir para que el error sea el de la regla
CREATE PROCEDURE crear_solicitud(IN p_id_usuario INT, IN p_tipo VARCHAR(30),
                                 IN p_prioridad VARCHAR(10), IN p_motivo VARCHAR(255),
                                 IN p_id_sector INT, IN p_duracion_min INT,
                                 IN p_id_dispositivo INT)
BEGIN
    DECLARE v_perfil VARCHAR(20);
    DECLARE v_sector INT;
    DECLARE v_duracion_max INT;
    DECLARE v_mensaje VARCHAR(128);
    DECLARE v_id INT;

    SELECT u.perfil, u.id_sector INTO v_perfil, v_sector
    FROM usuario u
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1);
    IF v_perfil IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No autorizado';
    END IF;

    IF p_tipo IS NULL
       OR p_tipo NOT IN ('cambio_equipo', 'mantenimiento', 'revision', 'acceso_sector')
       OR (p_tipo IN ('cambio_equipo', 'mantenimiento') AND v_perfil <> 'tech') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tipo no disponible';
    END IF;

    IF p_prioridad IS NULL OR p_prioridad NOT IN ('baja', 'normal', 'alta') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Prioridad no válida';
    END IF;

    IF p_motivo IS NULL OR TRIM(p_motivo) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El motivo es obligatorio';
    END IF;

    SELECT valor INTO v_duracion_max FROM parametro WHERE nombre = 'duracion_max_min';
    IF v_duracion_max IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Falta el parámetro duracion_max_min';
    END IF;
    IF p_duracion_min IS NULL OR p_duracion_min < 1 OR p_duracion_min > v_duracion_max THEN
        SET v_mensaje = CONCAT('La duración tiene que estar entre 1 y ', v_duracion_max, ' minutos');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_mensaje;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM sector WHERE id_sector = p_id_sector) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Sector no válido';
    END IF;

    IF p_tipo = 'acceso_sector' THEN
        IF p_id_dispositivo IS NOT NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El acceso a un sector no lleva dispositivo';
        END IF;
        IF p_id_sector = v_sector THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ya tienes acceso a tu sector';
        END IF;
    ELSE
        IF p_id_dispositivo IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Falta el dispositivo';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM dispositivo
                       WHERE id_dispositivo = p_id_dispositivo AND id_sector = p_id_sector) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El dispositivo no es de ese sector';
        END IF;
    END IF;

    INSERT INTO solicitud (tipo, prioridad, motivo, id_solicitante, id_sector, duracion_min)
    VALUES (p_tipo, p_prioridad, TRIM(p_motivo), p_id_usuario, p_id_sector, p_duracion_min);
    -- Se guarda antes del segundo INSERT, que cambia LAST_INSERT_ID()
    SET v_id = LAST_INSERT_ID();

    IF p_id_dispositivo IS NOT NULL THEN
        INSERT INTO objetivo_solicitud (id_solicitud, id_dispositivo)
        VALUES (v_id, p_id_dispositivo);
    END IF;

    SELECT v_id AS id_solicitud;
END //

CREATE PROCEDURE cancelar_solicitud(IN p_id_usuario INT, IN p_id_solicitud INT)
BEGIN
    DECLARE v_solicitante INT;
    DECLARE v_estado VARCHAR(20);

    IF NOT EXISTS (SELECT 1 FROM usuario u
                   WHERE u.id_usuario = p_id_usuario
                     AND u.estado = 'activo'
                     AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No autorizado';
    END IF;

    SELECT id_solicitante, estado INTO v_solicitante, v_estado
    FROM solicitud
    WHERE id_solicitud = p_id_solicitud;
    IF v_solicitante IS NULL OR v_solicitante <> p_id_usuario THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Solo puedes cancelar tus solicitudes';
    END IF;
    IF v_estado <> 'pendiente' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Solo se pueden cancelar las pendientes';
    END IF;

    UPDATE solicitud
    SET estado = 'cancelada', fecha_resolucion = NOW()
    WHERE id_solicitud = p_id_solicitud AND estado = 'pendiente';
END //

CREATE PROCEDURE mis_solicitudes(IN p_id_usuario INT)
BEGIN
    SELECT s.id_solicitud, s.tipo, s.prioridad, s.estado, s.fase,
           se.nombre AS sector, d.nombre AS dispositivo, s.motivo, s.duracion_min,
           s.fecha_creacion, s.fecha_resolucion, s.fecha_caducidad,
           (SELECT COUNT(*) FROM aprobacion a
            WHERE a.id_solicitud = s.id_solicitud AND a.decision = 'aceptada') AS aprobaciones
    FROM usuario u
    JOIN solicitud s ON s.id_solicitante = u.id_usuario
    JOIN sector se ON se.id_sector = s.id_sector
    LEFT JOIN objetivo_solicitud o ON o.id_solicitud = s.id_solicitud
    LEFT JOIN dispositivo d ON d.id_dispositivo = o.id_dispositivo
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)
    ORDER BY s.fecha_creacion DESC, s.id_solicitud DESC;
END //

CREATE PROCEDURE sectores(IN p_id_usuario INT)
BEGIN
    SELECT s.id_sector, s.nombre
    FROM usuario u
    CROSS JOIN sector s
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)
    ORDER BY s.id_sector;
END //

CREATE PROCEDURE dispositivos_sector(IN p_id_usuario INT, IN p_id_sector INT)
BEGIN
    SELECT d.id_dispositivo, d.nombre
    FROM usuario u
    CROSS JOIN dispositivo d
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)
      AND d.id_sector = p_id_sector
    ORDER BY d.id_dispositivo;
END //

DELIMITER ;

GRANT EXECUTE ON PROCEDURE a3i.crear_solicitud TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.cancelar_solicitud TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.mis_solicitudes TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.sectores TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.dispositivos_sector TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';

FLUSH PRIVILEGES;
