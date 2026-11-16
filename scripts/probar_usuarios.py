#Verifica usuarios, favoritos, recientes y sesiones con TTL deslizante.
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.conexion import obtener_cliente
from src import usuarios, sesiones

r = obtener_cliente()

print("Usuarios:", [u["nombre"] for u in usuarios.listar_usuarios(r)])

print("\nFavoritos del usuario 1:")
for item in usuarios.listar_favoritos(r, 1):
    print(" -", item["titulo"])

print("\nRecientes del usuario 1 (más reciente primero):")
for item in usuarios.listar_recientes(r, 1):
    print(" -", item["titulo"])

token = sesiones.iniciar_sesion(r, 1)
print(f"\nSesión creada: {token} | TTL: {sesiones.tiempo_restante(r, token)} s")
time.sleep(3)
print("TTL tras 3 s:", sesiones.tiempo_restante(r, token))
print("Validar sesión -> usuario:", sesiones.validar_sesion(r, token))
print("TTL tras validar (renovado):", sesiones.tiempo_restante(r, token))

sesiones.cerrar_sesion(r, token)
print("Sesión tras cerrarla:", sesiones.validar_sesion(r, token))