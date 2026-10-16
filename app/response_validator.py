
"""Validador diagnóstico de consultas de ExperTIA.

Este módulo:
- Identifica señales de preguntas ambiguas o fuera del catálogo.
- Analiza la correspondencia textual entre pregunta y conocimiento.
- NO modifica el motor híbrido.
- NO modifica Neon.
- NO autoriza respuestas automáticamente.

Los criterios son exploratorios y necesitan validación adicional
antes de utilizarse en producción.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping


# ============================================================
# CONFIGURACIÓN DIAGNÓSTICA
# ============================================================

UMBRAL_RERANKER_MUY_BAJO = 0.001

_PALABRAS_GENERICAS = {
    "a", "al", "con", "como", "cual", "cuales",
    "de", "del", "donde", "el", "ella", "en",
    "es", "ese", "esa", "eso", "esta", "este",
    "hacer", "hago", "hay", "informacion",
    "la", "las", "lo", "los", "me", "mi", "mis",
    "necesito", "necesitamos", "obtener",
    "para", "por", "puedo", "puede",
    "problema", "procedimiento", "quiero",
    "quisiera", "que", "se", "solicitar",
    "solicitud", "su", "sus", "saber",
    "tramite", "tengo", "tener", "un", "una",
    "unos", "unas", "y", "consultar",
    "consulta", "documento", "documentos",
    "estado", "estados", "algo", "ayuda",
    "tema", "asunto",
}

_REFERENCIAS_SIN_ANTECEDENTE = {
    "eso", "aquello", "anterior"
}

# Términos corporativos demasiado generales para demostrar
# por sí solos que una respuesta cubre una pregunta.
_PALABRAS_CORPORATIVAS_GENERICAS = {
    "megalabs", "empresa", "compania", "corporativa",
    "corporativo", "colombia", "informacion",
    "archivo", "archivos", "actualizado", "actualizada",
    "actualizar", "nuevo", "nueva",
}


# ============================================================
# UTILIDADES
# ============================================================

def _tokens(texto: str) -> list[str]:
    """Normaliza el texto, elimina tildes y separa palabras."""

    normalizado = unicodedata.normalize(
        "NFKD",
        texto.lower()
    )

    sin_tildes = "".join(
        caracter
        for caracter in normalizado
        if not unicodedata.combining(caracter)
    )

    return re.findall(r"[a-z0-9]+", sin_tildes)


def _numero(valor: Any) -> float | None:
    """Convierte un valor numérico de forma segura."""

    try:
        if valor is None or valor == "":
            return None

        return float(valor)

    except (TypeError, ValueError):
        return None


# ============================================================
# 1. VALIDACIÓN DIAGNÓSTICA ORIGINAL
# ============================================================

def diagnosticar_validacion(
    pregunta: str,
    resultado_hibrido: Mapping[str, Any] | None = None,
    *,
    senales: Mapping[str, Any] | None = None,
    error_tecnico: str | None = None,
) -> dict[str, Any]:
    """
    Clasifica señales preliminares.

    No acepta ni rechaza automáticamente una consulta.
    """

    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError(
            "La pregunta debe ser un texto no vacío."
        )

    h = resultado_hibrido or {}
    s = dict(senales or {})

    detalle = h.get("detalle_ranking") or {}
    seleccionado = h.get("resultado") or {}

    score = _numero(
        seleccionado.get(
            "score_reranker_bruto",
            s.get("score_reranker_bruto")
        )
    )

    similitud = _numero(
        detalle.get(
            "similitud_semantica_top1",
            s.get("similitud_semantica_top1")
        )
    )

    tradicional = _numero(
        detalle.get(
            "puntaje_tradicional_seleccionado",
            s.get("puntaje_tradicional_seleccionado")
        )
    )

    error = error_tecnico or s.get("error")

    motivos = []

    if error:

        estado = "error_tecnico"

        motivos.append(
            "La recuperación falló; no interpretar "
            "como ausencia de conocimiento."
        )

    else:

        palabras = _tokens(pregunta)

        especificas = [
            palabra
            for palabra in palabras
            if palabra not in _PALABRAS_GENERICAS
        ]

        referencia_suelta = any(
            palabra in _REFERENCIAS_SIN_ANTECEDENTE
            for palabra in palabras
        )

        if (
            not especificas
            or (
                referencia_suelta
                and len(especificas) <= 1
            )
        ):

            estado = "requiere_aclaracion"

            motivos.append(
                "La pregunta no identifica claramente "
                "un asunto o utiliza una referencia "
                "sin contexto."
            )

        elif (
            score is not None
            and score < UMBRAL_RERANKER_MUY_BAJO
        ):

            estado = "posible_fuera_catalogo"

            motivos.append(
                "Puntuación del reranker muy baja. "
                "Es una señal exploratoria, "
                "no un rechazo validado."
            )

        else:

            estado = "validacion_insuficiente"

            motivos.append(
                "Existe un candidato, pero todavía "
                "no se ha verificado que su respuesta "
                "cubra la consulta."
            )

        if score is None:

            motivos.append(
                "No hay puntuación disponible "
                "del reranker."
            )

    return {
        "estado_diagnostico": estado,
        "motivos": motivos,
        "score_reranker_bruto": score,
        "similitud_semantica_top1": similitud,
        "puntaje_tradicional_seleccionado": tradicional,
        "respuesta_autorizada": False,
        "validacion_pendiente": True,
    }


# ============================================================
# 2. ANÁLISIS DE COBERTURA TEXTUAL (NUEVO)
# ============================================================

def analizar_cobertura_textual(
    pregunta: str,
    conocimiento: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """
    Analiza coincidencias textuales entre una pregunta
    y el conocimiento seleccionado.

    Utiliza:
    - titulo
    - descripcion
    - respuesta

    IMPORTANTE:
    La coincidencia textual NO demuestra que la respuesta
    sea correcta. Puede haber sinónimos, negaciones,
    información incompleta o diferencias de significado.

    Esta función solo genera señales de diagnóstico.
    """

    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError(
            "La pregunta debe ser un texto no vacío."
        )

    conocimiento = conocimiento or {}

    # --------------------------------------------------------
    # Construir el contenido que vamos a comparar
    # --------------------------------------------------------

    campos = (
        "titulo",
        "descripcion",
        "respuesta",
    )

    partes = []

    for campo in campos:

        valor = conocimiento.get(campo)

        if valor is not None and str(valor).strip():
            partes.append(str(valor).strip())

    texto_conocimiento = " ".join(partes)

    # --------------------------------------------------------
    # Extraer términos específicos
    # --------------------------------------------------------

    palabras_pregunta = set(_tokens(pregunta))
    palabras_conocimiento = set(_tokens(texto_conocimiento))

    palabras_excluidas = (
        _PALABRAS_GENERICAS
        | _PALABRAS_CORPORATIVAS_GENERICAS
    )

    terminos_pregunta = {
        palabra
        for palabra in palabras_pregunta
        if palabra not in palabras_excluidas
        and len(palabra) > 2
    }

    terminos_conocimiento = {
        palabra
        for palabra in palabras_conocimiento
        if palabra not in palabras_excluidas
        and len(palabra) > 2
    }

    coincidentes = (
        terminos_pregunta & terminos_conocimiento
    )

    no_encontrados = (
        terminos_pregunta - terminos_conocimiento
    )

    # --------------------------------------------------------
    # Calcular proporción de coincidencia
    # --------------------------------------------------------

    proporcion = (
        len(coincidentes) / len(terminos_pregunta)
        if terminos_pregunta
        else 0.0
    )

    # --------------------------------------------------------
    # Clasificación exploratoria
    # --------------------------------------------------------

    if not texto_conocimiento:

        estado = "sin_contenido"

        motivo = (
            "El conocimiento seleccionado no contiene "
            "texto suficiente para evaluar cobertura."
        )

    elif not terminos_pregunta:

        estado = "sin_elementos_especificos"

        motivo = (
            "La pregunta no contiene términos específicos "
            "suficientes para esta comparación."
        )

    elif not coincidentes:

        estado = "sin_coincidencia_textual_especifica"

        motivo = (
            "No se encontraron términos específicos "
            "compartidos entre la pregunta y el conocimiento."
        )

    elif proporcion < 0.5:

        estado = "coincidencia_textual_limitada"

        motivo = (
            "Solo una parte de los términos específicos "
            "aparece en el conocimiento seleccionado."
        )

    else:

        estado = "coincidencia_textual"

        motivo = (
            "Existen términos específicos compartidos, "
            "pero no se ha comprobado que la respuesta "
            "resuelva completamente la pregunta."
        )

    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    return {
        "estado_cobertura": estado,
        "motivo_cobertura": motivo,
        "terminos_consulta": sorted(terminos_pregunta),
        "terminos_coincidentes": sorted(coincidentes),
        "terminos_no_encontrados": sorted(no_encontrados),
        "proporcion_coincidencia": round(proporcion, 4),

        # Esta versión no certifica cobertura semántica.
        "cobertura_verificada": False,

        # No permitir respuestas automáticas todavía.
        "respuesta_autorizada": False,
        "validacion_pendiente": True,
    }


def verificar_cancelacion(pregunta: str, conocimiento: dict) -> dict:
    """Protección conservadora para cancelaciones y anulaciones."""

    import re
    import unicodedata

    def normalizar(texto):
        texto = unicodedata.normalize("NFKD", str(texto).lower())
        return "".join(
            c for c in texto if not unicodedata.combining(c)
        )

    consulta = normalizar(pregunta)
    respuesta = normalizar(conocimiento.get("respuesta") or "")

    patron = r"\b(cancelar|cancelo|cancelacion|anular|anulo|anulacion)\b"

    if not re.search(patron, consulta):
        return {
            "estado": "sin_restriccion_especial",
            "motivo": None
        }

    if not re.search(patron, respuesta):
        return {
            "estado": "cobertura_no_confirmada",
            "motivo": (
                "La consulta solicita cancelar o anular, "
                "pero la respuesta no explica explícitamente "
                "esa operación."
            )
        }

    return {
        "estado": "requiere_validacion_semantica",
        "motivo": (
            "Se menciona la cancelación, pero todavía es "
            "necesario confirmar que existan instrucciones suficientes."
        )
    }
