# VidaPlena

Red de clínicas **ficticia** usada como base del taller de auditoría y corrección de seguridad de
datos — Seguridad Informática, Ingeniería Multimedia, UMNG (Sesión 7).

Este repositorio contiene **solo el código** de la aplicación. Las instrucciones completas del
taller (las 5 fallas a encontrar, el cronograma de la clase, la tarea y la rúbrica) están en la
guía interactiva del taller — pregúntale a tu profesor por el enlace si no lo tienes.

## Arranque rápido

```bash
git clone <url-de-este-repo>
cd vidaplena-taller
docker compose up --build
```

- Frontend: http://localhost:4200
- API / documentación interactiva: http://localhost:8000/docs
- MySQL: `localhost:3306` (usuario `vidaplena_app`, contraseña `vidaplena_app_pw`, base `vidaplena`)

Apagar: `docker compose down` (agregar `-v` para también borrar los datos).

## Estructura

```
vidaplena-taller/
├── docker-compose.yml
├── backend/     # API en FastAPI (Python) + esquema/datos de MySQL
└── frontend/    # Aplicación Angular + PrimeNG
```

## Stack

MySQL 8.0 · Python 3.11 / FastAPI · Angular 18 / PrimeNG · Docker Compose. Todo corre local, sin
ningún costo.

## Cómo entregar el resultado del taller

1. Confirma con tu profesor que ya tienes permiso de escritura (colaborador) sobre este
   repositorio — sin eso no vas a poder subir tu rama.
2. Crea tu rama a partir de `main`, nombrada con **los apellidos de todos los integrantes del
   grupo**, separados por guion y en minúscula, por ejemplo:

   ```bash
   git checkout -b taller/perez-gomez-rodriguez
   ```

3. Trabaja y confirma tus cambios normalmente en esa rama (código corregido de cada falla, y
   cualquier evidencia o nota que tu profesor haya pedido).
4. Sube la rama:

   ```bash
   git push origin taller/perez-gomez-rodriguez
   ```

No hagas push a `main` ni abras Pull Request salvo que tu profesor lo pida explícitamente — la
entrega es la rama en sí.

## Advertencia

Esta aplicación es **intencionalmente insegura**: contiene fallas de seguridad de datos sembradas
para fines educativos. No la usen como base para un sistema real sin antes corregir todas las
fallas y hacer una revisión de seguridad completa. Todos los datos (nombres, cédulas,
diagnósticos, contraseñas) son ficticios.
