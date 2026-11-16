"""Consultas especializadas sobre el modelo Clave-Valor.

Operaciones destacadas:
  - Sorted Set: ranking de popularidad (ZREVRANGE, ZREVRANK, ZINTERSTORE)
  - Sets: filtros por intersección y unión (SINTER, SUNION, SDIFF)
  - Caché con TTL: SETEX con expiración de 5 minutos
  - Recomendaciones por afinidad entre favoritos de usuarios
"""
from __future__ import annotations

import json

import redis

from src.catalogo import items_desde_referencias, listar_items, normalizar_genero

TTL_CACHE = 300  # 5 minutos


# ------------------------------- Géneros -------------------------------
def listar_generos(r: redis.Redis) -> list[tuple[str, int]]:
    """Devuelve [(género, cantidad de ítems)] usando los índices de géneros."""
    generos = []
    for clave in r.scan_iter(match="idx:genero:*"):
        nombre = clave.split(":", 2)[2]
        generos.append((nombre, r.scard(clave)))
    return sorted(generos)


# -------------------------------- Ranking --------------------------------
def top_populares(r: redis.Redis, n: int = 10, tipo: str | None = None) -> list[dict]:
    """Top N por visitas. Con 'tipo', intersecta el ranking con el índice de tipo."""
    if tipo:
        tmp = f"tmp:top:{tipo}"
        pipe = r.pipeline(transaction=True)
        # El peso 0 del Set conserva el puntaje original del ranking
        pipe.zinterstore(tmp, {"ranking:visitas": 1, f"idx:tipo:{tipo}": 0})
        pipe.zrevrange(tmp, 0, n - 1, withscores=True)
        pipe.delete(tmp)
        resultado = pipe.execute()[1]
    else:
        resultado = r.zrevrange("ranking:visitas", 0, n - 1, withscores=True)

    visitas = {ref: int(puntaje) for ref, puntaje in resultado}
    items = items_desde_referencias(r, [ref for ref, _ in resultado])
    for item in items:
        item["visitas"] = visitas[f"{item['tipo']}:{item['id']}"]
    return items


def posicion_ranking(r: redis.Redis, tipo: str, id_item) -> dict | None:
    """Posición (1 = más visto) y visitas de un ítem."""
    ref = f"{tipo}:{id_item}"
    pos = r.zrevrank("ranking:visitas", ref)
    if pos is None:
        return None
    return {"posicion": pos + 1, "visitas": int(r.zscore("ranking:visitas", ref))}


# ------------------------- Búsqueda con caché (TTL) -------------------------
def buscar(r: redis.Redis, tipo: str | None = None,
           genero: str | None = None) -> tuple[list[dict], bool]:
    """Búsqueda por tipo y/o género con caché.

    Devuelve (resultados, desde_cache).
    """
    gen = normalizar_genero(genero) if genero else "todos"
    clave = f"cache:busqueda:{tipo or 'todos'}:{gen}"

    en_cache = r.get(clave)
    if en_cache is not None:
        return json.loads(en_cache), True

    items = listar_items(r, tipo, genero)
    r.setex(clave, TTL_CACHE, json.dumps(items, ensure_ascii=False))
    return items, False


def invalidar_cache(r: redis.Redis) -> int:
    """Elimina todas las búsquedas en caché (útil tras crear, editar o borrar ítems)."""
    claves = list(r.scan_iter(match="cache:*"))
    return r.delete(*claves) if claves else 0


# --------------------- Consultas con conjuntos (Sets) ---------------------
def buscar_por_generos(r: redis.Redis, generos: list[str],
                       modo: str = "alguno") -> list[dict]:
    """modo='todos' -> SINTER (cumple todos los géneros); 'alguno' -> SUNION."""
    claves = [f"idx:genero:{normalizar_genero(g)}" for g in generos]
    refs = r.sinter(*claves) if modo == "todos" else r.sunion(*claves)
    refs = sorted(refs, key=lambda x: int(x.split(":")[1]))
    return items_desde_referencias(r, refs)


def buscar_por_titulo(r: redis.Redis, texto: str) -> list[dict]:
    """Búsqueda simple por coincidencia en el título.

    Nota: Redis básico no tiene búsqueda de texto completo (requiere el módulo
    RediSearch); con un catálogo pequeño basta filtrar en la aplicación.
    """
    texto = texto.strip().lower()
    return [i for i in listar_items(r) if texto in i["titulo"].lower()]


# ------------------------------ Recomendaciones ------------------------------
def recomendar(r: redis.Redis, id_usuario, limite: int = 5) -> list[dict]:
    """Recomienda ítems según afinidad con otros usuarios.

    Afinidad = cantidad de favoritos en común (SINTER). Se recomiendan los
    favoritos del otro usuario que el actual aún no tiene (SDIFF).
    """
    mis_favoritos = f"usuario:{id_usuario}:favoritos"
    if not r.scard(mis_favoritos):
        return []

    puntajes: dict[str, int] = {}
    for otro in r.smembers("idx:usuarios"):
        if otro == str(id_usuario):
            continue
        favoritos_otro = f"usuario:{otro}:favoritos"
        afinidad = len(r.sinter(mis_favoritos, favoritos_otro))
        if afinidad == 0:
            continue
        for ref in r.sdiff(favoritos_otro, mis_favoritos):
            puntajes[ref] = puntajes.get(ref, 0) + afinidad

    ordenados = sorted(puntajes.items(), key=lambda kv: (-kv[1], kv[0]))[:limite]
    items = items_desde_referencias(r, [ref for ref, _ in ordenados])
    for item in items:
        item["afinidad"] = puntajes[f"{item['tipo']}:{item['id']}"]
    return items