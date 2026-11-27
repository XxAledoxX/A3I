-- Pruebas de las restricciones de db/013_procedimientos_solicitud.sql
-- Lanzar con: sudo mariadb --force < tests/sql/pruebas_013.sql
-- La inserción marcada con "FALLA" tiene que dar error. ROLLBACK al final.

USE a3i;
START TRANSACTION;

-- Datos válidos: una solicitud de tech1 con la barrera como objetivo
INSERT INTO solicitud (tipo, motivo, id_solicitante, id_sector, duracion_min)
VALUES ('mantenimiento', 'Prueba',
        (SELECT id_usuario FROM usuario WHERE login = 'tech1'),
        (SELECT id_sector FROM sector WHERE nombre = 'general'), 30);
SET @s = LAST_INSERT_ID();
INSERT INTO objetivo_solicitud (id_solicitud, id_dispositivo)
VALUES (@s, (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'barrera'));
SELECT 'Válidas insertadas' AS paso,
       (SELECT COUNT(*) FROM solicitud) AS solicitudes,
       (SELECT COUNT(*) FROM objetivo_solicitud) AS objetivos;

-- 1. FALLA (uq_objetivo_solicitud): un segundo objetivo en la misma solicitud
INSERT INTO objetivo_solicitud (id_solicitud, id_dispositivo)
VALUES (@s, (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'camara'));

ROLLBACK;

SELECT 'Tras el ROLLBACK' AS paso,
       (SELECT COUNT(*) FROM solicitud) AS solicitudes,
       (SELECT COUNT(*) FROM objetivo_solicitud) AS objetivos;
