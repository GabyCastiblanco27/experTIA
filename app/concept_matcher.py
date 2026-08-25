from psycopg2.extras import RealDictCursor

from app.database import obtener_conexion
from app.normalizer import (
    normalizar_texto
)


def detectar_conceptos(texto):
    """
    Compatibilidad con la arquitectura actual.

    En la nueva versión de ExperTIA los conceptos
    se obtienen desde la tabla de keywords.
    """

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()

        cursor = conexion.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute("""
            SELECT
                ck.conocimiento_id,
                k.id AS keyword_id,
                k.palabra,
                ck.peso
            FROM conocimiento_keywords ck
            INNER JOIN keywords k
                ON ck.keyword_id = k.id
        """)

        registros = cursor.fetchall()

        texto_normalizado = normalizar_texto(
            texto
        )

        resultados = []

        for registro in registros:

            palabra = normalizar_texto(
                registro["palabra"]
            )

            if palabra in texto_normalizado:

                resultados.append({

                    "concepto_id":
                        registro["keyword_id"],

                    "concepto":
                        registro["palabra"],

                    "mejor_variante":
                        registro["palabra"],

                    "mejor_score":
                        float(
                            registro["peso"]
                        ),

                    "conocimiento_id":
                        registro[
                            "conocimiento_id"
                        ],

                    "coincidencias": [
                        {
                            "variante":
                                registro[
                                    "palabra"
                                ],

                            "peso":
                                float(
                                    registro[
                                        "peso"
                                    ]
                                ),

                            "score":
                                float(
                                    registro[
                                        "peso"
                                    ]
                                )
                        }
                    ]
                })

        resultados.sort(
            key=lambda x:
                x["mejor_score"],
            reverse=True
        )

        return resultados

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()