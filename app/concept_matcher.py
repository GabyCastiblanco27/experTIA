"""
concept_matcher.py

Compara la pregunta del usuario contra
el contenido conceptual de cada conocimiento.

La similitud prioriza coincidencias de términos
relevantes y objetos específicos del dominio,
aunque cambie el orden de las palabras.
"""

from difflib import SequenceMatcher

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


# ============================================================
# TOKENS GENÉRICOS DE ACCIÓN / CONTEXTO
# ============================================================

# Estos términos aparecen en muchos conocimientos y por sí
# solos no deberían determinar cuál conocimiento corresponde.

TOKENS_CONTEXTO_GENERICO = {
    "reportar",
    "reporte",
    "reporto",
    "solicitar",
    "solicitud",
    "solicito",
    "consultar",
    "consulta",
    "consulto",
    "ver",
    "revisar",
    "buscar",
    "verificar",
    "novedad",
    "novedades",
    "gestion",
    "gestionar",
    "proceso",
    "comprar",
    "compra",
    "compras",
}


# ============================================================
# EXPRESIONES DE DAÑO
# ============================================================

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
# EQUIVALENCIAS DE CONCEPTOS DEL DOMINIO
# ============================================================

EQUIVALENCIAS_CONCEPTO = {
    "orden_pago": {
        "op",
        "orden_pago",
    },

    "material": {
        "material",
        "materiales",
        "insumo",
        "insumos",
        "elemento",
        "elementos",
        "suministro",
        "suministros",
        "recurso",
        "recursos",
    },
}

# ============================================================
# REQUISITOS DE CONTEXTO POR CONOCIMIENTO
# ============================================================


REQUISITOS_CONTEXTO = {
    29: {
    "nombre": "Materiales Productivos",
    "grupos": [
        {
            "material_productivo",
            "productivo",
            "materia_prima",
            "envase",
            "empaque",
            "ax",
            "axapta",
            "detalle_articulo",
            "codigo_material",
            "proveedor_material",
            "proveedor_articulo",
        }
    ]
},

    42: {
        "nombre": "Compra de Material para Proyectos de Desarrollo",
        "grupos": [
            {
                "proyecto",
                "desarrollo",
                "axapta",
                "material_proyecto",
                "proyecto_desarrollo",
                "compra_desarrollo",
            }
        ]
    }
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
    },

    "consulta": {
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
    },
}


# ============================================================
# GRUPOS DE EQUIVALENCIA
# ============================================================

def obtener_grupo_equivalencia(token):
    """
    Devuelve el concepto común al que pertenece un token.

    Primero revisa equivalencias de acciones y luego
    equivalencias de conceptos del dominio.

    Ejemplos:
        solicitar -> solicitar
        insumos -> material
        materiales -> material
        elementos -> material
        suministros -> material
    """

    # --------------------------------------------
    # Equivalencias de acciones
    # --------------------------------------------

    for grupo, variantes in EQUIVALENCIAS_ACCION.items():

        if token == grupo or token in variantes:
            return grupo

    # --------------------------------------------
    # Equivalencias de conceptos del dominio
    # --------------------------------------------

    for grupo, variantes in EQUIVALENCIAS_CONCEPTO.items():

        if token == grupo or token in variantes:
            return grupo

    # --------------------------------------------
    # Si no existe equivalencia
    # --------------------------------------------

    return token

# ============================================================
# NORMALIZACIÓN DE CONCEPTOS DE DOMINIO
# ============================================================

def normalizar_conceptos_dominio(texto):
    """
    Convierte abreviaturas y expresiones específicas del dominio
    en conceptos comunes.

    Ejemplo:
        OP -> orden_pago
        orden de pago -> orden_pago
    """

    tokens = set(tokenize(texto))

    conceptos = {
        obtener_grupo_equivalencia(token)
        for token in tokens
    }

    # OP es equivalente a Orden de Pago
    if "op" in tokens:

        conceptos.discard("op")
        conceptos.add("orden_pago")

    # Orden + pago representan Orden de Pago
    if "orden" in tokens and "pago" in tokens:

        conceptos.discard("orden")
        conceptos.discard("pago")
        conceptos.add("orden_pago")

    return conceptos


# ============================================================
# OBTENER CONCEPTOS RELEVANTES
# ============================================================

def obtener_conceptos_relevantes(texto):
    """
    Obtiene los conceptos realmente útiles para comparar
    dos textos.

    Se eliminan:

    - términos genéricos de conversación
    - términos genéricos de acción/contexto

    De esta forma:

        "¿Cómo reporto una novedad con mis botas?"

    conserva principalmente:

        botas
    """

    conceptos = normalizar_conceptos_dominio(texto)

    # Agregar expresiones de daño
    conceptos_expresion = {
        grupo
        for expresion, grupo in EXPRESIONES_DANO.items()
        if expresion in normalize(texto)
    }

    conceptos.update(conceptos_expresion)

    relevantes = (
        conceptos
        - TOKENS_GENERICOS
        - TOKENS_CONTEXTO_GENERICO
    )

    return relevantes

# Términos que necesitan un objeto específico
# para identificar correctamente un conocimiento.

CONCEPTOS_AMPLIOS = {
    "formato",
    "documento",
    "proveedor",
    "certificado",
    "certificacion",
}


# ============================================================
# VALIDACIÓN DE CONTEXTO ESPECÍFICO
# ============================================================

def cumple_requisito_contexto(pregunta, conocimiento_id):
    """
    Determina si la pregunta contiene suficiente contexto
    para que un conocimiento específico pueda competir.

    Se utiliza únicamente para conocimientos que requieren
    contexto adicional para evitar falsos positivos.
    """

    requisito = REQUISITOS_CONTEXTO.get(conocimiento_id)

    if not requisito:
        return True

    texto = normalize(pregunta)

    tokens = set(tokenize(texto))

    # --------------------------------------------------------
    # Contextos compuestos
    # --------------------------------------------------------

    contextos_compuestos = {
        "material_productivo": {
            "material",
            "productivo"
        },
        "materia_prima": {
            "materia",
            "prima"
        },
        "detalle_articulo": {
            "detalle",
            "articulo"
        },
        "codigo_material": {
            "codigo",
            "material"
        },
        "proveedor_material": {
        "proveedor",
        "material"
        },
        "proveedor_articulo": {
            "proveedor",
            "articulo"
        }
    }

    # --------------------------------------------------------
    # Validar grupos
    # --------------------------------------------------------

    for grupo in requisito["grupos"]:

        for concepto in grupo:

            if concepto in contextos_compuestos:

                if contextos_compuestos[concepto].issubset(tokens):
                    return True

            elif concepto in tokens:
                return True

    return False


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

    if tokens1 == tokens2:
        return 1.0

    relevantes1 = tokens1 - TOKENS_GENERICOS
    relevantes2 = tokens2 - TOKENS_GENERICOS

    interseccion_relevante = (
        relevantes1 & relevantes2
    )

    if not interseccion_relevante:

        if interseccion.issubset(TOKENS_GENERICOS):
            return 0.10

        return 0.0

    if relevantes1 == relevantes2:
        return 1.0

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

    conceptos1 = obtener_conceptos_relevantes(texto1)
    conceptos2 = obtener_conceptos_relevantes(texto2)

    if not conceptos1 or not conceptos2:
        return 0.0

    # --------------------------------------------------------
    # Coincidencia exacta
    # --------------------------------------------------------

    if conceptos1 == conceptos2:
        return 1.0

    coincidencias = conceptos1 & conceptos2

    # --------------------------------------------------------
    # No existe coincidencia de objeto/concepto
    # --------------------------------------------------------

    if not coincidencias:
        return 0.0

    # --------------------------------------------------------
    # Un único concepto compartido
    # --------------------------------------------------------

    if len(coincidencias) == 1:

        cantidad1 = len(conceptos1)
        cantidad2 = len(conceptos2)

        if cantidad1 == 1 or cantidad2 == 1:

            concepto = next(iter(coincidencias))

            # Una coincidencia basada únicamente en un
            # concepto amplio no identifica un procedimiento
            # específico.
            #
            # Ejemplo:
            # "formatos de solicitud"
            # "formatos de confidencialidad"
            #
            # Ambos comparten "formato", pero corresponden
            # a procedimientos diferentes.

            if concepto in CONCEPTOS_AMPLIOS:
                return 0.25

            # Para conceptos específicos, conservamos
            # la similitud textual como refuerzo.

            score_secuencia = SequenceMatcher(
                None,
                texto1,
                texto2
            ).ratio()

            return min(
                0.65 + (score_secuencia * 0.15),
                0.80
            )

    # --------------------------------------------------------
    # Todos los conceptos de la pregunta están contenidos
    # en la referencia
    # --------------------------------------------------------

    if conceptos1.issubset(conceptos2):
        return 0.85

    # --------------------------------------------------------
    # Todos los conceptos de la referencia están contenidos
    # en la pregunta
    # --------------------------------------------------------

    if conceptos2.issubset(conceptos1):
        return 0.80

    # --------------------------------------------------------
    # Cobertura de conceptos
    # --------------------------------------------------------

    cobertura1 = (
        len(coincidencias)
        /
        len(conceptos1)
    )

    cobertura2 = (
        len(coincidencias)
        /
        len(conceptos2)
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

    return min(score, 1.0)


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
    """

    conocimiento_id = conocimiento.get("id")

    if not cumple_requisito_contexto(
        pregunta,
        conocimiento_id
    ):
        return {
            "score": 0.0,
            "preguntas_alternativas": 0.0,
            "titulo": 0.0,
            "descripcion": 0.0
        }

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

    score_final = (
        score_alternativas * 0.85
        +
        score_titulo * 0.10
        +
        score_descripcion * 0.05
    )

    return {
        "score": min(score_final, 1.0),

        "preguntas_alternativas":
            score_alternativas,

        "titulo":
            score_titulo,

        "descripcion":
            score_descripcion
    }
