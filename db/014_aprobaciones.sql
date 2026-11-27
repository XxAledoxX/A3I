-- Aprobar y rechazar solicitudes. Quién puede hacerlo está en puede_aprobar,
-- con la regla N+1 de Assets/Models/vigente/Reglas-acceso.pdf. Los tipos que
-- aún no tienen regla no los puede aprobar nadie

SET NAMES utf8mb4;
USE a3i;

DELIMITER //

-- La usan los procedimientos de abajo; ningún usuario de la app la llama directamente
CREATE FUNCTION puede_aprobar(p_id_usuario INT, p_id_solicitud INT) RETURNS BOOLEAN
READS SQL DATA
BEGIN
    DECLARE v_puede BOOLEAN DEFAULT FALSE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_puede = FALSE;

    SELECT CASE
               -- Sector crítico: jefe o subjefe de perfil de Seguridad con nivel 4
               WHEN s.tipo = 'acceso_sector' AND se.nivel = 3 THEN
                   u.perfil = 'seguridad'
                   AND u.rango IN ('jefe_perfil', 'subjefe_perfil')
                   AND u.nivel >= 4
               -- Otro sector de nivel N: jefe o subjefe de ese sector con nivel N+1
               WHEN s.tipo = 'acceso_sector' THEN
                   u.perfil = se.perfil
                   AND u.rango IN ('jefe_sector', 'subjefe_sector')
                   AND u.id_sector = se.id_sector
                   AND u.nivel >= se.nivel + 1
               WHEN s.tipo = 'accion_restringida' THEN
                   u.perfil = 'cientificos'
                   AND u.rango IN ('jefe_perfil', 'subjefe_perfil')
               ELSE FALSE
           END
    INTO v_puede
    FROM solicitud s
    JOIN sector se ON se.id_sector = s.id_sector
    JOIN usuario u ON u.id_usuario = p_id_usuario
    WHERE s.id_solicitud = p_id_solicitud
      AND s.id_solicitante <> p_id_usuario
      AND u.estado = 'activo';

    RETURN IFNULL(v_puede, FALSE);
END //

-- Pendientes que el usuario puede decidir, las de más prioridad primero
CREATE PROCEDURE por_aprobar(IN p_id_usuario INT)
BEGIN
    SELECT s.id_solicitud, s.tipo, s.prioridad, sol.nombre AS solicitante,
           se.nombre AS sector, d.nombre AS dispositivo, s.motivo, s.duracion_min,
           s.fecha_creacion
    FROM usuario u
    JOIN solicitud s ON s.estado = 'pendiente'
    JOIN usuario sol ON sol.id_usuario = s.id_solicitante
    JOIN sector se ON se.id_sector = s.id_sector
    LEFT JOIN objetivo_solicitud o ON o.id_solicitud = s.id_solicitud
    LEFT JOIN dispositivo d ON d.id_dispositivo = o.id_dispositivo
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)
      AND puede_aprobar(u.id_usuario, s.id_solicitud)
    ORDER BY FIELD(s.prioridad, 'alta', 'normal', 'baja'), s.fecha_creacion, s.id_solicitud;
END //

-- p_decision es 'aceptada' o 'rechazada'. Con una decisión basta: al aceptar,
-- el permiso caduca si no se empieza en plazo_inicio_min minutos (RF-077)
CREATE PROCEDURE decidir_solicitud(IN p_id_usuario INT, IN p_id_solicitud INT,
                                   IN p_decision VARCHAR(20), IN p_comentario VARCHAR(255))
BEGIN
    DECLARE v_solicitante INT;
    DECLARE v_estado VARCHAR(20);
    DECLARE v_tipo VARCHAR(30);
    DECLARE v_plazo INT;

    IF NOT EXISTS (SELECT 1 FROM usuario u
                   WHERE u.id_usuario = p_id_usuario
                     AND u.estado = 'activo'
                     AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No autorizado';
    END IF;

    IF p_decision IS NULL OR p_decision NOT IN ('aceptada', 'rechazada') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Decisión no válida';
    END IF;

    SELECT id_solicitante, estado, tipo INTO v_solicitante, v_estado, v_tipo
    FROM solicitud
    WHERE id_solicitud = p_id_solicitud;
    IF v_solicitante IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La solicitud no existe';
    END IF;
    IF v_solicitante = p_id_usuario THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No puedes decidir sobre tu propia solicitud';
    END IF;
    IF v_estado <> 'pendiente' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La solicitud ya no está pendiente';
    END IF;
    IF v_tipo NOT IN ('acceso_sector', 'accion_restringida') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Aún no está decidido quién aprueba este tipo';
    END IF;
    IF NOT puede_aprobar(p_id_usuario, p_id_solicitud) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No tienes autoridad para decidir esta solicitud';
    END IF;

    SELECT valor INTO v_plazo FROM parametro WHERE nombre = 'plazo_inicio_min';
    IF p_decision = 'aceptada' AND v_plazo IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Falta el parámetro plazo_inicio_min';
    END IF;

    -- El WHERE estado = 'pendiente' evita que dos jefes la decidan a la vez:
    -- el segundo no cambia ninguna fila y recibe el error
    UPDATE solicitud
    SET estado = p_decision,
        fase = IF(p_decision = 'aceptada', 'autorizada', NULL),
        fecha_resolucion = NOW(),
        fecha_caducidad = IF(p_decision = 'aceptada', NOW() + INTERVAL v_plazo MINUTE, NULL)
    WHERE id_solicitud = p_id_solicitud AND estado = 'pendiente';
    IF ROW_COUNT() = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La solicitud ya no está pendiente';
    END IF;

    INSERT INTO aprobacion (id_solicitud, id_usuario, decision, comentario)
    VALUES (p_id_solicitud, p_id_usuario, p_decision, NULLIF(TRIM(p_comentario), ''));
END //

DELIMITER ;

GRANT EXECUTE ON PROCEDURE a3i.por_aprobar TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.decidir_solicitud TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';

FLUSH PRIVILEGES;
