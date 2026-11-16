"""Menú principal de la aplicación (consola).

Orquesta el catálogo, los usuarios, las sesiones con TTL y las consultas
especializadas sobre Redis Cloud.
"""
from __future__ import annotations

import redis

from src import catalogo, consultas, sesiones, usuarios


# ============================ Utilidades de entrada ============================
def leer_texto(mensaje: str, obligatorio: bool = True) -> str:
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("  El campo no puede estar vacío.")


def leer_entero(mensaje: str, minimo: int | None = None, maximo: int | None = None,
                obligatorio: bool = True) -> int | None:
    while True:
        valor = input(mensaje).strip()
        if not valor and not obligatorio:
            return None
        if valor.isdigit():
            numero = int(valor)
            if (minimo is None or numero >= minimo) and \
               (maximo is None or numero <= maximo):
                return numero
        print("  Ingrese un número entero válido.")


def confirmar(mensaje: str) -> bool:
    return input(f"{mensaje} (s/n): ").strip().lower() == "s"


def elegir_tipo(obligatorio: bool = True) -> str | None:
    print("  1. Película   2. Libro")
    while True:
        opcion = input("  Tipo: " if obligatorio else "  Tipo (Enter para todos): ").strip()
        if opcion == "1":
            return "pelicula"
        if opcion == "2":
            return "libro"
        if not opcion and not obligatorio:
            return None
        print("  Opción no válida.")


def _pausar() -> None:
    input("\n  Presione Enter para continuar...")


# ================================ Presentación ================================
def mostrar_item(item: dict, extra: str = "") -> None:
    print(f"  [{item['id']}] {item['titulo']} ({item['tipo']}, {item.get('anio', '?')}) "
          f"- {item['genero']} - {item['autor_director']}{extra}")


def mostrar_lista(items: list[dict]) -> None:
    if not items:
        print("  (sin resultados)")
        return
    for item in items:
        mostrar_item(item)
    print(f"\n  Total: {len(items)}")


def mostrar_detalle(r: redis.Redis, item: dict) -> None:
    print(f"\n  ID:             {item['id']}")
    print(f"  Tipo:           {item['tipo']}")
    print(f"  Título:         {item['titulo']}")
    print(f"  Año:            {item.get('anio', '')}")
    print(f"  Género:         {item['genero']}")
    print(f"  Autor/Director: {item['autor_director']}")
    print(f"  Descripción:    {item.get('descripcion') or '(sin descripción)'}")
    ranking = consultas.posicion_ranking(r, item["tipo"], item["id"])
    if ranking:
        print(f"  Ranking:        puesto {ranking['posicion']} con {ranking['visitas']} visitas")


def _encabezado(r: redis.Redis, estado: dict) -> None:
    print("\n" + "=" * 58)
    print("  PELILIBROS - Catálogo de películas y libros (Redis Cloud)")
    print("=" * 58)
    if estado["token"]:
        ttl = sesiones.tiempo_restante(r, estado["token"])
        if ttl > 0:
            print(f"  Sesión: {estado['nombre']} (expira en {ttl // 60} min {ttl % 60} s)")
            return
        print("  Su sesión expiró por inactividad.")
        _limpiar_sesion(estado)
    print("  Sin sesión iniciada")


# ================================== Sesión ==================================
def _limpiar_sesion(estado: dict) -> None:
    estado.update({"token": None, "id": None, "nombre": None})


def _usuario_activo(r: redis.Redis, estado: dict, requerido: bool = True):
    """Valida la sesión (renueva su TTL) y devuelve el id del usuario."""
    token = estado["token"]
    id_usuario = sesiones.validar_sesion(r, token) if token else None

    if id_usuario is not None:
        return id_usuario

    if token:
        _limpiar_sesion(estado)
        if requerido:
            raise ValueError("Su sesión expiró por inactividad. Inicie sesión nuevamente.")
    elif requerido:
        raise ValueError("Debe iniciar sesión para usar esta función.")
    return None


def iniciar_o_cerrar_sesion(r: redis.Redis, estado: dict) -> None:
    if estado["token"]:
        sesiones.cerrar_sesion(r, estado["token"])
        _limpiar_sesion(estado)
        print("  Sesión cerrada.")
        return

    correo = leer_texto("  Correo: ")
    id_usuario = usuarios.buscar_por_correo(r, correo)
    if id_usuario is None:
        raise ValueError("No existe un usuario con ese correo.")

    usuario = usuarios.leer_usuario(r, id_usuario)
    estado["token"] = sesiones.iniciar_sesion(r, id_usuario)
    estado["id"] = id_usuario
    estado["nombre"] = usuario["nombre"]
    print(f"  Bienvenido(a), {usuario['nombre']}. "
          f"La sesión expira tras {sesiones.TTL_SESION // 60} minutos de inactividad.")


# ============================ Ejecución de menús ============================
def _mostrar_menu(titulo: str, opciones: list[str]) -> str:
    print(f"\n--- {titulo} ---")
    for i, texto in enumerate(opciones, start=1):
        print(f" {i}. {texto}")
    print(" 0. Volver")
    return input("Seleccione una opción: ").strip()


def _seguro(accion) -> None:
    """Ejecuta una acción mostrando los errores de forma amigable."""
    try:
        accion()
    except ValueError as error:
        print(f"  Error: {error}")
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        print("  No se pudo comunicar con Redis Cloud. Revise su conexión a internet.")


def _correr_menu(titulo: str, opciones: list[str], acciones: dict) -> None:
    while True:
        opcion = _mostrar_menu(titulo, opciones)
        if opcion == "0":
            return
        accion = acciones.get(opcion)
        if accion is None:
            print("  Opción no válida.")
            continue
        _seguro(accion)
        _pausar()


def _pedir_item(r: redis.Redis) -> dict | None:
    id_item = leer_entero("  ID del ítem: ", minimo=1)
    for tipo in catalogo.TIPOS_VALIDOS:
        item = catalogo.leer_item(r, tipo, id_item)
        if item:
            return item
    print("  No existe un ítem con ese ID.")
    return None


# ================================= CATÁLOGO =================================
def menu_catalogo(r: redis.Redis, estado: dict) -> None:
    def filtrar():
        generos = ", ".join(g for g, _ in consultas.listar_generos(r))
        print(f"  Géneros disponibles: {generos}")
        tipo = elegir_tipo(obligatorio=False)
        genero = leer_texto("  Género (Enter para todos): ", obligatorio=False)
        items, desde_cache = consultas.buscar(r, tipo, genero or None)
        origen = ("leído desde la CACHÉ de Redis" if desde_cache
                  else "calculado y guardado en caché (TTL de 5 min)")
        print(f"\n  Resultado {origen}:")
        mostrar_lista(items)

    def por_titulo():
        texto = leer_texto("  Texto a buscar en el título: ")
        mostrar_lista(consultas.buscar_por_titulo(r, texto))

    def por_generos():
        entrada = leer_texto("  Géneros separados por coma: ")
        generos = [g.strip() for g in entrada.split(",") if g.strip()]
        print("  1. Que cumpla ALGUNO (unión)   2. Que cumpla TODOS (intersección)")
        modo = "todos" if input("  Modo: ").strip() == "2" else "alguno"
        mostrar_lista(consultas.buscar_por_generos(r, generos, modo))

    def detalle():
        item = _pedir_item(r)
        if not item:
            return
        mostrar_detalle(r, item)
        id_usuario = _usuario_activo(r, estado, requerido=False)
        if id_usuario:
            usuarios.registrar_visualizacion(r, id_usuario, item["tipo"], item["id"])
            print("\n  Visita registrada en sus 'vistos recientemente' y en el ranking.")
        else:
            print("\n  Inicie sesión para que la visita cuente en el ranking.")

    _correr_menu("CATÁLOGO", [
        "Listar todo",
        "Filtrar por tipo y/o género (con caché)",
        "Buscar por título",
        "Buscar por varios géneros",
        "Ver detalle de un ítem",
    ], {
        "1": lambda: mostrar_lista(catalogo.listar_items(r)),
        "2": filtrar,
        "3": por_titulo,
        "4": por_generos,
        "5": detalle,
    })


# ============================= ADMINISTRAR CATÁLOGO =============================
def menu_admin_catalogo(r: redis.Redis) -> None:
    def crear():
        tipo = elegir_tipo()
        titulo = leer_texto("  Título: ")
        anio = leer_entero("  Año: ", 1000, 2100)
        genero = leer_texto("  Género: ")
        autor = leer_texto("  Autor/Director: ")
        descripcion = leer_texto("  Descripción (opcional): ", obligatorio=False)
        id_item = catalogo.crear_item(r, tipo, titulo, anio, genero, autor, descripcion)
        consultas.invalidar_cache(r)
        print(f"  Ítem creado con ID {id_item}.")

    def leer():
        item = _pedir_item(r)
        if item:
            mostrar_detalle(r, item)

    def actualizar():
        item = _pedir_item(r)
        if not item:
            return
        mostrar_detalle(r, item)
        print("\n  (Enter para conservar el valor actual)")
        campos = {
            "titulo": leer_texto("  Nuevo título: ", obligatorio=False),
            "anio": leer_entero("  Nuevo año: ", 1000, 2100, obligatorio=False),
            "genero": leer_texto("  Nuevo género: ", obligatorio=False),
            "autor_director": leer_texto("  Nuevo autor/director: ", obligatorio=False),
            "descripcion": leer_texto("  Nueva descripción: ", obligatorio=False),
        }
        if catalogo.actualizar_item(r, item["tipo"], item["id"], **campos):
            consultas.invalidar_cache(r)
            print("  Ítem actualizado.")
        else:
            print("  No se realizaron cambios.")

    def eliminar():
        item = _pedir_item(r)
        if not item:
            return
        mostrar_item(item)
        if confirmar("  ¿Eliminar este ítem?"):
            catalogo.eliminar_item(r, item["tipo"], item["id"])
            consultas.invalidar_cache(r)
            print("  Ítem eliminado.")

    _correr_menu("ADMINISTRAR CATÁLOGO (CRUD)", [
        "Crear ítem", "Consultar ítem", "Actualizar ítem", "Eliminar ítem",
    ], {"1": crear, "2": leer, "3": actualizar, "4": eliminar})


# ================================== USUARIOS ==================================
def menu_usuarios(r: redis.Redis, estado: dict) -> None:
    def crear():
        nombre = leer_texto("  Nombre: ")
        correo = leer_texto("  Correo: ")
        id_usuario = usuarios.crear_usuario(r, nombre, correo)
        print(f"  Usuario creado con ID {id_usuario}.")

    def listar():
        lista = usuarios.listar_usuarios(r)
        if not lista:
            print("  (no hay usuarios)")
        for u in lista:
            print(f"  [{u['id']}] {u['nombre']} - {u['correo']}")

    def actualizar():
        id_usuario = leer_entero("  ID del usuario: ", minimo=1)
        if not usuarios.leer_usuario(r, id_usuario):
            print("  No existe un usuario con ese ID.")
            return
        print("  (Enter para conservar el valor actual)")
        nombre = leer_texto("  Nuevo nombre: ", obligatorio=False)
        correo = leer_texto("  Nuevo correo: ", obligatorio=False)
        if usuarios.actualizar_usuario(r, id_usuario, nombre or None, correo or None):
            print("  Usuario actualizado.")
        else:
            print("  No se realizaron cambios.")

    def eliminar():
        id_usuario = leer_entero("  ID del usuario: ", minimo=1)
        usuario = usuarios.leer_usuario(r, id_usuario)
        if not usuario:
            print("  No existe un usuario con ese ID.")
            return
        if confirmar(f"  ¿Eliminar a {usuario['nombre']}?"):
            usuarios.eliminar_usuario(r, id_usuario)
            if estado["id"] == str(id_usuario):  # cierra su sesión activa
                sesiones.cerrar_sesion(r, estado["token"])
                _limpiar_sesion(estado)
            print("  Usuario eliminado.")

    _correr_menu("USUARIOS (CRUD)", [
        "Crear usuario", "Listar usuarios", "Actualizar usuario", "Eliminar usuario",
    ], {"1": crear, "2": listar, "3": actualizar, "4": eliminar})


# ================================ MI ESPACIO ================================
def menu_mi_espacio(r: redis.Redis, estado: dict) -> None:
    if not estado["token"]:
        print("\n  Debe iniciar sesión para usar esta sección.")
        _pausar()
        return

    def favoritos():
        mostrar_lista(usuarios.listar_favoritos(r, _usuario_activo(r, estado)))

    def agregar():
        id_usuario = _usuario_activo(r, estado)
        item = _pedir_item(r)
        if item:
            nuevo = usuarios.agregar_favorito(r, id_usuario, item["tipo"], item["id"])
            print("  Agregado a favoritos." if nuevo else "  Ya estaba en sus favoritos.")

    def quitar():
        id_usuario = _usuario_activo(r, estado)
        item = _pedir_item(r)
        if item:
            quitado = usuarios.quitar_favorito(r, id_usuario, item["tipo"], item["id"])
            print("  Quitado de favoritos." if quitado else "  No estaba en sus favoritos.")

    def recientes():
        mostrar_lista(usuarios.listar_recientes(r, _usuario_activo(r, estado)))

    def recomendaciones():
        items = consultas.recomendar(r, _usuario_activo(r, estado))
        if not items:
            print("  Aún no hay recomendaciones: agregue favoritos y espere a que "
                  "otros usuarios compartan gustos.")
        for item in items:
            mostrar_item(item, f"  (afinidad {item['afinidad']})")

    def estado_sesion():
        _usuario_activo(r, estado)
        ttl = sesiones.tiempo_restante(r, estado["token"])
        print(f"  Usuario: {estado['nombre']} | TTL renovado: {ttl} segundos")

    _correr_menu("MI ESPACIO", [
        "Ver mis favoritos", "Agregar a favoritos", "Quitar de favoritos",
        "Vistos recientemente", "Recomendaciones para mí", "Estado de mi sesión",
    ], {"1": favoritos, "2": agregar, "3": quitar, "4": recientes,
        "5": recomendaciones, "6": estado_sesion})


# ================================== RANKING ==================================
def menu_ranking(r: redis.Redis) -> None:
    def top(tipo):
        def accion():
            for i, item in enumerate(consultas.top_populares(r, 10, tipo), start=1):
                print(f"  {i:>2}. {item['titulo']} ({item['tipo']}) - {item['visitas']} visitas")
        return accion

    def posicion():
        item = _pedir_item(r)
        if item:
            datos = consultas.posicion_ranking(r, item["tipo"], item["id"])
            print(f"  {item['titulo']}: puesto {datos['posicion']} con {datos['visitas']} visitas.")

    def generos():
        for genero, cantidad in consultas.listar_generos(r):
            print(f"  - {genero}: {cantidad}")

    _correr_menu("RANKING Y ESTADÍSTICAS", [
        "Top 10 general", "Top 10 películas", "Top 10 libros",
        "Posición de un ítem", "Géneros y cantidad de ítems",
    ], {"1": top(None), "2": top("pelicula"), "3": top("libro"),
        "4": posicion, "5": generos})


# ============================== MENÚ PRINCIPAL ==============================
def ejecutar(r: redis.Redis) -> None:
    estado = {"token": None, "id": None, "nombre": None}

    while True:
        _encabezado(r, estado)
        etiqueta = "Cerrar sesión" if estado["token"] else "Iniciar sesión"
        print(" 1. Catálogo (explorar y buscar)")
        print(" 2. Administrar catálogo (CRUD)")
        print(" 3. Usuarios (CRUD)")
        print(f" 4. {etiqueta}")
        print(" 5. Mi espacio (favoritos, recientes, recomendaciones)")
        print(" 6. Ranking y estadísticas")
        print(" 0. Salir")
        opcion = input("Seleccione una opción: ").strip()

        if opcion == "0":
            print("\nHasta pronto.")
            return
        elif opcion == "1":
            menu_catalogo(r, estado)
        elif opcion == "2":
            menu_admin_catalogo(r)
        elif opcion == "3":
            menu_usuarios(r, estado)
        elif opcion == "4":
            _seguro(lambda: iniciar_o_cerrar_sesion(r, estado))
            _pausar()
        elif opcion == "5":
            menu_mi_espacio(r, estado)
        elif opcion == "6":
            menu_ranking(r)
        else:
            print("  Opción no válida.")