"""
repository.py
-------------
Consultas a la base de datos PostgreSQL de ExperTIA.
"""

from datetime import datetime, timezone

from app.database import obtener_conexion, obtener_cursor


# ============================================================
# KEYWORDS
# ============================================================

def get_keyword_matches():
    """
    Obtiene las keywords relacionadas con cada conocimiento
    junto con su peso.
    """

    sql = """
        SELECT
            ck.conocimiento_id,
            ck.keyword_id,
            k.palabra,
            COALESCE(ck.peso, 1.00)::float AS peso

        FROM conocimiento_keywords ck

        INNER JOIN keywords k
            ON k.id = ck.keyword_id

        WHERE COALESCE(k.activo, TRUE) = TRUE
    """

    with obtener_conexion() as conn:

        with obtener_cursor(conn) as cursor:

            cursor.execute(sql)

            return cursor.fetchall()


# ============================================================
# INTENCIONES
# ============================================================

def get_intention_variants():
    """
    Obtiene las variantes de intención activas.

    Ejemplo:

        Intención:
            Solicitar

        Variantes:
            necesito
            quiero
            solicitar
            requiero
            tramitar
    """

    sql = """
        SELECT
            iv.id,
            iv.intencion_id,
            i.nombre AS intencion,
            iv.frase,
            COALESCE(iv.peso, 1.00)::float AS peso

        FROM intencion_variantes iv

        INNER JOIN intenciones i
            ON i.id = iv.intencion_id

        WHERE COALESCE(i.activo, TRUE) = TRUE
    """

    with obtener_conexion() as conn:

        with obtener_cursor(conn) as cursor:

            cursor.execute(sql)

            return cursor.fetchall()


# ============================================================
# CONOCIMIENTOS
# ============================================================

def get_knowledge_candidates():
    """
    Obtiene todos los conocimientos activos junto con:

    - Área
    - Proceso
    - Preguntas alternativas
    - Keywords
    - Recursos
    """

    sql = """
        SELECT

            c.id,
            c.titulo,
            c.descripcion,
            c.respuesta,
            c.responsable,
            c.estado,

            c.area_id,
            a.nombre AS area,

            c.proceso_id,
            p.nombre AS proceso,

            /*
             * Preguntas alternativas
             */

            COALESCE(
                (
                    SELECT string_agg(
                        pa.pregunta,
                        ' || '
                    )

                    FROM preguntas_alternativas pa

                    WHERE pa.conocimiento_id = c.id
                ),
                ''
            ) AS preguntas_alternativas,

            /*
             * Keywords
             */

            COALESCE(
                (
                    SELECT string_agg(

                        k.palabra
                        || '::'
                        || COALESCE(
                            ck.peso::text,
                            '1.00'
                        ),

                        ' || '
                    )

                    FROM conocimiento_keywords ck

                    INNER JOIN keywords k
                        ON k.id = ck.keyword_id

                    WHERE ck.conocimiento_id = c.id

                    AND COALESCE(
                        k.activo,
                        TRUE
                    ) = TRUE
                ),
                ''
            ) AS keywords,

            /*
             * Recursos
             */

            COALESCE(
                (
                    SELECT string_agg(

                        r.nombre
                        || '::'
                        || r.tipo
                        || '::'
                        || COALESCE(
                            r.url,
                            ''
                        )
                        || '::'
                        || COALESCE(
                            r.descripcion,
                            ''
                        ),

                        ' || '
                    )

                    FROM recursos r

                    WHERE r.conocimiento_id = c.id

                    AND COALESCE(
                        r.activo,
                        TRUE
                    ) = TRUE
                ),
                ''
            ) AS recursos

        FROM conocimientos c

        LEFT JOIN areas a
            ON a.id = c.area_id

        LEFT JOIN procesos p
            ON p.id = c.proceso_id

        WHERE UPPER(
            COALESCE(
                c.estado,
                'ACTIVO'
            )
        ) = 'ACTIVO'

        AND (
            a.id IS NULL
            OR COALESCE(
                a.activo,
                TRUE
            ) = TRUE
        )

        AND (
            p.id IS NULL
            OR COALESCE(
                p.activo,
                TRUE
            ) = TRUE
        )
    """

    with obtener_conexion() as conn:

        with obtener_cursor(conn) as cursor:

            cursor.execute(sql)

            return cursor.fetchall()


# ============================================================
# HISTORIAL
# ============================================================

def save_query_history(
    usuario,
    pregunta,
    conocimiento_id,
    confianza
):
    """
    Guarda la consulta realizada en historial_consultas.

    El usuario puede ser NULL porque la API actualmente
    solo necesita recibir la pregunta.
    """

    sql = """
        INSERT INTO historial_consultas
        (
            usuario,
            pregunta,
            conocimiento_id,
            confianza,
            fecha
        )

        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s
        )
    """

    with obtener_conexion() as conn:

        with obtener_cursor(conn) as cursor:

            cursor.execute(
                sql,
                (
                    usuario,
                    pregunta,
                    conocimiento_id,
                    round(
                        float(confianza),
                        2
                    ),
                    datetime.now(
                        timezone.utc
                    )
                )
            )

        conn.commit()


# ============================================================
# OBTENER CONOCIMIENTOS
# ============================================================

def obtener_conocimientos():
    """
    Obtiene únicamente los conocimientos activos.

    Esta función mantiene compatibilidad con
    knowledge_retriever.py.
    """

    conocimientos = get_knowledge_candidates()

    resultado = []

    for conocimiento in conocimientos:

        resultado.append({

            "id":
                conocimiento["id"],

            "titulo":
                conocimiento["titulo"],

            "descripcion":
                conocimiento["descripcion"],

            "respuesta":
                conocimiento["respuesta"],

            "responsable":
                conocimiento["responsable"],

            "estado":
                conocimiento["estado"],

            "area":
                conocimiento["area"],

            "proceso":
                conocimiento["proceso"]

        })

    return resultado


# ============================================================
# PREGUNTAS ALTERNATIVAS
# ============================================================

def obtener_preguntas_alternativas():
    """
    Obtiene las preguntas alternativas asociadas
    a conocimientos activos.
    """

    sql = """
        SELECT
            pa.id,
            pa.conocimiento_id,
            pa.pregunta

        FROM preguntas_alternativas pa

        INNER JOIN conocimientos c
            ON c.id = pa.conocimiento_id

        WHERE UPPER(
            COALESCE(
                c.estado,
                'ACTIVO'
            )
        ) = 'ACTIVO'
    """

    with obtener_conexion() as conn:

        with obtener_cursor(conn) as cursor:

            cursor.execute(sql)

            return cursor.fetchall()


# ============================================================
# RECURSOS POR CONOCIMIENTO
# ============================================================

def obtener_recursos_por_conocimiento(
    conocimiento_id
):
    """
    Obtiene los recursos activos asociados
    a un conocimiento.

    Ejemplo:

    {
        "id": 1,
        "nombre": "Solicitud Pago Parcial de Cesantías",
        "tipo": "XLSX",
        "url": "https://...",
        "descripcion": "Formato oficial..."
    }
    """

    sql = """
        SELECT
            r.id,
            r.nombre,
            r.tipo,
            r.url,
            r.descripcion

        FROM recursos r

        WHERE r.conocimiento_id = %s

        AND COALESCE(
            r.activo,
            TRUE
        ) = TRUE

        ORDER BY r.id
    """

    with obtener_conexion() as conn:

        with obtener_cursor(conn) as cursor:

            cursor.execute(
                sql,
                (conocimiento_id,)
            )

            filas = cursor.fetchall()

            recursos = []

            for fila in filas:

                recursos.append({

                    "id":
                        fila["id"],

                    "nombre":
                        fila["nombre"],

                    "tipo":
                        fila["tipo"],

                    "url":
                        fila["url"],

                    "descripcion":
                        fila["descripcion"]

                })

            return recursos