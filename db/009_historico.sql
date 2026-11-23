-- Histórico de una variable entre dos fechas, con la misma regla de acceso
-- que ultimas_lecturas. Para que la gráfica no reciba miles de puntos, las
-- lecturas se agrupan en tramos iguales: como mucho p_puntos filas

SET NAMES utf8mb4;
USE a3i;

DELIMITER //

CREATE PROCEDURE historico_lecturas(IN p_id_usuario INT, IN p_variable VARCHAR(255),
                                    IN p_desde DATETIME, IN p_hasta DATETIME,
                                    IN p_puntos INT)
BEGIN
    DECLARE v_id_variable INT DEFAULT NULL;
    DECLARE v_tramo INT;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_id_variable = NULL;

    -- Si el usuario no puede ver la variable se queda en NULL y no sale nada
    SELECT v.id_variable INTO v_id_variable
    FROM usuario u
    CROSS JOIN variable v
    JOIN dispositivo d ON d.id_dispositivo = v.id_sensor
    JOIN sector s ON s.id_sector = d.id_sector
    WHERE u.id_usuario = p_id_usuario
      AND v.nombre = p_variable
      AND u.estado = 'activo'
      AND CONCAT('a3i_', u.perfil) = SUBSTRING_INDEX(USER(), '@', 1)
      AND (d.visible_todos
           OR (u.perfil = s.perfil
               AND (u.id_sector = s.id_sector
                    OR (u.rango IN ('jefe_perfil', 'subjefe_perfil')
                        AND s.nivel <= u.nivel))));

    -- Segundos de cada tramo. El +1 es para que una lectura justo en p_hasta
    -- no abra un tramo de más. El número de puntos se limita a 1..1000
    SET v_tramo = GREATEST(1, TIMESTAMPDIFF(SECOND, p_desde, p_hasta)
                              DIV LEAST(GREATEST(IFNULL(p_puntos, 1), 1), 1000) + 1);

    -- fecha_hora es el inicio del tramo. Se devuelven también el mínimo y el
    -- máximo para que un pico (o la llama) no se pierda en la media.
    -- Sin UNIX_TIMESTAMP: con el cambio de hora contaría una hora de más
    SELECT DATE_ADD(p_desde, INTERVAL TIMESTAMPDIFF(SECOND, p_desde, l.fecha_hora)
                                      DIV v_tramo * v_tramo SECOND) AS fecha_hora,
           ROUND(AVG(l.valor), 2) AS valor_medio,
           MIN(l.valor) AS valor_minimo,
           MAX(l.valor) AS valor_maximo,
           COUNT(*) AS lecturas
    FROM a3i_lecturas.lectura l
    WHERE l.id_variable = v_id_variable
      AND l.fecha_hora BETWEEN p_desde AND p_hasta
    GROUP BY 1
    ORDER BY 1;
END //

DELIMITER ;

GRANT EXECUTE ON PROCEDURE a3i.historico_lecturas TO
    'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1',
    'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1',
    'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1';

FLUSH PRIVILEGES;
