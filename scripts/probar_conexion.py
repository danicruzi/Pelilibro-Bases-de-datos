"""Script de prueba: verifica conexión, escritura, lectura y expiración (TTL)."""
import os
import sys

# Permite importar el paquete 'src' desde la carpeta raíz del proyecto
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.conexion import obtener_cliente

r = obtener_cliente()
print("Conexión exitosa:", r.ping())

r.set("prueba:saludo", "Hola Redis Cloud", ex=30)  # expira en 30 segundos
print("Valor guardado:", r.get("prueba:saludo"))
print("TTL restante:", r.ttl("prueba:saludo"), "segundos")