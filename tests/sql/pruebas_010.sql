-- Pruebas de las restricciones de db/010_solicitudes.sql
-- Lanzar con: sudo mariadb --force < tests/sql/pruebas_010.sql
-- Las 7 inserciones marcadas con "FALLA" tienen que dar error. ROLLBACK al final.

USE a3i;
START TRANSACTION;

-- Datos válidos: una solicitud de cientifico1 en el sector cientifico
INSERT INTO solicitud (tipo, motivo, id_solicitante, id_sector, duracion_min)
VALUES ('mantenimiento', 'Prueba',
        (SELECT id_usuario FROM usuario WHERE login = 'cientifico1'),
        (SELECT id_sector FROM sector WHERE nombre = 'cientifico'), 30);
SET @s = LAST_INSERT_ID();
SET @bomba = (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'bomba_agua');
SET @jefe = (SELECT id_usuario FROM usuario WHERE login = 'jefesector_cien');

-- Datos válidos: un objetivo y una aprobación
INSERT INTO objetivo_solicitud (id_solicitud, id_dispositivo) VALUES (@s, @bomba);
INSERT INTO aprobacion (id_solicitud, id_usuario, decision) VALUES (@s, @jefe, 'aceptada');
SELECT 'Válidas insertadas' AS paso,
       (SELECT COUNT(*) FROM solicitud) AS solicitudes,
       (SELECT COUNT(*) FROM objetivo_solicitud) AS objetivos,
       (SELECT COUNT(*) FROM aprobacion) AS aprobaciones;

-- 1. FALLA (ck_objetivo_uno): objetivo sin dispositivo ni usuario
INSERT INTO objetivo_solicitud (id_solicitud, id_dispositivo, id_usuario) VALUES (@s, NULL, NULL);

-- 2. FALLA (ck_objetivo_uno): objetivo con dispositivo y usuario
INSERT INTO objetivo_solicitud (id_solicitud, id_dispositivo, id_usuario) VALUES (@s, @bomba, @jefe);

-- 3. FALLA (ck_solicitud_duracion): duración 0
INSERT INTO solicitud (tipo, motivo, id_solicitante, id_sector, duracion_min)
VALUES ('mantenimiento', 'Prueba', @jefe,
        (SELECT id_sector FROM sector WHERE nombre = 'cientifico'), 0);

-- 4. FALLA (ck_solicitud_fase): pendiente con fase
INSERT INTO solicitud (tipo, estado, fase, motivo, id_solicitante, id_sector, duracion_min)
VALUES ('mantenimiento', 'pendiente', 'autorizada', 'Prueba', @jefe,
        (SELECT id_sector FROM sector WHERE nombre = 'cientifico'), 30);

-- 5. FALLA (ck_solicitud_fase): aceptada sin fase
INSERT INTO solicitud (tipo, estado, fase, motivo, id_solicitante, id_sector, duracion_min)
VALUES ('mantenimiento', 'aceptada', NULL, 'Prueba', @jefe,
        (SELECT id_sector FROM sector WHERE nombre = 'cientifico'), 30);

-- 6. FALLA (pk_aprobacion, sale como PRIMARY): la misma aprobación dos veces
INSERT INTO aprobacion (id_solicitud, id_usuario, decision) VALUES (@s, @jefe, 'rechazada');

-- 7. FALLA (uq_objetivo_dispositivo): el mismo dispositivo dos veces en la solicitud
INSERT INTO objetivo_solicitud (id_solicitud, id_dispositivo) VALUES (@s, @bomba);

ROLLBACK;

SELECT 'Tras el ROLLBACK' AS paso,
       (SELECT COUNT(*) FROM solicitud) AS solicitudes,
       (SELECT COUNT(*) FROM objetivo_solicitud) AS objetivos,
       (SELECT COUNT(*) FROM aprobacion) AS aprobaciones,
       (SELECT COUNT(*) FROM parametro) AS parametros;
