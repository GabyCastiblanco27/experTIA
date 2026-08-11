from app.database import obtener_conexion
from app.normalizer import normalizar_texto, obtener_palabras


def obtener_keywords():
    """
    Obtiene las keywords activas asociadas
    a cada conocimiento.
    """

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        consulta = """
            SELECT
                ck.conocimiento_id,
                k.id AS keyword_id,
                k.palabra AS keyword,
                ck.peso
            FROM conocimiento_keywords ck

            INNER JOIN keywords k
                ON ck.keyword_id = k.id

            WHERE k.tipo = 'KEYWORD'
              AND k.activo = TRUE

            ORDER BY
                ck.conocimiento_id,
                ck.peso DESC;
        """

        cursor.execute(consulta)

        return cursor.fetchall()

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


def calcular_coincidencia_keyword(
    pregunta,
    keyword
):
    """
    Calcula qué porcentaje de las palabras
    de la keyword aparecen en la pregunta.
    """

    palabras_pregunta = set(
        obtener_palabras(pregunta)
    )

    palabras_keyword = set(
        obtener_palabras(keyword)
    )

    if not palabras_keyword:
        return 0.0

    coincidencias = (
        palabras_pregunta.intersection(
            palabras_keyword
        )
    )

    return (
        len(coincidencias)
        /
        len(palabras_keyword)
    )


def detectar_keywords(pregunta):
    """
    Detecta keywords relacionadas con la pregunta.
    """

    pregunta_normalizada = normalizar_texto(
        pregunta
    )

    keywords = obtener_keywords()

    resultados = {}

    for keyword in keywords:

        keyword_normalizada = normalizar_texto(
            keyword["keyword"]
        )

        # =========================================
        # NIVEL 1
        # Coincidencia exacta de frase
        # =========================================

        if keyword_normalizada in pregunta_normalizada:

            coincidencia = 1.0

        else:

            # =====================================
            # NIVEL 2
            # Coincidencia por palabras
            # =====================================

            coincidencia = (
                calcular_coincidencia_keyword(
                    pregunta,
                    keyword["keyword"]
                )
            )

            if coincidencia < 0.70:
                continue

        score = (
            coincidencia
            *
            float(keyword["peso"])
        )

        conocimiento_id = (
            keyword["conocimiento_id"]
        )

        # =========================================
        # Crear resultado del conocimiento
        # =========================================

        if conocimiento_id not in resultados:

            resultados[conocimiento_id] = {

                "conocimiento_id":
                    conocimiento_id,

                "score_keywords":
                    0.0,

                "keywords_detectadas":
                    []
            }

        # =========================================
        # Guardar evidencia
        # =========================================

        resultados[
            conocimiento_id
        ][
            "keywords_detectadas"
        ].append({

            "keyword_id":
                keyword["keyword_id"],

            "keyword":
                keyword["keyword"],

            "peso":
                float(keyword["peso"]),

            "score":
                round(score, 4)
        })

        # =========================================
        # Acumular score
        # =========================================

        resultados[
            conocimiento_id
        ][
            "score_keywords"
        ] += score

    resultados = list(
        resultados.values()
    )

    resultados.sort(
        key=lambda x:
            x["score_keywords"],
        reverse=True
    )

    return resultados