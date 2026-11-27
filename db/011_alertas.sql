-- Alertas: avisos y alarmas de las lecturas (diseño en Assets/Models/vigente/Diseno-alertas.pdf).
-- Las crea el trigger detectar_alerta, que va después de meter las del histórico
-- para que solo actúe sobre las lecturas que llegan después del reset

-- La misma collation que la BD: si no, MariaDB 11 no compara los textos de la función
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
USE a3i;

-- id_lectura e id_lectura_alarma sin FK: una FK a a3i_lecturas cerraría un
-- círculo con la de lectura a variable y el reset no podría borrar ninguna BD
CREATE TABLE alerta (
    id_alerta         INT          NOT NULL AUTO_INCREMENT,
    id_variable       INT          NOT NULL,
    tipo              ENUM('aviso', 'alarma') NOT NULL,
    estado            ENUM('pendiente', 'en_curso', 'por_revisar', 'resuelta')
                                   NOT NULL DEFAULT 'pendiente',
    id_lectura        BIGINT       NOT NULL,
    id_lectura_alarma BIGINT       NULL,
    id_encargado      INT          NULL,
    id_asignador      INT          NULL,
    fecha_asignacion  DATETIME     NULL,
    fecha_terminada   DATETIME     NULL,
    motivo_devolucion VARCHAR(255) NULL,
    id_revisor        INT          NULL,
    fecha_resolucion  DATETIME     NULL,
    CONSTRAINT pk_alerta           PRIMARY KEY (id_alerta),
    CONSTRAINT fk_alerta_variable  FOREIGN KEY (id_variable) REFERENCES variable (id_variable)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_alerta_encargado FOREIGN KEY (id_encargado) REFERENCES usuario (id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_alerta_asignador FOREIGN KEY (id_asignador) REFERENCES usuario (id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_alerta_revisor   FOREIGN KEY (id_revisor) REFERENCES usuario (id_usuario)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    -- Para buscar rápido la alerta activa de una variable
    INDEX ix_alerta_variable_estado (id_variable, estado)
) ENGINE = InnoDB;

ALTER TABLE solicitud
    ADD CONSTRAINT fk_solicitud_alerta FOREIGN KEY (id_alerta) REFERENCES alerta (id_alerta)
        ON UPDATE CASCADE ON DELETE RESTRICT;

DELIMITER //

-- 'alarma' si el valor pasa un límite, 'aviso' si está a menos de
-- porcentaje_aviso del ancho del rango de un límite y NULL si es normal.
-- En la llama, 1 es alarma. Los equipos en mantenimiento no se comparan,
-- salvo la llama
CREATE FUNCTION tipo_alerta(p_id_variable INT, p_valor DECIMAL(7,2))
RETURNS VARCHAR(10)
READS SQL DATA
BEGIN
    DECLARE v_nombre VARCHAR(50);
    DECLARE v_minimo DECIMAL(7,2);
    DECLARE v_maximo DECIMAL(7,2);
    DECLARE v_estado VARCHAR(20);
    DECLARE v_margen DECIMAL(9,4);

    SELECT v.nombre, v.minimo_normal, v.maximo_normal, d.estado
    INTO v_nombre, v_minimo, v_maximo, v_estado
    FROM variable v
    JOIN dispositivo d ON d.id_dispositivo = v.id_sensor
    WHERE v.id_variable = p_id_variable;

    IF v_nombre = 'llama' THEN
        RETURN IF(p_valor = 1, 'alarma', NULL);
    END IF;
    IF v_estado = 'mantenimiento' OR v_minimo IS NULL OR v_maximo IS NULL THEN
        RETURN NULL;
    END IF;
    IF p_valor < v_minimo OR p_valor > v_maximo THEN
        RETURN 'alarma';
    END IF;

    SELECT (v_maximo - v_minimo) * valor / 100 INTO v_margen
    FROM parametro WHERE nombre = 'porcentaje_aviso';
    IF p_valor < v_minimo + v_margen OR p_valor > v_maximo - v_margen THEN
        RETURN 'aviso';
    END IF;
    RETURN NULL;
END //

DELIMITER ;

-- Alertas del histórico de 006, con la misma regla que el trigger: varias
-- lecturas malas seguidas son una sola alerta. Se dan por resueltas en la
-- primera lectura normal de después. Las resuelve jefesector_cien en el
-- sector científico, jefe_cien en el crítico y jefe_seg en la llama
SET @jefe_cientifico = (SELECT id_usuario FROM usuario WHERE login = 'jefesector_cien');
SET @jefe_critico = (SELECT id_usuario FROM usuario WHERE login = 'jefe_cien');
SET @jefe_llama = (SELECT id_usuario FROM usuario WHERE login = 'jefe_seg');

INSERT INTO alerta (id_variable, tipo, estado, id_lectura, id_lectura_alarma,
                    id_revisor, fecha_resolucion)
SELECT t.id_variable,
       IF(t.hay_alarma, 'alarma', 'aviso'),
       IF(t.fecha_normal IS NULL, 'pendiente', 'resuelta'),
       (SELECT l.id_lectura FROM a3i_lecturas.lectura l
        WHERE l.id_variable = t.id_variable AND l.fecha_hora = t.inicio
        ORDER BY l.id_lectura LIMIT 1),
       -- Solo si empezó como aviso y luego subió a alarma
       IF(t.primera_alarma > t.inicio,
          (SELECT l.id_lectura FROM a3i_lecturas.lectura l
           WHERE l.id_variable = t.id_variable AND l.fecha_hora = t.primera_alarma
           ORDER BY l.id_lectura LIMIT 1),
          NULL),
       IF(t.fecha_normal IS NULL, NULL,
          CASE WHEN v.nombre = 'llama' THEN @jefe_llama
               WHEN s.nombre = 'critico' THEN @jefe_critico
               ELSE @jefe_cientifico END),
       t.fecha_normal
FROM (
    SELECT g.id_variable,
           MIN(g.fecha_hora) AS inicio,
           MAX(g.tipo = 'alarma') AS hay_alarma,
           MIN(IF(g.tipo = 'alarma', g.fecha_hora, NULL)) AS primera_alarma,
           (SELECT MIN(l.fecha_hora) FROM a3i_lecturas.lectura l
            WHERE l.id_variable = g.id_variable AND l.fecha_hora > MAX(g.fecha_hora)) AS fecha_normal
    FROM (
        -- grupo cuenta las lecturas normales anteriores: las malas seguidas
        -- comparten grupo
        SELECT c.*,
               SUM(c.tipo IS NULL) OVER (PARTITION BY c.id_variable
                                         ORDER BY c.fecha_hora, c.id_lectura) AS grupo
        FROM (
            SELECT l.id_lectura, l.id_variable, l.fecha_hora,
                   tipo_alerta(l.id_variable, l.valor) AS tipo
            FROM a3i_lecturas.lectura l
        ) c
    ) g
    WHERE g.tipo IS NOT NULL
    GROUP BY g.id_variable, g.grupo
) t
JOIN variable v ON v.id_variable = t.id_variable
JOIN dispositivo d ON d.id_dispositivo = v.id_sensor
JOIN sector s ON s.id_sector = d.id_sector
ORDER BY t.inicio, t.id_variable;

-- Detección (RF-039): después de cada lectura válida (la de RF-030 ya ha
-- descartado las imposibles). Solo una alerta activa por variable: si ya hay
-- una, no se crea otra, pero un aviso sube a alarma
USE a3i_lecturas;

DELIMITER //

CREATE TRIGGER detectar_alerta AFTER INSERT ON lectura
FOR EACH ROW
BEGIN
    DECLARE v_tipo VARCHAR(10);
    DECLARE v_id_alerta INT DEFAULT NULL;
    DECLARE v_tipo_activa VARCHAR(10);
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_id_alerta = NULL;

    SET v_tipo = a3i.tipo_alerta(NEW.id_variable, NEW.valor);
    IF v_tipo IS NOT NULL THEN
        SELECT id_alerta, tipo INTO v_id_alerta, v_tipo_activa
        FROM a3i.alerta
        WHERE id_variable = NEW.id_variable AND estado <> 'resuelta'
        LIMIT 1;

        IF v_id_alerta IS NULL THEN
            INSERT INTO a3i.alerta (id_variable, tipo, id_lectura)
            VALUES (NEW.id_variable, v_tipo, NEW.id_lectura);
        ELSEIF v_tipo = 'alarma' AND v_tipo_activa = 'aviso' THEN
            UPDATE a3i.alerta
            SET tipo = 'alarma', id_lectura_alarma = NEW.id_lectura
            WHERE id_alerta = v_id_alerta;
        END IF;
    END IF;
END //

DELIMITER ;
