#Modulo de conexion a redis


import os

import redis
from dotenv import load_dotenv

load_dotenv()

def obtener_cliente() -> redis.Redis:
    #Crea y valida la conexion con la base de datos de la nube
    cliente = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        username=os.getenv("REDIS_USER", "default"),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True, #devuelve el texto (str) en lugar de bytes
    )
    cliente.ping() #lanza una excepcion si no logra conectar
    return cliente