from app.database import (
    obtener_conexion,
    obtener_cursor
)

from app.repository import obtener_recursos


def buscar_conocimientos(texto):

    conexion = obtener_conexion()
    cursor = obtener_cursor(conexion)

    try:

        patron = f"%{texto.lower()}%"

        sql = """
        SELECT DISTINCT

            c.id,
            c.titulo,
            c.descripcion,
            c.respuesta,
            c.responsable,
            c.estado,

            a.nombre AS area,
            p.nombre AS proceso

        FROM conocimientos c

        LEFT JOIN areas a
            ON a.id = c.area_id

        LEFT JOIN procesos p
            ON p.id = c.proceso_id

        LEFT JOIN preguntas_alternativas pa
            ON pa.conocimiento_id = c.id

        LEFT JOIN conocimiento_keywords ck
            ON ck.conocimiento_id = c.id

        LEFT JOIN keywords k
            ON k.id = ck.keyword_id

        WHERE

            LOWER(c.titulo) LIKE %s
            OR LOWER(c.descripcion) LIKE %s
            OR LOWER(pa.pregunta) LIKE %s
            OR LOWER(k.palabra) LIKE %s
        """

        cursor.execute(
            sql,
            (
                patron,
                patron,
                patron,
                patron
            )
        )

        resultados = cursor.fetchall()

        for resultado in resultados:

            resultado["recursos"] = (
                obtener_recursos(
                    resultado["id"]
                )
            )

        return resultados

    finally:
        cursor.close()
        conexion.close()