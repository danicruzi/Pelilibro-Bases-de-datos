#Seeding script: limpia la base y carga datos iniciales 

import os 
import random
import sys 

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.conexion import obtener_cliente
from src import catalogo, usuarios

PREFIJOS = ("item:", "idx:", "ranking:", "usuario:", "sesion:", "cache:", "contador:", "prueba:")

#(tipo, titulo, año, genero, autor/director)
DATOS = [
    ("pelicula", "Matrix", 1999, "ciencia ficcion", "Lana y Lilly Wachowski"),
    ("pelicula", "El Padrino", 1972, "drama", "Francis Ford Coppola"),
    ("pelicula", "Inception", 2010, "ciencia ficcion", "Christopher Nolan"),
    ("pelicula", "Coco", 2017, "animacion", "Lee Unkrich"),
    ("pelicula", "Pulp Fiction", 1994, "crimen", "Quentin Tarantino"),
    ("pelicula", "El laberinto del fauno", 2006, "fantasia", "Guillermo del Toro"),
    ("pelicula", "Parásitos", 2019, "drama", "Bong Joon-ho"),
    ("pelicula", "Mad Max: Fury Road", 2015, "accion", "George Miller"),
    ("pelicula", "Amores perros", 2000, "drama", "Alejandro González Iñárritu"),
    ("pelicula", "Interstellar", 2014, "ciencia ficcion", "Christopher Nolan"),
    ("pelicula", "The Lighthouse", 2019, "terror psicologico", "Robert Eggers"),
    ("pelicula", "Se7en", 1995, "thriller", "David Fincher"),
    ("pelicula", "Edward Scissorhands", 1990, "fantasia", "Tim Burton"),
    ("libro", "Cien años de soledad", 1967, "realismo magico", "Gabriel García Márquez"),
    ("libro", "1984", 1949, "distopia", "George Orwell"),
    ("libro", "El principito", 1943, "fantasia", "Antoine de Saint-Exupéry"),
    ("libro", "Don Quijote de la Mancha", 1605, "clasico", "Miguel de Cervantes"),
    ("libro", "Pedro Páramo", 1955, "realismo magico", "Juan Rulfo"),
    ("libro", "Fahrenheit 451", 1953, "distopia", "Ray Bradbury"),
    ("libro", "Dune", 1965, "ciencia ficcion", "Frank Herbert"),
    ("libro", "El Aleph", 1949, "fantasia", "Jorge Luis Borges"),
    ("libro", "Orgullo y prejuicio", 1813, "romance", "Jane Austen"),
    ("libro", "Rayuela", 1963, "novela", "Julio Cortázar"),
    ("libro", "A Game of Thrones", 1996, "fantasia", "George R R Martin"),
    ("libro", "Frankenstein o el moderno prometeo", 1818, "ciencia ficcion", "Mary Shelley"),
]

USUARIOS = [
    ("Daniel Cruz", "dani.cruz@gmail.com"),
    ("Luis Martinez", "luis@gmail.com"),
    ("David Magana", "davidma@gmail.com"),
]

def limpiar(r) -> int:
    #Borra las claves de la aplicación (solo con los prefijos del proyecto).
    borradas = 0
    for prefijo in PREFIJOS:
        claves = list(r.scan_iter(match=f"{prefijo}*"))
        if claves:
            borradas += r.delete(*claves)
    return borradas


def main():
    r = obtener_cliente()

    print(f"Claves anteriores eliminadas: {limpiar(r)}")

    # Catálogo con visitas iniciales aleatorias (reproducibles)
    random.seed(42)
    creados = []  # [(tipo, id)] en el mismo orden que DATOS
    for tipo, titulo, anio, genero, autor in DATOS:
        id_item = catalogo.crear_item(r, tipo, titulo, anio, genero, autor)
        creados.append((tipo, id_item))
        r.zincrby("ranking:visitas", random.randint(1, 50), f"{tipo}:{id_item}")

    # Usuarios de ejemplo
    ids_usuarios = [usuarios.crear_usuario(r, n, c) for n, c in USUARIOS]
    u1, u2, u3 = ids_usuarios

    # Favoritos: Matrix, Inception y Cien años de soledad para el usuario 1
    for pos in (0, 2, 13):
        usuarios.agregar_favorito(r, u1, *creados[pos])
    for pos in (3, 5):  # Coco y El laberinto del fauno para el usuario 2
        usuarios.agregar_favorito(r, u2, *creados[pos])
    for pos in (0, 2, 9, 19):  # Matrix, Inception, Interstellar y Dune
        usuarios.agregar_favorito(r, u3, *creados[pos])

    # Vistos recientemente del usuario 1
    for pos in (0, 1, 2, 3):
        usuarios.registrar_visualizacion(r, u1, *creados[pos])

    print("\n--- Resumen de la carga ---")
    print("Películas:", r.scard("idx:tipo:pelicula"))
    print("Libros:   ", r.scard("idx:tipo:libro"))
    print("En ranking:", r.zcard("ranking:visitas"))
    print("Géneros distintos:", len(list(r.scan_iter(match="idx:genero:*"))))
    print("Usuarios:", r.scard("idx:usuarios"))
    print("Datos iniciales cargados correctamente.")


if __name__ == "__main__":
    main()