-- TLS obligatorio para los usuarios de BD de la app (RF-016).
-- Antes hay que configurar los certificados en MariaDB (db/README.md, «TLS»)

SET NAMES utf8mb4;

DELIMITER //

BEGIN NOT ATOMIC
    IF IFNULL(@@ssl_cert, '') = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'MariaDB no tiene TLS configurado: sigue el apartado TLS de db/README.md';
    END IF;
END //

DELIMITER ;

-- IF EXISTS: así no falla si algún usuario aún no se ha creado
ALTER USER IF EXISTS 'a3i_app'@'localhost', 'a3i_app'@'127.0.0.1' REQUIRE SSL;
ALTER USER IF EXISTS 'a3i_login'@'localhost', 'a3i_login'@'127.0.0.1' REQUIRE SSL;
ALTER USER IF EXISTS 'a3i_cientificos'@'localhost', 'a3i_cientificos'@'127.0.0.1' REQUIRE SSL;
ALTER USER IF EXISTS 'a3i_seguridad'@'localhost', 'a3i_seguridad'@'127.0.0.1' REQUIRE SSL;
ALTER USER IF EXISTS 'a3i_tech'@'localhost', 'a3i_tech'@'127.0.0.1' REQUIRE SSL;
ALTER USER IF EXISTS 'a3i_simulador'@'localhost', 'a3i_simulador'@'127.0.0.1' REQUIRE SSL;

FLUSH PRIVILEGES;
