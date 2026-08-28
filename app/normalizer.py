"""
normalizer.py
-------------
Normalización de preguntas realizadas a ExperTIA.

La normalización permite reconocer diferentes formas
de expresar una misma idea.

Ejemplos:

    radicar      -> radicacion
    radicación   -> radicacion

    factura      -> factura
    facturas     -> factura

    solicitar    -> solicitud
    solicito     -> solicitud

    cambiar      -> cambio
    cambios      -> cambio
"""

import re
import unicodedata


# ============================================================
# STOPWORDS
# ============================================================

STOPWORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "es",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "mis",
    "para",
    "por",
    "que",
    "se",
    "su",
    "sus",
    "un",
    "una",
    "unos",
    "unas",
    "y",
    "o",
    "u",
    "como",
    "donde",
    "cuando",
    "cual",
    "cuales",
    "puedo",
    "puede",
    "pueden",
    "quiero",
    "necesito",
    "quisiera",
    "hay",
    "hacer",
    "hago"
}


# ============================================================
# REEMPLAZOS LÉXICOS
# ============================================================

REPLACEMENTS = {

    # --------------------------------------------------------
    # RETIROS / CESANTÍAS
    # --------------------------------------------------------

    "retirar": "retiro",
    "retiros": "retiro",
    "retiro": "retiro",

    # --------------------------------------------------------
    # SOLICITUDES
    # --------------------------------------------------------

    "solicitar": "solicitud",
    "solicito": "solicitud",
    "solicitudes": "solicitud",
    "solicitud": "solicitud",

    # --------------------------------------------------------
    # TRÁMITES
    # --------------------------------------------------------

    "tramitar": "tramite",
    "tramito": "tramite",
    "tramites": "tramite",
    "tramite": "tramite",

    # --------------------------------------------------------
    # DESCARGAS
    # --------------------------------------------------------

    "descargar": "descarga",
    "descargo": "descarga",
    "descargas": "descarga",
    "descarga": "descarga",

    # --------------------------------------------------------
    # ACTUALIZACIONES
    # --------------------------------------------------------

    "actualizar": "actualizacion",
    "actualizo": "actualizacion",
    "actualizaciones": "actualizacion",
    "actualizacion": "actualizacion",

    # --------------------------------------------------------
    # REPORTES
    # --------------------------------------------------------

    "reportar": "reporte",
    "reporto": "reporte",
    "reportes": "reporte",
    "reporte": "reporte",

    # --------------------------------------------------------
    # RADICACIÓN / RADICAR
    # --------------------------------------------------------

    "radicar": "radicacion",
    "radico": "radicacion",
    "radican": "radicacion",
    "radicado": "radicacion",
    "radicados": "radicacion",
    "radicacion": "radicacion",
    "radicaciones": "radicacion",

    # --------------------------------------------------------
    # FACTURA / FACTURAS
    # --------------------------------------------------------

    "factura": "factura",
    "facturas": "factura",
    "facturacion": "facturacion",
    "facturaciones": "facturacion",
    "facturar": "facturacion",

    # --------------------------------------------------------
    # RECEPCIÓN
    # --------------------------------------------------------

    "recibir": "recepcion",
    "recibo": "recepcion",
    "reciben": "recepcion",
    "recibimos": "recepcion",
    "recepcion": "recepcion",
    "recepciones": "recepcion",

    # --------------------------------------------------------
    # CIERRES
    # --------------------------------------------------------

    "cerrar": "cierre",
    "cierres": "cierre",
    "cierre": "cierre",

    # --------------------------------------------------------
    # CAMBIOS / REEMPLAZOS
    # --------------------------------------------------------

    "cambiar": "cambio",
    "cambio": "cambio",
    "cambios": "cambio",
    "cambie": "cambio",
    "reemplazar": "reemplazo",
    "reemplazo": "reemplazo",
    "reemplazos": "reemplazo",
    "reemplazado": "reemplazo",

    # --------------------------------------------------------
    # REPOSICIÓN
    # --------------------------------------------------------

    "reponer": "reposicion",
    "repongo": "reposicion",
    "reponer": "reposicion",
    "reposiciones": "reposicion",
    "reposicion": "reposicion",

    # --------------------------------------------------------
    # DAÑOS
    # --------------------------------------------------------

    "dañado": "daño",
    "dañada": "daño",
    "dañados": "daño",
    "dañadas": "daño",
    "dañaron": "daño",
    "dañe": "daño",
    "daño": "daño",
    "danos": "daño",

    # --------------------------------------------------------
    # PÉRDIDA
    # --------------------------------------------------------

    "perder": "perdida",
    "perdi": "perdida",
    "perdio": "perdida",
    "perdieron": "perdida",
    "perdida": "perdida",
    "perdidas": "perdida",

    # --------------------------------------------------------
    # ASIGNACIÓN
    # --------------------------------------------------------

    "asignar": "asignacion",
    "asigno": "asignacion",
    "asignaciones": "asignacion",
    "asignacion": "asignacion",

    # --------------------------------------------------------
    # SOLICITUD DE INFORMACIÓN
    # --------------------------------------------------------

    "consultar": "consulta",
    "consulto": "consulta",
    "consultas": "consulta",
    "consulta": "consulta",

    # --------------------------------------------------------
    # FECHAS
    # --------------------------------------------------------

    "fecha": "fecha",
    "fechas": "fecha",

    # --------------------------------------------------------
    # PLAZOS
    # --------------------------------------------------------

    "plazo": "plazo",
    "plazos": "plazo",

    # --------------------------------------------------------
    # PROVEEDORES
    # --------------------------------------------------------

    "proveedor": "proveedor",
    "proveedores": "proveedor"
}


# ============================================================
# ELIMINAR TILDES
# ============================================================

def remove_accents(text: str) -> str:
    """
    Elimina las tildes de un texto.

    Ejemplo:

        cesantías -> cesantias
        nómina -> nomina
        radicación -> radicacion
    """

    if not text:
        return ""

    normalized = unicodedata.normalize(
        "NFD",
        text
    )

    return "".join(
        character
        for character in normalized
        if unicodedata.category(
            character
        ) != "Mn"
    )


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize(text: str) -> str:
    """
    Normaliza una pregunta.

    Ejemplo:

        ¿Cuál es el plazo para radicar una factura a proveedores?

    Resultado aproximado:

        plazo radicacion factura proveedor
    """

    if not text:
        return ""

    # --------------------------------------------------------
    # Minúsculas
    # --------------------------------------------------------

    text = text.lower().strip()

    # --------------------------------------------------------
    # Eliminar tildes
    # --------------------------------------------------------

    text = remove_accents(text)

    # --------------------------------------------------------
    # Eliminar signos
    # --------------------------------------------------------

    text = re.sub(
        r"[^a-z0-9ñü\s]",
        " ",
        text
    )

    # --------------------------------------------------------
    # Eliminar espacios repetidos
    # --------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    # --------------------------------------------------------
    # Procesar tokens
    # --------------------------------------------------------

    tokens = []

    for token in text.split():

        # Ignorar stopwords
        if token in STOPWORDS:
            continue

        # Aplicar equivalencia léxica
        token = REPLACEMENTS.get(
            token,
            token
        )

        tokens.append(token)

    return " ".join(tokens)


# ============================================================
# TOKENIZACIÓN
# ============================================================

def tokenize(text: str) -> list[str]:
    """
    Convierte una pregunta en tokens normalizados.

    Ejemplo:

        ¿Cuál es el plazo para radicar una factura a proveedores?

    Resultado:

        [
            "plazo",
            "radicacion",
            "factura",
            "proveedor"
        ]
    """

    normalized = normalize(text)

    if not normalized:
        return []

    return normalized.split()