-- Usuarios de prueba (contraseñas en db/README.md)

SET NAMES utf8mb4;
USE a3i;

INSERT INTO `user` (`name`, `login`, `password_hash`, `rank`, `sec_level`, `id_role`)
VALUES
    ('Lucía Herrera', 'cientifico1',
     '$argon2id$v=19$m=65536,t=3,p=4$bgLkLYVlOgd7COtabmMEcg$5WXeFCZF9wO6fuse2Gyln0kpQxKEECAzyV33VyphH1g',
     'worker', 2, (SELECT `id_role` FROM `role` WHERE `name` = 'scientist')),
    ('Marcos Ibáñez', 'seguridad1',
     '$argon2id$v=19$m=65536,t=3,p=4$YSA/cKUigyZeDIcgjkQ5/w$E7VA7BRVI5+IlXkUuzBvdIvWcj2ceprYyaXdA6P+48M',
     'worker', 1, (SELECT `id_role` FROM `role` WHERE `name` = 'security')),
    ('Daniel Ortega', 'tech1',
     '$argon2id$v=19$m=65536,t=3,p=4$oB38DR7WOtUdufAvi1KcUw$ckEJkv+E6mLDi91ZybOfLBGpjdOBkgK2RQtoP/w23JA',
     'worker', 1, (SELECT `id_role` FROM `role` WHERE `name` = 'tech'));
