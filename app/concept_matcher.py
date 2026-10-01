"""
concept_matcher.py

Compara la pregunta del usuario contra
el contenido conceptual de cada conocimiento.

La similitud prioriza coincidencias de términos
relevantes aunque cambie el orden de las palabras.
"""

from difflib import SequenceMatcher
import token

from app.normalizer import normalize, tokenize


# ============================================================
# TOKENS GENÉRICOS
# ============================================================

TOKENS_GENERICOS = {
    "como",
    "puedo",
    "puede",
    "quiero",
    "necesito",
}


EXPRESIONES_DANO = {
    "ya no sirve": "dano",
    "no sirve": "dano",
    "ya no funcionan": "dano",
    "no funciona": "dano",
    "ya no funcionan bien": "dano",
    "no funcionan bien": "dano",
    "esta en mal estado": "dano",
    "esta deteriorado": "dano",
    "esta deteriorada": "dano",
}


# ============================================================
# EQUIVALENCIAS DE ACCIONES
# ============================================================

EQUIVALENCIAS_ACCION = {
    "creacion": {
        "crear",
        "creo",
        "crea",
        "creacion",
        "registrar",
        "registro",
        "registra",
        "registrado",
        "registrada",
        "ingresar",
        "ingreso",
        "ingresa",
        "agregar",
        "agrego",
        "agrega",
        "alta",
    },

    "cambio": {
        "cambiar",
        "cambio",
        "cambie",
        "cambias",
        "cambia",
        "cambian",
        "cambiamos",
        "cambiado",
        "cambiada",
        "cambiados",
        "cambiadas",
        "cambiarlas",
        "cambiarlos",

        "reemplazar",
        "reemplazo",
        "reemplazos",
        "reemplazado",
        "reemplazada",
        "reemplazados",
        "reemplazadas",
        "reemplazarla",
        "reemplazarlo",
        "reemplazarlas",
        "reemplazarlos",

        "reponer",
        "repongo",
        "reposicion",
        "reposiciones",
    },

    "dano": {
        "dañado",
        "dañada",
        "dañados",
        "dañadas",
        "dañe",
        "dañar",
        "daña",
        "danado",
        "danada",
        "danados",
        "danadas",

        "roto",
        "rota",
        "rotos",
        "rotas",
        "rompio",
        "romper",
        "rompieron",

        "deteriorado",
        "deteriorada",
        "deteriorados",
        "deterioradas",
        "deterioro",

        "desgastado",
        "desgastada",
        "desgastados",
        "desgastadas",
        "desgaste",

        "averiado",
        "averiada",
        "averiados",
        "averiadas",
        "averia",
    },

    "perdida": {
        "perdi",
        "perdido",
        "perdida",
        "perdidos",
        "perdidas",
        "extraviado",
        "extraviada",
        "extraviados",
        "extraviadas",
        "extravie",
    }
}




def obtener_grupo_equivalencia(token):
    """
    Devuelve el concepto común al que pertenece un token.
    Si no existe equivalencia, devuelve el mismo token.
    """

    for grupo, variantes in EQUIVALENCIAS_ACCION.items():

        if token == grupo or token in variantes:
            return grupo

    return token


# ============================================================
# SIMILITUD POR TOKENS
# ============================================================

def similitud_tokens(texto1, texto2):

    tokens1 = set(tokenize(texto1))
    tokens2 = set(tokenize(texto2))

    if not tokens1 or not tokens2:
        return 0.0

    interseccion = tokens1 & tokens2

    if not interseccion:
        return 0.0

    # --------------------------------------------------------
    # Coincidencia exacta
    # --------------------------------------------------------

    if tokens1 == tokens2:
        return 1.0

    # --------------------------------------------------------
    # Eliminar tokens genéricos de la comparación
    # --------------------------------------------------------

    relevantes1 = tokens1 - TOKENS_GENERICOS
    relevantes2 = tokens2 - TOKENS_GENERICOS

    interseccion_relevante = (
        relevantes1 & relevantes2
    )

    # Si después de eliminar términos genéricos
    # no queda ninguna coincidencia relevante,
    # no debemos considerar que las preguntas son iguales.

    if not interseccion_relevante:

        if interseccion.issubset(TOKENS_GENERICOS):
            return 0.10

        return 0.0

    # --------------------------------------------------------
    # Coincidencia exacta de conceptos relevantes
    # --------------------------------------------------------

    if relevantes1 == relevantes2:
        return 1.0

    # --------------------------------------------------------
    # Cobertura de términos relevantes
    # --------------------------------------------------------

    cobertura1 = (
        len(interseccion_relevante)
        /
        len(relevantes1)
        if relevantes1
        else 0.0
    )

    cobertura2 = (
        len(interseccion_relevante)
        /
        len(relevantes2)
        if relevantes2
        else 0.0
    )

    # --------------------------------------------------------
    # Promedio armónico
    # --------------------------------------------------------

    if cobertura1 + cobertura2 == 0:
        return 0.0

    score = (
        2
        *
        cobertura1
        *
        cobertura2
        /
        (cobertura1 + cobertura2)
    )

    return min(score, 1.0)


# ============================================================
# SIMILITUD DE TEXTO
# ============================================================

def similitud_texto(texto1, texto2):

    texto1 = normalize(texto1)
    texto2 = normalize(texto2)

    if not texto1 or not texto2:
        return 0.0

    tokens1 = set(tokenize(texto1))
    tokens2 = set(tokenize(texto2))

    if not tokens1 or not tokens2:
        return 0.0

     # --------------------------------------------------------
    # Detectar expresiones completas de daño
    # --------------------------------------------------------

    conceptos_expresion1 = {
        grupo
        for expresion, grupo in EXPRESIONES_DANO.items()
        if expresion in texto1
    }

    conceptos_expresion2 = {
        grupo
        for expresion, grupo in EXPRESIONES_DANO.items()
        if expresion in texto2
    }

    # --------------------------------------------------------
    # Convertir acciones equivalentes a conceptos comunes
    # --------------------------------------------------------

    conceptos1 = {
        obtener_grupo_equivalencia(token)
        for token in tokens1
    }

    conceptos2 = {
        obtener_grupo_equivalencia(token)
        for token in tokens2
    }


    # Agregar conceptos detectados mediante expresiones completas
    conceptos1.update(conceptos_expresion1)
    conceptos2.update(conceptos_expresion2)


    # --------------------------------------------------------
    # Coincidencia exacta
    # --------------------------------------------------------

    if conceptos1 == conceptos2:
        return 1.0

    # --------------------------------------------------------
    # Eliminar términos genéricos
    # --------------------------------------------------------

    relevantes1 = conceptos1 - TOKENS_GENERICOS
    relevantes2 = conceptos2 - TOKENS_GENERICOS

    if not relevantes1 or not relevantes2:
        return 0.0

    coincidencias = relevantes1 & relevantes2

    # --------------------------------------------------------
    # No hay coincidencia relevante
    # --------------------------------------------------------

    if not coincidencias:
        return 0.0

    # --------------------------------------------------------
    # Coincidencia de un concepto principal
    #
    # Si la pregunta contiene un concepto que también aparece
    # en la referencia, no debemos penalizar excesivamente
    # porque la pregunta tenga palabras adicionales.
    #
    # Ejemplo:
    #
    # PDF RUT
    #      ↓
    # descargar RUT
    #
    # Ambos hablan del mismo objeto: RUT.
    # --------------------------------------------------------

    if len(coincidencias) == 1:

        concepto = next(iter(coincidencias))

        # Cantidad de conceptos relevantes
        cantidad1 = len(relevantes1)
        cantidad2 = len(relevantes2)

        # Si ambos textos comparten un único concepto relevante,
        # damos prioridad a esa coincidencia.
        if cantidad1 == 1 or cantidad2 == 1:

            score_secuencia = SequenceMatcher(
                None,
                texto1,
                texto2
            ).ratio()

            return min(
                0.75 + (score_secuencia * 0.10),
                0.85
            )

    # --------------------------------------------------------
    # Si todos los conceptos de la pregunta están contenidos
    # en la referencia
    # --------------------------------------------------------

    if relevantes1.issubset(relevantes2):
        return 0.85

    # --------------------------------------------------------
    # Si todos los conceptos de la referencia están contenidos
    # en la pregunta
    # --------------------------------------------------------

    if relevantes2.issubset(relevantes1):
        return 0.80

    # --------------------------------------------------------
    # Cobertura de conceptos
    # --------------------------------------------------------

    cobertura1 = (
        len(coincidencias)
        /
        len(relevantes1)
    )

    cobertura2 = (
        len(coincidencias)
        /
        len(relevantes2)
    )

    if cobertura1 + cobertura2 == 0:
        return 0.0

    score_tokens = (
        2
        *
        cobertura1
        *
        cobertura2
        /
        (cobertura1 + cobertura2)
    )

    # --------------------------------------------------------
    # Similitud de secuencia
    # --------------------------------------------------------

    score_secuencia = SequenceMatcher(
        None,
        texto1,
        texto2
    ).ratio()

    # --------------------------------------------------------
    # Score final
    # --------------------------------------------------------

    score = (
        score_tokens * 0.85
        +
        score_secuencia * 0.15
    )

    return min(
        score,
        1.0
    )
# ============================================================
# PREGUNTAS ALTERNATIVAS
# ============================================================

def mejor_pregunta_alternativa(
    pregunta,
    preguntas_alternativas
):
    """
    Encuentra la pregunta alternativa más relacionada
    con la pregunta del usuario.
    """

    if not preguntas_alternativas:
        return 0.0

    mejor = 0.0

    for alternativa in preguntas_alternativas:

        if not alternativa:
            continue

        score = similitud_texto(
            pregunta,
            alternativa
        )

        if score > mejor:
            mejor = score

    return min(
        mejor,
        1.0
    )


# ============================================================
# SCORE CONCEPTUAL
# ============================================================

def calcular_score_conceptual(
    pregunta,
    conocimiento,
    preguntas_alternativas
):
    """
    Calcula el score conceptual de un conocimiento.

    Componentes:

    - Preguntas alternativas: 85 %
    - Título: 10 %
    - Descripción: 5 %

    Las preguntas alternativas tienen mayor peso porque
    representan diferentes formas reales en que un usuario
    puede formular una misma consulta.
    """

    score_alternativas = (
        mejor_pregunta_alternativa(
            pregunta,
            preguntas_alternativas
        )
    )

    score_titulo = (
        similitud_texto(
            pregunta,
            conocimiento.get(
                "titulo",
                ""
            )
        )
    )

    score_descripcion = (
        similitud_texto(
            pregunta,
            conocimiento.get(
                "descripcion",
                ""
            )
        )
    )

    # --------------------------------------------------------
    # Ranking conceptual
    # --------------------------------------------------------

    score_final = (

        score_alternativas
        *
        0.85

        +

        score_titulo
        *
        0.10

        +

        score_descripcion
        *
        0.05
    )

    return {

        "score":
            min(
                score_final,
                1.0
            ),

        "preguntas_alternativas":
            score_alternativas,

        "titulo":
            score_titulo,

        "descripcion":
            score_descripcion
    }