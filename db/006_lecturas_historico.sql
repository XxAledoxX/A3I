-- Histórico inventado de 30 días: una lectura cada 15 min de cada variable
-- (2880 por variable). Y el usuario a3i_simulador, que mete las nuevas

SET NAMES utf8mb4;
USE a3i;

-- Hora actual redondeada a 15 min: la lectura más reciente es de ahora
SET @ahora = FROM_UNIXTIME(UNIX_TIMESTAMP() DIV 900 * 900);

-- seq_0_to_2879 es una tabla virtual de MariaDB con los números 0..2879.
-- seq es cuántos tramos de 15 min hacia atrás desde @ahora
INSERT INTO a3i_lecturas.lectura (id_variable, valor, fecha_hora)
SELECT id_variable,
       ROUND(CASE
           -- Fuego hace 12 días (30 min) y hace 4 días (15 min)
           WHEN nombre = 'llama' THEN IF(seq BETWEEN 1150 AND 1152 OR seq BETWEEN 383 AND 384, 1, 0)
           WHEN nombre = 'temperatura_interior' AND (seq BETWEEN 1150 AND 1152 OR seq BETWEEN 383 AND 384) THEN 82
           -- Algunos valores fuera del rango normal: bomba que falla y picos
           WHEN nombre = 'caudal' AND seq BETWEEN 600 AND 603 THEN 5.5
           WHEN nombre = 'calidad_aire' AND seq BETWEEN 2000 AND 2003 THEN 1150
           WHEN nombre = 'humedad_ambiente' AND seq BETWEEN 1700 AND 1702 THEN 68
           -- Lo normal: valor medio, una onda diaria y algo de ruido
           WHEN nombre = 'temperatura_interior' THEN 55 + 6 * SIN(2 * PI() * (hora - 3) / 24) + (r - 0.5) * 4
           WHEN nombre = 'humedad_interior' THEN 40 + 4 * SIN(2 * PI() * (hora - 3) / 24) + (r - 0.5) * 3
           WHEN nombre = 'temperatura_ambiente' THEN 22 + 2.5 * SIN(2 * PI() * (hora - 9) / 24) + (r - 0.5) * 1.5
           WHEN nombre = 'humedad_ambiente' THEN 50 - 6 * SIN(2 * PI() * (hora - 9) / 24) + (r - 0.5) * 3
           WHEN nombre = 'calidad_aire' THEN 650 + 120 * SIN(2 * PI() * (hora - 11) / 24) + (r - 0.5) * 80
           WHEN nombre = 'caudal' THEN 11.5 + 1.5 * SIN(2 * PI() * (hora - 6) / 24) + (r - 0.5)
       END, 2),
       fecha_hora
FROM (
    SELECT id_variable, nombre, seq, fecha_hora,
           HOUR(fecha_hora) + MINUTE(fecha_hora) / 60 AS hora,
           -- Con semilla, para que todos tengamos los mismos datos
           RAND(29) AS r
    FROM (
        SELECT v.id_variable, v.nombre, s.seq,
               @ahora - INTERVAL s.seq * 15 MINUTE AS fecha_hora
        FROM variable v
        CROSS JOIN seq_0_to_2879 s
    ) tramos
) datos
ORDER BY fecha_hora, id_variable;

-- Usuario del simulador (RF-029): solo lee las variables y mete lecturas.
-- Va aquí y no en el 002 porque necesita que exista a3i_lecturas.lectura
DROP USER IF EXISTS 'a3i_simulador'@'localhost';
DROP USER IF EXISTS 'a3i_simulador'@'127.0.0.1';

-- La contraseña llega en @a3i_simulador_password desde reset_db.sh
SET @crear = CONCAT('CREATE USER ''a3i_simulador''@''localhost'' IDENTIFIED BY ',
                    QUOTE(@a3i_simulador_password));
PREPARE stmt FROM @crear;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @crear = CONCAT('CREATE USER ''a3i_simulador''@''127.0.0.1'' IDENTIFIED BY ',
                    QUOTE(@a3i_simulador_password));
PREPARE stmt FROM @crear;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

GRANT SELECT ON a3i.variable TO 'a3i_simulador'@'localhost', 'a3i_simulador'@'127.0.0.1';
GRANT INSERT ON a3i_lecturas.lectura TO 'a3i_simulador'@'localhost', 'a3i_simulador'@'127.0.0.1';

FLUSH PRIVILEGES;
