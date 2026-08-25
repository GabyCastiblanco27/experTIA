from psycopg2.extras import RealDictCursor

from app.database import obtener_conexion
from app.normalizer import (
    normalizar_texto,
    obtener_palabras
)


def obtener_variantes_intenciones():

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()

        cursor = conexion.cursor(
            cursor_factory=RealDictCursor
        )

        consulta = """
            SELECT
                i.id AS intencion_id,
                i.nombre AS intencion,
                i.descripcion,
                iv.frase AS variante,
                iv.peso

            FROM intencion_variantes iv

            INNER JOIN intenciones i
                ON iv.intencion_id = i.id

            WHERE i.activo = TRUE

            ORDER BY
                i.id,
                iv.peso DESC
        """

        cursor.execute(consulta)

        return cursor.fetchall()

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


def calcular_coincidencia_palabras(
    pregunta,
    variante
):

    palabras_pregunta = set(
        obtener_palabras(pregunta)
    )

    palabras_variante = set(
        obtener_palabras(variante)
    )

    if not palabras_variante:
        return 0.0

    coincidencias = (
        palabras_pregunta.intersection(
            palabras_variante
        )
    )

    return (
        len(coincidencias)
        /
        len(palabras_variante)
    )


def detectar_intenciones(
    pregunta
):

    pregunta_normalizada = (
        normalizar_texto(
            pregunta
        )
    )

    variantes = (
        obtener_variantes_intenciones()
    )

    intenciones = {}

    for variante in variantes:

        variante_normalizada = (
            normalizar_texto(
                variante["variante"]
            )
        )

        # ===========================
        # Coincidencia exacta
        # ===========================

        if variante_normalizada in pregunta_normalizada:

            score = float(
                variante["peso"]
            )

        else:

            coincidencia = (
                calcular_coincidencia_palabras(
                    pregunta,
                    variante["variante"]
                )
            )

            if coincidencia < 0.70:
                continue

            score = (
                coincidencia
                *
                float(
                    variante["peso"]
                )
            )

        intencion_id = (
            variante["intencion_id"]
        )

        if intencion_id not in intenciones:

            intenciones[intencion_id] = {

                "intencion_id":
                    intencion_id,

                "intencion":
                    variante["intencion"],

                "descripcion":
                    variante.get(
                        "descripcion"
                    ),

                "mejor_variante":
                    variante["variante"],

                "mejor_score":
                    score,

                "coincidencias":
                    []
            }

        intenciones[intencion_id][
            "coincidencias"
        ].append({

            "variante":
                variante["variante"],

            "peso":
                float(
                    variante["peso"]
                ),

            "score":
                round(
                    score,
                    4
                )
        })

        if (
            score
            >
            intenciones[
                intencion_id
            ]["mejor_score"]
        ):

            intenciones[
                intencion_id
            ]["mejor_score"] = score

            intenciones[
                intencion_id
            ]["mejor_variante"] = (
                variante["variante"]
            )

    resultados = list(
        intenciones.values()
    )

    resultados.sort(
        key=lambda x:
            x["mejor_score"],
        reverse=True
    )

    return resultados