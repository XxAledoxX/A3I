-- Datos de partida de la planta: dispositivos, sensores, actuadores y variables

SET NAMES utf8mb4;
USE a3i;

-- Un dispositivo de cada; la llama la ven todos
INSERT INTO dispositivo (nombre, estado, visible_todos, id_sector)
VALUES
    ('sensor_interior', 'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'critico')),
    ('detector_llama',  'operativo', TRUE,  (SELECT id_sector FROM sector WHERE nombre = 'critico')),
    ('turbina',         'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'critico')),
    ('sensor_ambiente', 'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('sensor_aire',     'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('caudalimetro',    'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('bomba_agua',      'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('humidificador',   'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('barrera',         'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'general')),
    ('camara',          'operativo', FALSE, (SELECT id_sector FROM sector WHERE nombre = 'general'));

INSERT INTO sensor (id_dispositivo, intervalo_segundos)
SELECT id_dispositivo, 5
FROM dispositivo
WHERE nombre IN ('sensor_interior', 'detector_llama', 'sensor_ambiente',
                 'sensor_aire', 'caudalimetro');

-- Todos parados y a 0 %: la barrera empieza cerrada
INSERT INTO actuador (id_dispositivo, consigna, posicion, movimiento)
SELECT id_dispositivo, 0, 0, 'inmovil'
FROM dispositivo
WHERE nombre IN ('turbina', 'bomba_agua', 'humidificador', 'barrera', 'camara');

-- Los nombres de las variables los usan el histórico, el simulador y los paneles
INSERT INTO variable (nombre, unidad, minimo_normal, maximo_normal, id_sensor)
VALUES
    ('temperatura_interior', '°C',    40,   70,   (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'sensor_interior')),
    ('humedad_interior',     '%',     30,   50,   (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'sensor_interior')),
    ('temperatura_ambiente', '°C',    18,   26,   (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'sensor_ambiente')),
    ('humedad_ambiente',     '%',     40,   60,   (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'sensor_ambiente')),
    ('calidad_aire',         'ppm',   400,  900,  (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'sensor_aire')),
    ('caudal',               'L/min', 8,    15,   (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'caudalimetro')),
    ('llama',                'si/no', NULL, NULL, (SELECT id_dispositivo FROM dispositivo WHERE nombre = 'detector_llama'));
