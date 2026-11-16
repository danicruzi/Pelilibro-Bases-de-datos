#Sesiones de usuario con expiración deslizante (TTL).

#sesion:{token} -> Hash (usuario_id, inicio), con TTL de 30 minutos

from __future__ import annotations

import secrets
from datetime import datetime

import redis

TTL_SESION = 1800  # 30 minutos


def _clave(token: str) -> str:
    return f"sesion:{token}"


def iniciar_sesion(r: redis.Redis, id_usuario) -> str:
    if not r.exists(f"usuario:{id_usuario}"):
        raise ValueError("El usuario no existe.")

    token = secrets.token_hex(8)
    pipe = r.pipeline(transaction=True)
    pipe.hset(_clave(token), mapping={
        "usuario_id": id_usuario,
        "inicio": datetime.now().isoformat(timespec="seconds"),
    })
    pipe.expire(_clave(token), TTL_SESION)
    pipe.execute()
    return token


def validar_sesion(r: redis.Redis, token: str) -> str | None:
    #Devuelve el id del usuario si la sesión sigue vigente y renueva su TTL.
    id_usuario = r.hget(_clave(token), "usuario_id")
    if id_usuario is None:
        return None
    r.expire(_clave(token), TTL_SESION)  # expiración deslizante
    return id_usuario


def cerrar_sesion(r: redis.Redis, token: str) -> bool:
    return r.delete(_clave(token)) == 1


def tiempo_restante(r: redis.Redis, token: str) -> int:
    #Segundos restantes (-2 si la sesión ya no existe).
    return r.ttl(_clave(token))