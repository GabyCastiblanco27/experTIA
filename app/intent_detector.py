"""
intent_detector.py

Detecta la intención de la pregunta
utilizando las tablas:

- intenciones
- intencion_variantes
"""

from difflib import SequenceMatcher

from app.normalizer import normalize, tokenize

from app.repository import get_intention_variants


# ============================================================
# SIMILITUD
# ============================================================

def calcular_similitud(
    texto1,
    texto2
):
    """
    Calcula la similitud entre dos textos utilizando:

    1. Similitud por tokens.
    2. Similitud por secuencia.

    Devuelve el mayor de los dos valores.
    """

    if not texto1 or not texto2:
        return 0.0

    tokens1 = set(
        tokenize(texto1)
    )

    tokens2 = set(
        tokenize(texto2)
    )

    # --------------------------------------------------------
    # Similitud por tokens
    # --------------------------------------------------------

    interseccion = len(
        tokens1 & tokens2
    )

    union = len(
        tokens1 | tokens2
    )

    if union == 0:

        similitud_tokens = 0.0

    else:

        similitud_tokens = (
            interseccion / union
        )

    # --------------------------------------------------------
    # Similitud de secuencia
    # --------------------------------------------------------

    similitud_secuencia = (
        SequenceMatcher(
            None,
            texto1,
            texto2
        ).ratio()
    )

    return max(
        similitud_tokens,
        similitud_secuencia
    )


# ============================================================
# DETECCIÓN DE INTENCIÓN
# ============================================================

def detectar_intencion(
    pregunta
):
    """
    Detecta la intención más probable
    de la pregunta del usuario.
    """

    if not pregunta:
        return None

    pregunta_normalizada = normalize(
        pregunta
    )

    if not pregunta_normalizada:
        return None

    tokens_pregunta = set(
        tokenize(pregunta)
    )

    variantes = get_intention_variants()

    if not variantes:
        return None

    mejor_resultado = None

    for variante in variantes:

        frase_original = variante[
            "frase"
        ]

        frase = normalize(
            frase_original
        )

        if not frase:
            continue

        tokens_frase = set(
            tokenize(frase)
        )

        if not tokens_frase:
            continue

        # ----------------------------------------------------
        # Coincidencia exacta
        # ----------------------------------------------------

        coincidencia_exacta = (
            tokens_frase.issubset(
                tokens_pregunta
            )
        )

        if coincidencia_exacta:

            puntaje = 1.0

        else:

            puntaje = calcular_similitud(
                pregunta_normalizada,
                frase
            )

        # ----------------------------------------------------
        # Aplicar peso de la variante
        # ----------------------------------------------------

        peso = float(
            variante.get(
                "peso",
                1.0
            ) or 1.0
        )

        # El peso influye ligeramente
        # sin permitir que una variante
        # de peso alto destruya la similitud.
        puntaje_ponderado = min(
            puntaje * peso,
            1.0
        )

        resultado = {

            "intencion_id":
                variante["intencion_id"],

            "intencion":
                variante["intencion"],

            "frase":
                frase_original,

            "score":
                puntaje_ponderado
        }

        # ----------------------------------------------------
        # Seleccionar mejor intención
        # ----------------------------------------------------

        if (
            mejor_resultado is None
            or puntaje_ponderado
            >
            mejor_resultado["score"]
        ):

            mejor_resultado = resultado

    return mejor_resultado