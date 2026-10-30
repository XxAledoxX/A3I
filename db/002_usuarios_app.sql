-- Usuario a3i_app que usa la aplicación, con los permisos justos

SET NAMES utf8mb4;
USE a3i;

DROP USER IF EXISTS 'a3i_app'@'localhost';
DROP USER IF EXISTS 'a3i_app'@'127.0.0.1';

-- La contraseña llega en @a3i_app_password desde reset_db.sh (sale del .env)
SET @crear = CONCAT('CREATE USER ''a3i_app''@''localhost'' IDENTIFIED BY ',
                    QUOTE(@a3i_app_password));
PREPARE stmt FROM @crear;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @crear = CONCAT('CREATE USER ''a3i_app''@''127.0.0.1'' IDENTIFIED BY ',
                    QUOTE(@a3i_app_password));
PREPARE stmt FROM @crear;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

GRANT SELECT ON a3i.perfil TO 'a3i_app'@'localhost', 'a3i_app'@'127.0.0.1';
GRANT SELECT, UPDATE (intentos_fallidos, estado, hash_contrasena) ON a3i.usuario
    TO 'a3i_app'@'localhost', 'a3i_app'@'127.0.0.1';

FLUSH PRIVILEGES;
