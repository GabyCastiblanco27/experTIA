from app.database import obtener_conexion
from app.normalizer import normalizar_texto, obtener_palabras


def obtener_variantes_conceptos():
    """
    Obtiene de MySQL todos los conceptos y sus variantes.
    """

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        consulta = """
          SELECT
             c.id AS concepto_id,
            c.nombre AS concepto,
            cv.variante,
            cv.peso
        FROM concepto_variantes cv
        INNER JOIN conceptos c
            ON cv.concepto_id = c.id
        WHERE cv.activo = TRUE
            AND c.activo = TRUE
        ORDER BY c.id, cv.peso DESC;
"""

        cursor.execute(consulta)

        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


def calcular_coincidencia_palabras(pregunta, variante):
    """
    Calcula qué porcentaje de las palabras importantes
    de una variante aparecen en la pregunta.
    """

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

    return len(coincidencias) / len(palabras_variante)


def detectar_conceptos(pregunta):

    pregunta_normalizada = normalizar_texto(
        pregunta
    )

    variantes = obtener_variantes_conceptos()

    conceptos = {}

    for variante in variantes:

        variante_normalizada = normalizar_texto(
            variante["variante"]
        )

        # ----------------------------------------
        # NIVEL 1: coincidencia exacta de frase
        # ----------------------------------------

        if variante_normalizada in pregunta_normalizada:

            score = float(variante["peso"])

        else:

            # ------------------------------------
            # NIVEL 2: coincidencia por palabras
            # ------------------------------------

            coincidencia = calcular_coincidencia_palabras(
                pregunta,
                variante["variante"]
            )

            # Solo aceptamos coincidencias
            # suficientemente fuertes.
            if coincidencia < 0.70:
                continue

            score = (
                coincidencia *
                float(variante["peso"])
            )

        concepto_id = variante["concepto_id"]

        # ----------------------------------------
        # Agrupar todas las coincidencias
        # del mismo concepto
        # ----------------------------------------

        if concepto_id not in conceptos:

            conceptos[concepto_id] = {
                "concepto_id": concepto_id,
                "concepto": variante["concepto"],
                "mejor_variante": variante["variante"],
                "mejor_score": score,
                "coincidencias": []
            }

        conceptos[concepto_id]["coincidencias"].append({
            "variante": variante["variante"],
            "peso": float(variante["peso"]),
            "score": round(score, 4)
        })

        # Guardar solamente la mejor coincidencia
        if score > conceptos[concepto_id]["mejor_score"]:

            conceptos[concepto_id]["mejor_score"] = score

            conceptos[concepto_id]["mejor_variante"] = (
                variante["variante"]
            )

    resultados = list(
        conceptos.values()
    )

    # Ordenar del concepto más relevante
    # al menos relevante.
    resultados.sort(
        key=lambda x: x["mejor_score"],
        reverse=True
    )

    return resultados