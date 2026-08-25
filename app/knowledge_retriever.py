from app.database import (
    obtener_conexion,
    obtener_cursor
)

from app.repository import obtener_recursos


def buscar_conocimientos(texto):

    return [
        {
            "titulo": "Prueba",
            "area": "Prueba",
            "proceso": "Prueba",
            "descripcion": "Prueba",
            "respuesta": "La API funciona correctamente",
            "responsable": "Prueba",
            "recursos": []
        }
    ]