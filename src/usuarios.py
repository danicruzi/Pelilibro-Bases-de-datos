"""Usuarios, favoritos y vistos recientemente sobre Redis.

Modelo de claves:
  usuario:{id}                -> Hash (nombre, correo, fecha_registro)
  usuario:{id}:favoritos      -> Set de referencias "tipo:id"
  usuario:{id}:recientes      -> List (más reciente primero, máx. 10)
  idx:usuarios                -> Set con los ids de usuarios
  idx:correo:{correo}         -> String con el id (garantiza correo único)
  contador:usuario            -> String autoincremental
"""
from __future__ import annotations

from datetime import datetime 

import redis 

from src.catalogo import items_desde_referencias

MAX_RECIENTES = 10

def _clave (id_usuario) -> str:
    return f"usuario:{id_usuario}"

def crear_usuario(r: redis.Redis, nombre: str, correo: str) -> int:
    correo = correo.strip().lower()
    id_usuario = r.incr("contador:usuario")

    # SET con NX solo escribe si la clave no existe: unicidad del correo
    if not r.set(f"idx:correo:{correo}", id_usuario, nx=True):
        raise ValueError("El correo ya está registrado.")

    pipe = r.pipeline(transaction=True)
    pipe.hset(_clave(id_usuario), mapping={
        "nombre": nombre,
        "correo": correo,
        "fecha_registro": datetime.now().isoformat(timespec="seconds"),
    })
    pipe.sadd("idx:usuarios", id_usuario)
    pipe.execute()
    return id_usuario


def leer_usuario(r: redis.Redis, id_usuario) -> dict | None:
    datos = r.hgetall(_clave(id_usuario))
    if not datos:
        return None
    datos["id"] = str(id_usuario)
    return datos


def listar_usuarios(r: redis.Redis) -> list[dict]:
    ids = sorted(r.smembers("idx:usuarios"), key=int)
    pipe = r.pipeline(transaction=False)
    for id_usuario in ids:
        pipe.hgetall(_clave(id_usuario))
    resultados = pipe.execute()

    usuarios = []
    for id_usuario, datos in zip(ids, resultados):
        if datos:
            datos["id"] = id_usuario
            usuarios.append(datos)
    return usuarios


def actualizar_usuario(r: redis.Redis, id_usuario, nombre: str | None = None,
                       correo: str | None = None) -> bool:
    actual = r.hgetall(_clave(id_usuario))
    if not actual:
        return False

    cambios = {}
    if nombre:
        cambios["nombre"] = nombre
    if correo:
        correo = correo.strip().lower()
        if correo != actual.get("correo"):
            if not r.set(f"idx:correo:{correo}", id_usuario, nx=True):
                raise ValueError("El correo ya está registrado.")
            r.delete(f"idx:correo:{actual.get('correo', '')}")
            cambios["correo"] = correo

    if not cambios:
        return False
    r.hset(_clave(id_usuario), mapping=cambios)
    return True


def eliminar_usuario(r: redis.Redis, id_usuario) -> bool:
    actual = r.hgetall(_clave(id_usuario))
    if not actual:
        return False

    pipe = r.pipeline(transaction=True)
    pipe.delete(
        _clave(id_usuario),
        f"{_clave(id_usuario)}:favoritos",
        f"{_clave(id_usuario)}:recientes",
        f"idx:correo:{actual.get('correo', '')}",
    )
    pipe.srem("idx:usuarios", id_usuario)
    pipe.execute()
    return True

def _validar(r: redis.Redis, id_usuario, tipo: str, id_item) -> None:
    if not r.exists(_clave(id_usuario)):
        raise ValueError("El usuario no existe.")
    if not r.exists(f"item:{tipo}:{id_item}"):
        raise ValueError("El ítem no existe.")


def agregar_favorito(r: redis.Redis, id_usuario, tipo: str, id_item) -> bool:
    """Devuelve True si se agregó, False si ya estaba (el Set evita duplicados)."""
    _validar(r, id_usuario, tipo, id_item)
    return r.sadd(f"{_clave(id_usuario)}:favoritos", f"{tipo}:{id_item}") == 1


def quitar_favorito(r: redis.Redis, id_usuario, tipo: str, id_item) -> bool:
    return r.srem(f"{_clave(id_usuario)}:favoritos", f"{tipo}:{id_item}") == 1


def listar_favoritos(r: redis.Redis, id_usuario) -> list[dict]:
    refs = r.smembers(f"{_clave(id_usuario)}:favoritos")
    refs = sorted(refs, key=lambda x: int(x.split(":")[1]))
    return items_desde_referencias(r, refs)

def registrar_visualizacion(r: redis.Redis, id_usuario, tipo: str, id_item) -> dict:
    #Registra que el usuario vio un ítem.

    #- Lo coloca al inicio de su lista de recientes (sin duplicados, máx. 10).
    #- Suma una visita en el ranking global.
    
    _validar(r, id_usuario, tipo, id_item)
    ref = f"{tipo}:{id_item}"
    clave_recientes = f"{_clave(id_usuario)}:recientes"

    pipe = r.pipeline(transaction=True)
    pipe.lrem(clave_recientes, 0, ref)             # quita repetidos
    pipe.lpush(clave_recientes, ref)               # lo pone al inicio
    pipe.ltrim(clave_recientes, 0, MAX_RECIENTES - 1)  # conserva los últimos 10
    pipe.zincrby("ranking:visitas", 1, ref)        # suma una visita
    pipe.execute()

    return items_desde_referencias(r, [ref])[0]


def listar_recientes(r: redis.Redis, id_usuario) -> list[dict]:
    refs = r.lrange(f"{_clave(id_usuario)}:recientes", 0, -1)
    return items_desde_referencias(r, refs)

def buscar_por_correo(r: redis.Redis, correo: str) -> str | None:
    """Devuelve el id del usuario asociado al correo, o None si no existe."""
    return r.get(f"idx:correo:{correo.strip().lower()}")