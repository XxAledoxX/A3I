-- Control de acceso: la app solo ejecuta procedimientos, nunca lee tablas.
-- a3i_login entra para el login y, tras autenticar, la app usa el usuario
-- de BD de su perfil. Las contraseñas llegan desde reset_db.sh (salen del .env)

SET NAMES utf8mb4;
USE a3i;

DELIMITER //

-- Crea el usuario en localhost (socket) y en 127.0.0.1 (TCP)
CREATE PROCEDURE crear_usuario_bd(IN p_usuario VARCHAR(32), IN p_contrasena VARCHAR(255))
BEGIN
    DECLARE v_host VARCHAR(20);
    DECLARE v_vuelta INT DEFAULT 0;
    WHILE v_vuelta < 2 DO
        SET v_host = IF(v_vuelta = 0, 'localhost', '127.0.0.1');
        SET @sql = CONCAT('DROP USER IF EXISTS ', QUOTE(p_usuario), '@', QUOTE(v_host));
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SET @sql = CONCAT('CREATE USER ', QUOTE(p_usuario), '@', QUOTE(v_host),
                          ' IDENTIFIED BY ', QUOTE(p_contrasena));
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SET v_vuelta = v_vuelta + 1;
    END WHILE;
END //

-- Procedimientos del login. Los parámetros de texto son largos a propósito:
-- un login de más no debe dar error, solo no encontrar a nadie

CREATE PROCEDURE buscar_usuario(IN p_login VARCHAR(255))
BEGIN
    -- Devuelve el hash porque Argon2id se verifica en Python
    SELECT id_usuario, nombre, login, hash_contrasena, intentos_fallidos,
           estado, rango, nivel, perfil
    FROM usuario
    WHERE login = p_login;
END //

CREATE PROCEDURE actualizar_intentos(IN p_id_usuario INT, IN p_intentos TINYINT UNSIGNED)
BEGIN
    UPDATE usuario SET intentos_fallidos = p_intentos WHERE id_usuario = p_id_usuario;
END //

CREATE PROCEDURE registrar_fallo(IN p_login VARCHAR(255), IN p_max_intentos TINYINT UNSIGNED)
BEGIN
    -- En una sola consulta para no perder fallos si llegan dos a la vez.
    -- estado va primero porque MariaDB asigna de izquierda a derecha
    UPDATE usuario
    SET estado = IF(intentos_fallidos + 1 >= p_max_intentos, 'bloqueado', estado),
        intentos_fallidos = intentos_fallidos + 1
    WHERE login = p_login AND estado = 'activo';
END //

CREATE PROCEDURE actualizar_hash(IN p_id_usuario INT, IN p_hash VARCHAR(255))
BEGIN
    UPDATE usuario SET hash_contrasena = p_hash WHERE id_usuario = p_id_usuario;
END //

-- Procedimientos de datos (regla de RF-025, Assets/Models/Reglas-acceso.pdf).
-- Solo devuelven algo si el usuario está activo y el usuario de BD que llama
-- es el de su perfil: un científico no puede pedir datos con a3i_tech.
-- Desde DBeaver con root salen vacíos por eso

CREATE PROCEDURE ultimas_lecturas(IN p_id_usuario INT)
BEGIN
    SELECT v.nombre AS variable, v.unidad, l.valor, l.fecha_hora,
           v.minimo_normal, v.maximo_normal, s.nombre AS sector
    FROM usuario u
    CROSS JOIN variable v
    JOIN dispositivo d ON d.id_dispositivo = v.id_sensor
    JOIN sector s ON s.id_sector = d.id_sector
    -- Última lectura de cada variable, con el índice (id_variable, fecha_hora)
    JOIN a3i_lecturas.lectura l ON l.id_lectura = (
        SELECT l2.id_lectura
        FROM a3i_lecturas.lectura l2
        WHERE l2.id_variable = v.id_variable
        ORDER BY l2.fecha_hora DESC, l2.id_lectura DESC
        LIMIT 1)
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)
      AND (d.visible_todos
           OR (u.perfil = s.perfil
               AND (u.id_sector = s.id_sector
                    OR (u.rango IN ('jefe_perfil', 'subjefe_perfil')
                        AND s.nivel <= u.nivel))))
    ORDER BY v.id_variable;
END //

CREATE PROCEDURE estado_actuadores(IN p_id_usuario INT)
BEGIN
    SELECT d.nombre, s.nombre AS sector, a.posicion, a.movimiento, d.estado
    FROM usuario u
    CROSS JOIN actuador a
    JOIN dispositivo d ON d.id_dispositivo = a.id_dispositivo
    JOIN sector s ON s.id_sector = d.id_sector
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)
      AND (d.visible_todos
           OR (u.perfil = s.perfil
               AND (u.id_sector = s.id_sector
                    OR (u.rango IN ('jefe_perfil', 'subjefe_perfil')
                        AND s.nivel <= u.nivel))))
    ORDER BY d.id_dispositivo;
END //

-- El estado del equipo es de Tech: a los demás perfiles no les sale nada
CREATE PROCEDURE estado_equipos(IN p_id_usuario INT)
BEGIN
    SELECT d.nombre, s.nombre AS sector, d.estado
    FROM usuario u
    CROSS JOIN dispositivo d
    JOIN sector s ON s.id_sector = d.id_sector
    WHERE u.id_usuario = p_id_usuario
      AND u.estado = 'activo'
      AND u.perfil = 'tech'
      AND SUBSTRING_INDEX(USER(), '@', 1) = 'a3i_tech'
      AND (u.id_sector = s.id_sector
           OR (u.rango IN ('jefe_perfil', 'subjefe_perfil') AND s.nivel <= u.nivel))
    ORDER BY d.id_dispositivo;
END //

DELIMITER ;

CALL crear_usuario_bd('a3i_login', @a3i_login_password);
CALL crear_usuario_bd('a3i_cientificos', @a3i_cientificos_password);
CALL crear_usuario_bd('a3i_seguridad', @a3i_seguridad_password);
CALL crear_usuario_bd('a3i_tech', @a3i_tech_password);
DROP PROCEDURE crear_usuario_bd;

-- Solo EXECUTE: ningún usuario de la app puede leer ni cambiar tablas
GRANT EXECUTE ON PROCEDURE a3i.buscar_usuario TO 'a3i_login'@'localhost', 'a3i_login'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.actualizar_intentos TO 'a3i_login'@'localhost', 'a3i_login'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.registrar_fallo TO 'a3i_login'@'localhost', 'a3i_login'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.actualizar_hash TO 'a3i_login'@'localhost', 'a3i_login'@'127.0.0.1';

GRANT EXECUTE ON PROCEDURE a3i.ultimas_lecturas TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.estado_actuadores TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';
GRANT EXECUTE ON PROCEDURE a3i.estado_equipos TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';

FLUSH PRIVILEGES;

-- Validación de lecturas (RF-030): se rechazan los valores físicamente
-- imposibles. Los que solo se salen del rango normal sí se guardan, porque
-- son las alertas del Sprint 3
USE a3i_lecturas;

DELIMITER //

CREATE TRIGGER validar_lectura BEFORE INSERT ON lectura
FOR EACH ROW
BEGIN
    DECLARE v_nombre VARCHAR(50);
    DECLARE v_minimo DECIMAL(7,2);
    DECLARE v_maximo DECIMAL(7,2);
    DECLARE v_mensaje VARCHAR(128);

    SELECT nombre INTO v_nombre FROM a3i.variable WHERE id_variable = NEW.id_variable;

    CASE
        WHEN v_nombre IN ('humedad_interior', 'humedad_ambiente') THEN
            SET v_minimo = 0, v_maximo = 100;
        WHEN v_nombre IN ('temperatura_interior', 'temperatura_ambiente') THEN
            SET v_minimo = -40, v_maximo = 150;
        WHEN v_nombre = 'calidad_aire' THEN
            SET v_minimo = 0, v_maximo = 10000;
        WHEN v_nombre = 'caudal' THEN
            SET v_minimo = 0, v_maximo = 100;
        WHEN v_nombre = 'llama' THEN
            SET v_minimo = 0, v_maximo = 1;
        ELSE
            -- Variable sin límites: se acepta
            SET v_minimo = NULL, v_maximo = NULL;
    END CASE;

    IF NEW.valor < v_minimo OR NEW.valor > v_maximo
       OR (v_nombre = 'llama' AND NEW.valor NOT IN (0, 1)) THEN
        SET v_mensaje = CONCAT('Lectura imposible de ', v_nombre, ': ', NEW.valor);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_mensaje;
    END IF;
END //

DELIMITER ;
