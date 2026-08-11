from app.database import obtener_conexion


def obtener_conocimientos():
    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        consulta = """
            SELECT
                c.id,
                c.area_id,
                a.nombre AS area,
                c.proceso,
                c.sub_proceso,
                c.tema,
                c.pregunta_principal,
                c.descripcion_proceso,
                c.paso_a_paso,
                c.responsable,
                c.entradas,
                c.salidas,
                c.herramientas,
                c.link_politica,
                c.estado
            FROM conocimientos c
            INNER JOIN areas a
                ON c.area_id = a.id
            WHERE c.estado = 'ACTIVO'
            ORDER BY c.id;
        """

        cursor.execute(consulta)

        conocimientos = cursor.fetchall()

        for conocimiento in conocimientos:

            conocimiento["preguntas_alternativas"] = (
                obtener_preguntas_alternativas(
                    conocimiento["id"]
                )
            )

            conocimiento["keywords"] = (
                obtener_keywords(
                    conocimiento["id"]
                )
            )

            conocimiento["intenciones"] = (
                obtener_intenciones(
                    conocimiento["id"]
                )
            )

            conocimiento["recursos"] = (
                obtener_recursos(
                    conocimiento["id"]
                )
            )

        return conocimientos

    finally:
        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


def obtener_preguntas_alternativas(conocimiento_id):
    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        consulta = """
            SELECT
                id,
                pregunta
            FROM preguntas_alternativas
            WHERE conocimiento_id = %s
              AND activo = TRUE
            ORDER BY id;
        """

        cursor.execute(
            consulta,
            (conocimiento_id,)
        )

        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


def obtener_keywords(conocimiento_id):
    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        consulta = """
            SELECT
                k.id,
                k.palabra,
                k.tipo,
                ck.peso
            FROM conocimiento_keywords ck
            INNER JOIN keywords k
                ON ck.keyword_id = k.id
            WHERE ck.conocimiento_id = %s
              AND k.activo = TRUE
            ORDER BY ck.peso DESC, k.id;
        """

        cursor.execute(
            consulta,
            (conocimiento_id,)
        )

        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


def obtener_intenciones(conocimiento_id):
    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        consulta = """
            SELECT
                i.id,
                i.nombre,
                i.descripcion,
                ci.peso
            FROM conocimiento_intenciones ci
            INNER JOIN intenciones i
                ON ci.intencion_id = i.id
            WHERE ci.conocimiento_id = %s
              AND i.activo = TRUE
            ORDER BY ci.peso DESC, i.id;
        """

        cursor.execute(
            consulta,
            (conocimiento_id,)
        )

        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


def obtener_recursos(conocimiento_id):
    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        consulta = """
            SELECT
                id,
                tipo,
                nombre,
                url,
                descripcion
            FROM recursos
            WHERE conocimiento_id = %s
              AND activo = TRUE
            ORDER BY id;
        """

        cursor.execute(
            consulta,
            (conocimiento_id,)
        )

        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()

        if conexion:
            conexion.close()