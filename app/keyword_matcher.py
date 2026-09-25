"""
keyword_matcher.py

Detecta keywords presentes en la pregunta
y calcula qué conocimientos están relacionados
con ellas.

Las keywords compuestas tienen mayor peso que
las keywords genéricas de una sola palabra.
"""

from app.normalizer import normalize, tokenize
from app.repository import get_keyword_matches


# ============================================================
# DETECTAR KEYWORDS
# ============================================================

def detectar_keywords(pregunta):
    """
    Detecta keywords relacionadas con la pregunta.

    Se consideran:

    - Coincidencias exactas de una palabra.
    - Coincidencias completas de varias palabras.

    Las keywords de una sola palabra reciben un peso reducido
    porque pueden ser términos genéricos.

    Las keywords compuestas solo se consideran cuando todos
    sus términos están presentes en la pregunta.
    """

    texto_normalizado = normalize(pregunta)

    if not texto_normalizado:
        return []

    tokens_pregunta = set(
        tokenize(pregunta)
    )

    keywords_bd = get_keyword_matches()

    encontradas = []

    for keyword in keywords_bd:

        palabra_original = keyword["palabra"]

        palabra_bd = normalize(
            palabra_original
        )

        if not palabra_bd:
            continue

        tokens_keyword = set(
            tokenize(palabra_bd)
        )

        if not tokens_keyword:
            continue

        peso_base = float(
            keyword["peso"]
        )

        cantidad_tokens = len(
            tokens_keyword
        )

        # ====================================================
        # KEYWORD DE UNA SOLA PALABRA
        # ====================================================

        if cantidad_tokens == 1:

            token_keyword = next(
                iter(tokens_keyword)
            )

            if token_keyword in tokens_pregunta:

                # Las keywords de una sola palabra son
                # consideradas coincidencias genéricas.
                #
                # Ejemplos:
                # "reporte"
                # "proveedor"
                # "factura"
                # "retiro"
                #
                # No deben tener suficiente peso para
                # seleccionar por sí solas un conocimiento.

                peso_ajustado = (
                    peso_base * 0.40
                )

                encontradas.append({

                    "conocimiento_id":
                        keyword["conocimiento_id"],

                    "keyword_id":
                        keyword["keyword_id"],

                    "palabra":
                        palabra_original,

                    "peso":
                        peso_ajustado,

                    "es_compuesta":
                        False,

                    "cantidad_tokens":
                        1

                })

            # IMPORTANTE:
            # No procesamos esta keyword como compuesta.
            continue

        # ====================================================
        # KEYWORD DE VARIAS PALABRAS
        # ====================================================

        coincidencias = (
            tokens_keyword
            &
            tokens_pregunta
        )

        porcentaje = (
            len(coincidencias)
            /
            len(tokens_keyword)
        )

        # ====================================================
        # COINCIDENCIA COMPLETA
        # ====================================================

        if porcentaje >= 1.0:

            # Las keywords compuestas tienen mayor importancia
            # porque representan una relación más específica.

            multiplicador_especificidad = (
                1.0
                +
                0.5 * (cantidad_tokens - 1)
            )

            peso_ajustado = (
                peso_base
                *
                multiplicador_especificidad
            )

            encontradas.append({

                "conocimiento_id":
                    keyword["conocimiento_id"],

                "keyword_id":
                    keyword["keyword_id"],

                "palabra":
                    palabra_original,

                "peso":
                    peso_ajustado,

                "es_compuesta":
                    True,

                "cantidad_tokens":
                    cantidad_tokens

            })

        # IMPORTANTE:
        # No existe coincidencia parcial para keywords
        # compuestas.
        #
        # Ejemplo:
        #
        # Keyword:
        # "Retiro de cesantías"
        #
        # Pregunta:
        # "como retiro mi clima"
        #
        # Después de normalizar:
        #
        # Keyword  -> "retiro cesantias"
        # Pregunta  -> "retiro clima"
        #
        # Solo coincide "retiro", por lo tanto la keyword
        # compuesta NO obtiene puntos.


    return encontradas


# ============================================================
# CALCULAR PUNTAJES
# ============================================================

def calcular_puntajes_keywords(pregunta):
    """
    Calcula el puntaje de keywords por conocimiento.

    Las coincidencias específicas tienen mayor influencia
    que las coincidencias genéricas.
    """

    keywords = detectar_keywords(
        pregunta
    )

    puntajes = {}

    for keyword in keywords:

        conocimiento_id = (
            keyword["conocimiento_id"]
        )

        peso = float(
            keyword["peso"]
        )

        if conocimiento_id not in puntajes:

            puntajes[
                conocimiento_id
            ] = 0.0

        puntajes[
            conocimiento_id
        ] += peso

    return puntajes