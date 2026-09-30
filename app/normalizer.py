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
    # SOLICITUD
    # --------------------------------------------------------

    "solicitar": "solicitud",
    "solicito": "solicitud",
    "solicita": "solicitud",
    "solicitan": "solicitud",
    "solicitud": "solicitud",
    "solicitudes": "solicitud",

    "pedir": "solicitud",
    "pido": "solicitud",
    "pide": "solicitud",
    "piden": "solicitud",   
    "pedido": "solicitud",
    "pedida": "solicitud",

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
    # CARGAS / SUBIR
    # --------------------------------------------------------

    "subir": "subir",
    "subo": "subir",
    "subes": "subir",
    "sube": "subir",
    "suben": "subir",
    "subimos": "subir",
    "subido": "subir",
    "subida": "subir",
    "subidas": "subir",

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
    "proveedores": "proveedor",

    # --------------------------------------------------------
    # CREACIÓN
    # --------------------------------------------------------

    "crear": "creacion",
    "creo": "creacion",
    "creas": "creacion",
    "crea": "creacion",
    "crean": "creacion",
    "creamos": "creacion",
    "creado": "creacion",
    "creada": "creacion",
    "creados": "creacion",
    "creadas": "creacion",
    "creacion": "creacion",
    "creaciones": "creacion",
    
    # --------------------------------------------------------
    # PAGOS
    # --------------------------------------------------------

    "pagar": "pago",
    "paga": "pago",
    "pagan": "pago",
    "pago": "pago",
    "pagos": "pago",
    "pagado": "pago",
    "pagada": "pago",
    "pagados": "pago",
    "pagadas": "pago",

    # --------------------------------------------------------
    # REGISTRO
    # --------------------------------------------------------
    "registrar": "registro",
    "registro": "registro",
    "registra": "registro",
    "registras": "registro",
    "registran": "registro",
    "registramos": "registro",
    "registrado": "registro",
    "registrada": "registro",
    "registrados": "registro",
    "registradas": "registro",
    "registros": "registro",

    # --------------------------------------------------------
    # ENVÍOS
    # --------------------------------------------------------

    "enviar": "envio",
    "envio": "envio",
    "envia": "envio",
    "envian": "envio",
    "enviamos": "envio",
    "enviado": "envio",
    "enviada": "envio",
    "envios": "envio",

    "mandar": "envio",
    "mando": "envio",
    "manda": "envio",
    "mandan": "envio",

    "despachar": "envio",
    "despacho": "envio",
    "despacha": "envio",
    "despachado": "envio",
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