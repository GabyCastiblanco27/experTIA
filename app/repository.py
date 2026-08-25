from app.database import (
    obtener_conexion,
    obtener_cursor
)


def obtener_recursos(conocimiento_id):

    conexion = obtener_conexion()
    cursor = obtener_cursor(conexion)

    try:

        cursor.execute("""
            SELECT
                id,
                nombre,
                tipo,
                url,
                descripcion
            FROM recursos
            WHERE conocimiento_id = %s
        """, (conocimiento_id,))

        return cursor.fetchall()

    finally:
        cursor.close()
        conexion.close()