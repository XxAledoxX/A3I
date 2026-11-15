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

-- Un usuario por cada combinación de perfil y rango que se usa en las pruebas de permisos
INSERT INTO usuario (nombre, login, hash_contrasena, rango, nivel, perfil, id_sector)
VALUES
    ('Elena Navarro', 'cientifico2',
     '$argon2id$v=19$m=65536,t=3,p=4$3BEAJLxkxw3PCmh1C9Xt1w$V1v7g8EXBla4f7BoF/JrfV69dHfITYiwOv6gXqPQ8/c',
     'empleado', 3, 'cientificos',
     (SELECT id_sector FROM sector WHERE nombre = 'critico')),
    ('Javier Morales', 'jefesector_cien',
     '$argon2id$v=19$m=65536,t=3,p=4$TXDtGdBvrg7HMN4HBKy+9Q$cNBafOy48054XBuDcE/M022BPNwg6zR1zSU3I5SLp4M',
     'jefe_sector', 3, 'cientificos',
     (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('Carmen Ruiz', 'subjefe_cien',
     '$argon2id$v=19$m=65536,t=3,p=4$UAD4iuFXDgiofzsbS7l6kA$dnDIgVlF/x4ULc38z4TglWaZASfZznbGax7n6glraJU',
     'subjefe_perfil', 2, 'cientificos',
     (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('Pablo Serrano', 'jefe_cien',
     '$argon2id$v=19$m=65536,t=3,p=4$IgRVvgcmpGdZgIZKpVk+MA$T1jcQ1F3KBsQYIy7KBNLZ4zY2DKdofTrOnot4L/X/BA',
     'jefe_perfil', 3, 'cientificos',
     (SELECT id_sector FROM sector WHERE nombre = 'critico')),
    ('Raúl Castillo', 'jefesector_seg',
     '$argon2id$v=19$m=65536,t=3,p=4$5AxJBN/0z1w9ATApQsHdNA$RwFQ2craPeQO7tHLMbU7ESw9cC/+mDrRGrEf2W3/Hi8',
     'jefe_sector', 2, 'seguridad',
     (SELECT id_sector FROM sector WHERE nombre = 'general')),
    ('Marta Delgado', 'subjefe_seg',
     '$argon2id$v=19$m=65536,t=3,p=4$P8Y8qLZZMp2KC/+8c6bQYg$y4P9lQl+cKL5w/Fh2hlfyJMBmq0CTY5/DI54ojFa6GI',
     'subjefe_perfil', 4, 'seguridad',
     (SELECT id_sector FROM sector WHERE nombre = 'general')),
    ('Andrés Romero', 'jefe_seg',
     '$argon2id$v=19$m=65536,t=3,p=4$sgXnJehuZmWjX6iZXvpF5Q$Lgy6NW7KF0s/uKGdPI0VEWhf795eD3sjPGNweOFTDc8',
     'jefe_perfil', 4, 'seguridad',
     (SELECT id_sector FROM sector WHERE nombre = 'general')),
    ('Sara Molina', 'tech2',
     '$argon2id$v=19$m=65536,t=3,p=4$mKaTiALatVTR4qHp78+mFQ$pEBSTqNXpZBg5laCDrTHH42g57WxnZVBLhE8LcQ4Ecw',
     'empleado', 1, 'tech',
     (SELECT id_sector FROM sector WHERE nombre = 'critico')),
    ('Iván Herrero', 'subjefe_tech',
     '$argon2id$v=19$m=65536,t=3,p=4$BmM3IXczjEFd/YyfKGiwog$I6ePNk9dTfIYHF19SZh3Q9qwAyoGWE2f5cjvrsuIHlY',
     'subjefe_perfil', 2, 'tech',
     (SELECT id_sector FROM sector WHERE nombre = 'cientifico')),
    ('Laura Vidal', 'jefe_tech',
     '$argon2id$v=19$m=65536,t=3,p=4$7LwK7gTHWyaXokBD6bOQwg$XCL0L0epxjLttwGkhYKmiDZGIwcJsuUUmIf8dcIcNcw',
     'jefe_perfil', 3, 'tech',
     (SELECT id_sector FROM sector WHERE nombre = 'critico'));
