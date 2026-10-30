# A3I

Dashboard de escritorio para una central nuclear (maqueta) con tres perfiles: Científicos, Seguridad y Tech.

Proyecto de Ingeniería I, Universidad Europea, curso 2026-2027.
Equipo: Alejandro Dotor, Arturo Fernández y Aarón Peñafiel.

## Ramas

- `main`: versión estable de cada sprint, con tag.
- `production`: solo recibe de `main`.
- `development`: de aquí salen las ramas de tarea (`AD/RF-004-login`, ...) y aquí vuelven por PR.

## Instalación

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
