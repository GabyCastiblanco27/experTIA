from app.database import obtener_conexion
from app.normalizer import normalizar_texto, obtener_palabras


def obtener_variantes_intenciones():
    """
    Obtiene de MySQL todas las variantes de intención activas.
    """

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        consulta = """
            SELECT
                i.id AS intencion_id,
                i.nombre AS intencion,
                iv.variante,
                iv.peso
            FROM intencion_variantes iv
            INNER JOIN intenciones i
                ON iv.intencion_id = i.id
            WHERE iv.activo = TRUE
              AND i.activo = TRUE
            ORDER BY i.id, iv.peso DESC;
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


def detectar_intenciones(pregunta):
    """
    Detecta las intenciones posibles de una pregunta.
    """

    pregunta_normalizada = normalizar_texto(
        pregunta
    )

    variantes = obtener_variantes_intenciones()

    intenciones = {}

    for variante in variantes:

        variante_normalizada = normalizar_texto(
            variante["variante"]
        )

        # =========================================
        # NIVEL 1: coincidencia exacta de frase
        # =========================================

        if variante_normalizada in pregunta_normalizada:

            score = float(variante["peso"])

        else:

            # =====================================
            # NIVEL 2: coincidencia por palabras
            # =====================================

            coincidencia = calcular_coincidencia_palabras(
                pregunta,
                variante["variante"]
            )

            if coincidencia < 0.70:
                continue

            score = (
                coincidencia *
                float(variante["peso"])
            )

        intencion_id = variante["intencion_id"]

        # =========================================
        # AGRUPAR POR INTENCIÓN
        # =========================================

        if intencion_id not in intenciones:

            intenciones[intencion_id] = {
                "intencion_id": intencion_id,
                "intencion": variante["intencion"],
                "mejor_variante": variante["variante"],
                "mejor_score": score,
                "coincidencias": []
            }

        intenciones[intencion_id]["coincidencias"].append({
            "variante": variante["variante"],
            "peso": float(variante["peso"]),
            "score": round(score, 4)
        })

        # Guardar la mejor coincidencia
        if score > intenciones[intencion_id]["mejor_score"]:

            intenciones[intencion_id]["mejor_score"] = score

            intenciones[intencion_id]["mejor_variante"] = (
                variante["variante"]
            )

    resultados = list(
        intenciones.values()
    )

    resultados.sort(
        key=lambda x: x["mejor_score"],
        reverse=True
    )

    return resultados