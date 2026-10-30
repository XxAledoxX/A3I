-- Usuarios de prueba (contraseñas en db/README.md)

SET NAMES utf8mb4;
USE a3i;

INSERT INTO usuario (nombre, login, hash_contrasena, rango, nivel, id_perfil)
VALUES
    ('Lucía Herrera', 'cientifico1',
     '$argon2id$v=19$m=65536,t=3,p=4$bgLkLYVlOgd7COtabmMEcg$5WXeFCZF9wO6fuse2Gyln0kpQxKEECAzyV33VyphH1g',
     'empleado', 2, (SELECT id_perfil FROM perfil WHERE nombre = 'cientificos')),
    ('Marcos Ibáñez', 'seguridad1',
     '$argon2id$v=19$m=65536,t=3,p=4$YSA/cKUigyZeDIcgjkQ5/w$E7VA7BRVI5+IlXkUuzBvdIvWcj2ceprYyaXdA6P+48M',
     'empleado', 1, (SELECT id_perfil FROM perfil WHERE nombre = 'seguridad')),
    ('Daniel Ortega', 'tech1',
     '$argon2id$v=19$m=65536,t=3,p=4$oB38DR7WOtUdufAvi1KcUw$ckEJkv+E6mLDi91ZybOfLBGpjdOBkgK2RQtoP/w23JA',
     'empleado', 1, (SELECT id_perfil FROM perfil WHERE nombre = 'tech'));
