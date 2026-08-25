"""
keyword_matcher.py

Detecta keywords presentes en la pregunta
y calcula qué conocimientos están relacionados
con ellas.
"""

from app.normalizer import normalize, tokenize
from app.repository import get_keyword_matches


# ============================================================
# DETECCIÓN DE KEYWORDS
# ============================================================

def detectar_keywords(pregunta):
    """
    Detecta las keywords de PostgreSQL presentes
    en la pregunta del usuario.
    """

    if not pregunta:
        return []

    texto_normalizado = normalize(pregunta)

    tokens = set(
        tokenize(pregunta)
    )

    keywords_bd = get_keyword_matches()

    encontradas = []

    for keyword in keywords_bd:

        palabra_bd = normalize(
            keyword["palabra"]
        )

        if not palabra_bd:
            continue

        tokens_keyword = set(
            tokenize(palabra_bd)
        )

        # ----------------------------------------------------
        # Keyword de una palabra
        # ----------------------------------------------------

        if len(tokens_keyword) == 1:

            if palabra_bd in tokens:

                encontradas.append({

                    "conocimiento_id":
                        keyword["conocimiento_id"],

                    "keyword_id":
                        keyword["keyword_id"],

                    "palabra":
                        keyword["palabra"],

                    "peso":
                        float(
                            keyword["peso"] or 1.0
                        )
                })

            continue

        # ----------------------------------------------------
        # Keyword de varias palabras
        # ----------------------------------------------------

        if tokens_keyword.issubset(tokens):

            encontradas.append({

                "conocimiento_id":
                    keyword["conocimiento_id"],

                "keyword_id":
                    keyword["keyword_id"],

                "palabra":
                    keyword["palabra"],

                "peso":
                    float(
                        keyword["peso"] or 1.0
                    )
            })

    return encontradas


# ============================================================
# PUNTAJE DE KEYWORDS
# ============================================================

def calcular_puntajes_keywords(pregunta):
    """
    Calcula el puntaje total de keywords por conocimiento.

    Resultado:

        {
            conocimiento_id: puntaje
        }
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

        puntajes.setdefault(
            conocimiento_id,
            0.0
        )

        puntajes[
            conocimiento_id
        ] += peso

    return puntajes