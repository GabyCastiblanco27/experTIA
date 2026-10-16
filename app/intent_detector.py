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
# EQUIVALENCIAS DE ACCIONES POR INTENCIÓN
# ============================================================

EQUIVALENCIAS_INTENCION = {

    "CONSULTAR": {
        "consultar",
        "consulta",
        "consulto",
        "consultas",
        "ver",
        "veo",
        "ves",
        "revisar",
        "reviso",
        "revisa",
        "buscar",
        "busco",
        "visualizar",
        "visualizo",
        "verificar",
        "verifico",

        # Expresiones para consultar estado o ubicación
        "donde",
        "esta",
        "encuentra",
        "estado",
        "seguimiento",
        "tracking",
    },

    "SOLICITAR": {
        "solicitar",
        "solicito",
        "solicitud",

        "pedir",
        "pido",

        "crear",
        "creo",
        "creacion",

        "registrar",
        "registro",
        "registra",
        "registrado",
        "registrada",

        "agregar",
        "agrega",

        "ingresar",
        "ingreso",

        "reponer",
        "repongo",
        "reposicion",
        "reposiciones",
    },
    

    "REPORTAR": {
        "reportar",
        "reporto",
        "reporte",
        "dano",
        "danar",
        "danado",
        "romper",
        "rompio",
        "rota",
        "roto",
        "deteriorado",
        "deteriorada",
        "deterioro",
        "desgaste",
        "extraviado",
        "extraviada",
        "perdido",
        "perdida",
    },

    "MODIFICAR": {
        "modificar",
        "modifico",
        "modificacion",
        "actualizar",
        "actualizo",
        "actualizacion",
        "cambiar",
        "cambio",
        "reemplazar",
        "reemplazo",
    },
}


# ============================================================
# EXPRESIONES DE REPORTE
# ============================================================

EXPRESIONES_REPORTAR = {
    "ya no sirve",
    "no sirve",
    "ya no funciona",
    "no funciona",
    "ya no funcionan",
    "no funcionan",
    "esta en mal estado",
    "esta deteriorado",
    "esta deteriorada",
}


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
# DETECTAR ACCIONES
# ============================================================

def detectar_acciones_intencion(
    pregunta
):
    """
    Detecta acciones o expresiones que permiten
    identificar directamente una intención.
    """

    texto = normalize(
        pregunta
    )

    if not texto:
        return set()

    tokens = set(
        tokenize(texto)
    )

    intenciones_detectadas = set()

    # --------------------------------------------------------
    # Acciones directas
    # --------------------------------------------------------

    for intencion, variantes in EQUIVALENCIAS_INTENCION.items():

        if tokens & variantes:

            intenciones_detectadas.add(
                intencion
            )

    # --------------------------------------------------------
    # Expresiones de reporte
    # --------------------------------------------------------

    for expresion in EXPRESIONES_REPORTAR:

        expresion_normalizada = normalize(
            expresion
        )

        if expresion_normalizada in texto:

            intenciones_detectadas.add(
                "REPORTAR"
            )

    return intenciones_detectadas


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


    acciones_detectadas = detectar_acciones_intencion(
        pregunta
    )

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
        # Equivalencia de acción
        # ----------------------------------------------------

        intencion = variante["intencion"]

        if intencion in acciones_detectadas:

            puntaje = max(
                puntaje,
                0.85
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

    # ========================================================
    # UMBRAL DE CONFIANZA
    # ========================================================

    UMBRAL_INTENCION = 0.50

    if (
        mejor_resultado is None
        or mejor_resultado["score"]
        < UMBRAL_INTENCION
    ):

        return None

    return mejor_resultado