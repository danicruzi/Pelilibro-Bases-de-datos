"""Punto de entrada de la aplicación PeliLibros (Redis Cloud)."""
from src.conexion import obtener_cliente
from src import menu


def main():
    try:
        r = obtener_cliente()
    except Exception as error:
        print(f"No se pudo conectar a Redis Cloud: {error}")
        return

    print("Conexión con Redis Cloud establecida.")
    try:
        menu.ejecutar(r)
    except KeyboardInterrupt:
        print("\nAplicación finalizada.")


if __name__ == "__main__":
    main()