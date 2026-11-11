-- Sectores y usuarios de prueba (contraseñas en db/README.md)

SET NAMES utf8mb4;
USE a3i;

INSERT INTO sector (nombre, nivel, perfil) VALUES
    ('general', 1, 'seguridad'),
    ('cientifico', 2, 'cientificos'),
    ('critico', 3, 'cientificos');

INSERT INTO usuario (nombre, login, hash_contrasena, rango, nivel, perfil, id_sector)
VALUES
    ('Lucía Herrera', 'cientifico1',
     '$argon2id$v=19$m=65536,t=3,p=4$bgLkLYVlOgd7COtabmMEcg$5WXeFCZF9wO6fuse2Gyln0kpQxKEECAzyV33VyphH1g',
     'empleado', 2, 'cientificos',
     (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('Marcos Ibáñez', 'seguridad1',
     '$argon2id$v=19$m=65536,t=3,p=4$YSA/cKUigyZeDIcgjkQ5/w$E7VA7BRVI5+IlXkUuzBvdIvWcj2ceprYyaXdA6P+48M',
     'empleado', 1, 'seguridad',
     (SELECT id_sector FROM sector WHERE nombre = 'general')),
    ('Daniel Ortega', 'tech1',
     '$argon2id$v=19$m=65536,t=3,p=4$oB38DR7WOtUdufAvi1KcUw$ckEJkv+E6mLDi91ZybOfLBGpjdOBkgK2RQtoP/w23JA',
     'empleado', 1, 'tech',
     (SELECT id_sector FROM sector WHERE nombre = 'general'));
