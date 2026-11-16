"""Verifica las consultas especializadas: ranking, caché con TTL, conjuntos y recomendaciones."""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.conexion import obtener_cliente
from src import consultas

r = obtener_cliente()

print("=== Géneros ===")
for genero, cantidad in consultas.listar_generos(r):
    print(f" - {genero}: {cantidad}")

print("\n=== Top 5 general ===")
for i, item in enumerate(consultas.top_populares(r, 5), start=1):
    print(f" {i}. {item['titulo']} ({item['tipo']}) - {item['visitas']} visitas")

print("\n=== Top 3 películas ===")
for item in consultas.top_populares(r, 3, tipo="pelicula"):
    print(f" - {item['titulo']} - {item['visitas']} visitas")

print("\nPosición de Matrix:", consultas.posicion_ranking(r, "pelicula", 1))

print("\n=== Búsqueda con caché (fantasía) ===")
consultas.invalidar_cache(r)
for intento in (1, 2):
    resultados, desde_cache = consultas.buscar(r, genero="fantasia")
    print(f" Intento {intento}: {len(resultados)} resultados | desde caché: {desde_cache}")
print(" TTL de la caché:", r.ttl("cache:busqueda:todos:fantasia"), "segundos")

print("\n=== Géneros combinados ===")
union = consultas.buscar_por_generos(r, ["fantasia", "distopia"], modo="alguno")
inter = consultas.buscar_por_generos(r, ["fantasia", "ciencia ficcion"], modo="todos")
print(" Fantasía O distopía:", len(union), "ítems")
print(" Fantasía Y ciencia ficción:", len(inter), "ítems")

print("\n=== Búsqueda por título ('inter') ===")
for item in consultas.buscar_por_titulo(r, "inter"):
    print(" -", item["titulo"])

print("\n=== Recomendaciones para el usuario 1 ===")
for item in consultas.recomendar(r, 1):
    print(f" - {item['titulo']} (afinidad {item['afinidad']})")