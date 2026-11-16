"""CRUD del catálogo de películas y libros sobre Redis.

Modelo de claves:
  item:{tipo}:{id}      -> Hash con los datos del ítem
  idx:genero:{genero}   -> Set de referencias "tipo:id"
  idx:tipo:{tipo}       -> Set de referencias "tipo:id"
  ranking:visitas       -> Sorted Set (puntaje = visitas)
  contador:item         -> String autoincremental de ids
"""
from __future__ import annotations

import redis 

TIPOS_VALIDOS = ("pelicula", "libro")
CAMPOS_EDITABLES= {"titulo", "anio", "genero", "autor_director", "descripcion"}

def normalizar_genero(genero: str) -> str:
    #Normaliza el genero para usarlo en claves: minusculas y sin espacios
    return genero.strip().lower().replace(" ", "_")

def _clave_item(tipo: str, id_item) -> str:
    return f"item:{tipo}:{id_item}"

def _referencia(tipo: str, id_item) -> str:
    return f"{tipo}:{id_item}"


def crear_item(r: redis.Redis, tipo: str, titulo: str, anio: int, genero: str, autor_director: str, descripcion: str = "") -> int:
    #Crea un item y lo registra en sus indices
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"Tipo invalido. Use: {', '.join(TIPOS_VALIDOS)}")
    
    id_item = r.incr("contador:item")
    genero = normalizar_genero(genero)
    ref = _referencia(tipo, id_item)
    
    pipe = r.pipeline(transaction=True) #MULTI/EXEC
    pipe.hset(_clave_item(tipo, id_item), mapping={
        "titulo": titulo,
        "tipo": tipo,
        "anio": anio,
        "genero": genero,
        "autor_director": autor_director,
        "descripcion": descripcion,
    })
    pipe.sadd(f"idx:genero:{genero}", ref)
    pipe.sadd(f"idx:tipo:{tipo}", ref)
    pipe.zadd("ranking:visitas", {ref: 0})
    pipe.execute()
    return id_item

def leer_item (r: redis.Redis, tipo:str, id_item) -> dict | None:
    #Devuelve el item como diccionario, o None si no existe
    datos = r.hgetall(_clave_item(tipo, id_item))
    if not datos:
        return None
    datos["id"] = str(id_item)
    return datos

def listar_items(r: redis.Redis, tipo: str | None = None,
                 genero: str | None = None) -> list[dict]:
    #Lista ítems usando los índices; combina filtros con SINTER.
    indices = []
    if tipo:
        indices.append(f"idx:tipo:{tipo}")
    if genero:
        indices.append(f"idx:genero:{normalizar_genero(genero)}")

    if not indices:
        refs = r.sunion("idx:tipo:pelicula", "idx:tipo:libro")
    elif len(indices) == 1:
        refs = r.smembers(indices[0])
    else:
        refs = r.sinter(*indices)

    refs = sorted(refs, key=lambda x: int(x.split(":")[1]))

    pipe = r.pipeline(transaction=False)
    for ref in refs:
        t, i = ref.split(":")
        pipe.hgetall(_clave_item(t, i))
    resultados = pipe.execute()

    items = []
    for ref, datos in zip(refs, resultados):
        if datos:  # ignora referencias a ítems ya eliminados
            datos["id"] = ref.split(":")[1]
            items.append(datos)
    return items

def actualizar_item (r: redis.Redis, tipo: str, id_item, **campos) -> bool:
    #Actualiza campos de un item; si cambia el genero, mueve el indice
    clave = _clave_item(tipo, id_item)
    actual = r.hgetall(clave)
    if not actual:
        return False

    campos = {k: v for k, v in campos.items()
              if k in CAMPOS_EDITABLES and v not in (None, "")}
    if not campos:
        return False

    ref = _referencia(tipo, id_item)
    pipe = r.pipeline(transaction=True)
    if "genero" in campos:
        campos["genero"] = normalizar_genero(campos["genero"])
        pipe.srem(f"idx:genero:{actual.get('genero', '')}", ref)
        pipe.sadd(f"idx:genero:{campos['genero']}", ref)
    pipe.hset(clave, mapping=campos)
    pipe.execute()
    return True

def eliminar_item(r: redis.Redis, tipo: str, id_item) -> bool:
    #Elimina el ítem y sus entradas en índices y ranking.
    clave = _clave_item(tipo, id_item)
    item = r.hgetall(clave)
    if not item:
        return False

    ref = _referencia(tipo, id_item)
    pipe = r.pipeline(transaction=True)
    pipe.delete(clave)
    pipe.srem(f"idx:genero:{item.get('genero', '')}", ref)
    pipe.srem(f"idx:tipo:{tipo}", ref)
    pipe.zrem("ranking:visitas", ref)
    pipe.execute()
    return True

def items_desde_referencias (r: redis.Redis, refs) -> list[dict]:
    #Convierte referencias 'tipo:id' en ítems, conservando el orden. Ignora las referencias a ítems que ya no existen.
    refs = list(refs)
    pipe = r.pipeline(transaction=False)
    for ref in refs:
        tipo, id_item = ref.split(":")
        pipe.hgetall(_clave_item(tipo, id_item))
    resultados = pipe.execute()

    items = []
    for ref, datos in zip(refs, resultados):
        if datos:
            datos["id"] = ref.split(":")[1]
            items.append(datos)
    return items