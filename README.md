# PeliLibros: catálogo de películas y libros con Redis Cloud

Proyecto individual de Bases de Datos Avanzadas.
Marco Daniel Cruz Ixta · Quinto semestre de Ing. en TI 

Aplicación de consola en Python conectada a una base de datos NoSQL Clave-Valor (Redis) alojada en Redis Cloud (servicio administrado). Permite administrar un catálogo de películas y libros, usuarios con sesiones, favoritos, vistos recientemente, ranking de popularidad, búsquedas con caché y recomendaciones.

## Tecnologías
- Python 3.9 o superior
- Redis Cloud (plan gratuito de 30 MB)
- Driver oficial `redis-py` y `python-dotenv`

## Requerimientos
- Python 3.9+ y `pip`
- Una base de datos Redis en la nube (se explica abajo)
- Conexión a internet

## Instalación

```bash
git clone [URL_DEL_REPOSITORIO]
cd catalogo-redis

python -m venv venv
# Windows: venv\Scripts\activate    |    Linux/Mac: source venv/bin/activate

pip install -r requirements.txt
```

## Configuración de la base de datos en la nube
1. Cree una cuenta en [redis.io/try-free](https://redis.io/try-free) y una base de datos del plan **Free (30 MB)**.
2. Copie el *Public endpoint* (host y puerto), el usuario y la contraseña.
3. Copie `.env.example` como `.env` y complete los datos:

```
REDIS_HOST=su-host.db.redis.io
REDIS_PORT=12345
REDIS_USER=default
REDIS_PASSWORD=su_contraseña
```

> Las credenciales se leen exclusivamente desde variables de entorno. El archivo `.env` no se sube al repositorio.

## Cargar los datos iniciales (seeding)
```bash
python scripts/seed.py
```
Limpia las claves del proyecto y carga 25 ítems (películas y libros), 3 usuarios, favoritos, vistos recientemente y un ranking inicial. Puede ejecutarse varias veces.

## Ejecutar la aplicación
```bash
python main.py
```
Usuario de ejemplo para iniciar sesión: `dani.cruz@gmail.com`

## Pruebas
```bash
python scripts/probar_conexion.py     # conexión, escritura, lectura y TTL
python scripts/probar_usuarios.py     # usuarios, favoritos, recientes y sesiones
python scripts/probar_consultas.py    # ranking, caché, conjuntos y recomendaciones
python scripts/prueba_integral.py     # prueba automática de punta a punta
```

## Estructura del proyecto
```
catalogo-redis/
├── main.py                    # punto de entrada
├── src/
│   ├── conexion.py            # conexión a Redis Cloud
│   ├── catalogo.py            # CRUD de ítems e índices
│   ├── usuarios.py            # usuarios, favoritos y recientes
│   ├── sesiones.py            # sesiones con TTL deslizante
│   ├── consultas.py           # ranking, caché, conjuntos, recomendaciones
│   └── menu.py                # interfaz de consola
├── scripts/                   # seeding y pruebas
├── .env.example
├── requirements.txt
└── README.md
```

## Modelo de claves

| Clave | Estructura | Uso | TTL |
|---|---|---|---|
| `item:{tipo}:{id}` | Hash | Datos del ítem | No |
| `idx:genero:{genero}` | Set | Índice por género | No |
| `idx:tipo:{tipo}` | Set | Índice por tipo | No |
| `ranking:visitas` | Sorted Set | Popularidad | No |
| `usuario:{id}` | Hash | Perfil | No |
| `usuario:{id}:favoritos` | Set | Favoritos | No |
| `usuario:{id}:recientes` | List | Últimos 10 vistos | No |
| `idx:correo:{correo}` | String | Correo único | No |
| `sesion:{token}` | Hash | Sesión activa | 30 min (deslizante) |
| `cache:busqueda:{tipo}:{genero}` | String (JSON) | Caché de búsquedas | 5 min |

## Notas
- El plan gratuito de Redis Cloud ofrece 30 MB y un límite de operaciones por segundo, suficiente para este proyecto.
- Las operaciones sobre varias claves usan pipelines transaccionales (`MULTI/EXEC`).
