"""ExperTIA: contraste semantico general para el POST /buscar existente.

Sustituye la antigua regla 'solo ejecutar el hibrido si encontrado=False'.
No contiene reglas especiales para portatiles, cesantias ni otros temas.

IMPORTANTE: un score de similitud/reranking NO certifica cobertura. Este
modulo utiliza senales de acuerdo como criterio PROVISIONAL y, ante un
conflicto que no logra resolver, pide aclaracion en vez de dar un procedimiento
incorrecto o activar la derivacion con encontrado=False.

EXPERTIA_MODO_BUSQUEDA=tradicional -> comportamiento anterior (por defecto)
EXPERTIA_MODO_BUSQUEDA=rescate     -> contraste semantico para aciertos debiles
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from typing import Any

from app.knowledge_retriever import buscar_conocimiento

LOG = logging.getLogger(__name__)


def _solicitud_credenciales_ajenas(pregunta: str) -> bool:
    """Reconoce solicitudes explicitas de contrasenas de terceros."""
    texto = unicodedata.normalize("NFKD", pregunta.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))

    credencial = re.search(
        r"\b(?:contrasen\w*|clave(?:s)?|password(?:s)?|credencial(?:es)?)\b",
        texto,
    )
    tercero = re.search(
        r"\b(?:companero\w*|colega\w*|colaborador\w*|emplead\w*|"
        r"otra persona|otras personas|otro usuario|otra cuenta|alguien|tercero\w*)\b",
        texto,
    )
    divulgacion = re.search(
        r"\b(?:dime|decir|decirme|dame|darme|pasame|pasar|mostrar|"
        r"revelar|compartir|conocer|obtener|averiguar|consultar|"
        r"ver|saber|facilitar)\b|\bcual es\b",
        texto,
    )
    # Diferenciar consultas sobre soporte/restablecimiento de pedidos de divulgacion.
    soporte = re.search(
        r"\b(?:procedimiento|proceso|reportar|reporto|denunciar|"
        r"restablecer|resetear|cambiar|cambio|soporte)\b",
        texto,
    )
    return bool(credencial and tercero and divulgacion and not soporte)


def _proteger_credenciales_ajenas(pregunta: str) -> dict[str, Any] | None:
    if _solicitud_credenciales_ajenas(pregunta):
        return _pedir_aclaracion(
            "No puedo proporcionar contraseñas ni credenciales de otra "
            "persona. Para solicitar acceso o asistencia, utiliza los "
            "canales autorizados de soporte de TI.",
            "proteccion_credenciales_terceros",
        )
    return None


def _numero(valor: Any) -> float | None:
    try:
        n = float(valor)
        return n if __import__("math").isfinite(n) else None
    except (TypeError, ValueError):
        return None



def _aclaracion_previa(pregunta: str) -> str | None:
    """Detecta solicitudes independientes sin separar pasos relacionados."""

    texto = unicodedata.normalize("NFKD", pregunta.lower())
    texto = "".join(
        c for c in texto if not unicodedata.combining(c)
    )

    conectores = r"\b(?:y|ademas|tambien|asimismo)\b"
    partes = [
        p.strip()
        for p in re.split(conectores, texto)
        if p.strip()
    ]

    if len(partes) < 2:
        return None

    acciones = (
        r"\b(?:reportar|notificar|informar|solicitar|pedir|"
        r"descargar|obtener|consultar|buscar|registrar|crear|"
        r"actualizar|modificar|cancelar|anular|tramitar|"
        r"cambiar|retirar|generar|enviar|"
        r"cancelo|cancelarlo|anulo|anularlo|actualizo|actualizarlo|"
        r"cambio|cambiarlo|consulto|consultarlo|registro|registrarlo|"
        r"creo|crearlo|reporto|reportarlo|solicito|solicitarlo)\b"
    )

    partes_con_accion = [
        p for p in partes if re.search(acciones, p)
    ]

    if len(partes_con_accion) < 2:
        return None

    if len(partes) == 2:

        # Consultar saldo y solicitar dias de descanso:
        # dos acciones de una misma gestion de vacaciones.
        def consulta_saldo(parte):
            return bool(
                re.search(
                    r"\b(?:consulto|consultar|consulta|reviso|"
                    r"revisar|ver|veo)\b",
                    parte
                )
                and re.search(r"\bsaldo\b", parte)
                and re.search(r"\bvacaciones\b", parte)
            )

        def solicita_descanso(parte):
            return bool(
                re.search(
                    r"\b(?:solicito|solicitar|pido|pedir)\b",
                    parte
                )
                and re.search(r"\b(?:dias|dia)\b", parte)
                and re.search(r"\b(?:descanso|vacaciones)\b", parte)
            )

        if (
            consulta_saldo(partes[0])
            and solicita_descanso(partes[1])
        ) or (
            consulta_saldo(partes[1])
            and solicita_descanso(partes[0])
        ):
            return None

        # Consultar un documento y obtener su archivo asociado.
        documento = (
            r"\b(?:factura|facturas|documento|documentos|"
            r"comprobante|comprobantes)\b"
        )
        consulta = (
            r"\b(?:consultar|consulto|consulta|buscar|"
            r"revisar|reviso|ver)\b"
        )
        descarga = (
            r"^\s*(?:obtener|descargar|generar|ver|visualizar|abrir)"
            r"\s+(?:su|sus|el|la)"
            r"\s+(?:pdf|archivo|documento|comprobante)\b"
        )

        if (
            re.search(consulta, partes[0])
            and re.search(documento, partes[0])
            and re.search(descarga, partes[1])
        ):
            return None

    return (
        "Identifiqué varias solicitudes en tu mensaje. "
        "Para ayudarte correctamente, ¿cuál deseas "
        "resolver primero?"
    )




def _pedir_aclaracion(pregunta_aclaracion: str, razon: str) -> dict[str, Any]:
    """Respeta el contrato antiguo: False dispara derivacion en Teams.

    True aqui significa 'mostrar este mensaje', NO un conocimiento validado.
    Debe interpretarse como aclaracion, y en historial queda ID nulo.
    """
    cuerpo = {
        "id": None,
        "titulo": "Necesito una aclaración",
        "respuesta": pregunta_aclaracion,
        "area": None,
        "proceso": None,
        "responsable": None,
        "recursos": [],
        "confianza": 0.0,
        "detalle_ranking": {
            "estado": "requiere_aclaracion",
            "conocimiento_confirmado": False,
            "motivo": razon,
        },
    }
    return {
        "encontrado": True,
        "confianza": 0.0,
        "resultado": cuerpo,
        "requiere_aclaracion": True,
        "mensaje": pregunta_aclaracion,
    }


def _amerita_contraste(original: dict[str, Any]) -> bool:
    """Prioriza contrastar los resultados de mayor riesgo, por latencia CPU.

    Estos umbrales son criterios operativos PROVISIONALES, no calibracion
    de confianza ni garantias de calidad.
    """
    if not original.get("encontrado"):
        return True
    score = _numero(original.get("confianza"))
    if score is None:
        return True
    detalle = (original.get("resultado") or {}).get("detalle_ranking") or {}
    palabras_clave = _numero(detalle.get("keywords"))
    return score < 0.65 or (score < 0.85 and (palabras_clave is None or palabras_clave < 0.10))



def _consulta_demasiado_generica(pregunta: str) -> bool:
    """Bloquea mensajes sin tema concreto antes de recuperar un ID.

    No es un diccionario de sinónimos ni una validación completa.
    """
    texto = unicodedata.normalize("NFKD", pregunta.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    tokens = re.findall(r"[a-z0-9]+", texto)
    genericos = {
        "a", "al", "ante", "con", "como", "cual", "cuando", "de", "del",
        "donde", "el", "en", "esa", "ese", "eso", "esta", "este",
        "esos", "hacer", "hago", "hay", "informacion", "la", "las",
        "lo", "los", "me", "mi", "mis", "necesito", "para", "por",
        "puedo", "podria", "que", "quiero", "se", "si", "solicitar",
        "su", "sus", "tengo", "tu", "un", "una", "unos", "unas",
        "ver", "y", "ayuda", "ayudar", "algo", "cosa", "tema",
        "tramite", "procedimiento", "proceso", "gestion", "solicitud",
        "consulta", "consultar", "estado", "documento", "formato",
        "pendiente", "saber", "puedes", "favor", "necesitaria",
        "debo", "deseo", "hacerlo", "pedirlo", "tramitarlo",
        "reportarlo", "consultarlo", "descargarlo", "solicitarlo",
        "actualizar", "actualizo", "actualice", "actualizacion",
        "dato", "datos", "ayudas", "ayudarme",
    }
    return not any(t not in genericos and not t.startswith('ayud') for t in tokens)

def _acuerdo_semantico(h: dict[str, Any]) -> bool:
    """Confirmacion de eleccion de ID, NO verificacion de cobertura total.

    El candidato ha de ser el mejor tanto para el buscador semantico como
    para el reranker y superar filtros conservadores. No se usan sinónimos
    escritos a mano ni reglas por ID.
    """
    candidato = h.get("resultado") or {}
    detalle = h.get("detalle_ranking") or {}
    cid = candidato.get("id")
    sem = detalle.get("ids_semanticos") or []
    rer = detalle.get("top_3_reranker") or []
    if cid is None or not candidato.get("respuesta") or not sem or not rer:
        return False
    try:
        seleccionado = int(cid)
        if seleccionado != int(sem[0]) or seleccionado != int(rer[0]["id"]):
            return False
    except (TypeError, KeyError, ValueError):
        return False
    margen = _numero(detalle.get("margen_reranker_top2"))
    similitud = _numero(detalle.get("similitud_semantica_seleccionado"))
    bruto = _numero(candidato.get("score_reranker_bruto"))
    if margen is None or similitud is None or bruto is None:
        return False

    # El score del CrossEncoder NO es una probabilidad. Su diferencia
    # absoluta no es comparable entre preguntas: puede ser pequeña aun
    # cuando el primer candidato sea muy superior al segundo.
    # Conservamos el criterio previo para casos con score alto.
    camino_absoluto = (bruto >= 0.60 and margen >= 0.25
                       and similitud >= 0.83)

    # Alternativa PROVISIONAL y más estricta en similitud: el mejor debe
    # superar por >=20 veces al segundo, además de tener magnitud mínima.
    segundo = bruto - margen
    ventaja_relativa = bruto / max(segundo, 1e-6)
    camino_relativo = (
        bruto >= 0.02
        and margen >= 0.015
        and similitud >= 0.85
        and ventaja_relativa >= 20.0
    )
    return bool(camino_absoluto or camino_relativo)


def _resultado_hibrido(h: dict[str, Any]) -> dict[str, Any]:
    c = h["resultado"]
    # No usar score bruto de reranker como probabilidad de confianza.
    conocimiento = {
        "id": int(c["id"]),
        "titulo": c.get("titulo"),
        "respuesta": c.get("respuesta"),
        "area": c.get("area"),
        "proceso": c.get("proceso"),
        "responsable": c.get("responsable"),
        "recursos": c.get("recursos") or [],
        "confianza": 0.0,
        "detalle_ranking": {
            "metodo": "comparacion_semantica_provisional",
            "aviso": "Seleccion del ID con senales concordantes; cobertura no certificada",
        },
    }
    return {
        "encontrado": True,
        "confianza": 0.0,
        "resultado": conocimiento,
        "mensaje": "Candidato recuperado por contraste semantico.",
    }

def _buscar_conocimiento_asistido_base(pregunta: str) -> dict[str, Any]:
    proteccion = _proteger_credenciales_ajenas(pregunta)
    if proteccion:
        return proteccion

    aclaracion = _aclaracion_previa(pregunta)
    if aclaracion:
        return _pedir_aclaracion(aclaracion, "pregunta_ambigua_o_multiple")
    if _consulta_demasiado_generica(pregunta):
        return _pedir_aclaracion(
            "¿Sobre qué trámite o procedimiento necesitas información?",
            "pregunta_sin_tema_identificable",
        )

    if os.getenv("EXPERTIA_MODO_BUSQUEDA", "tradicional").strip().lower() != "rescate":
        return buscar_conocimiento(pregunta)

    original = buscar_conocimiento(pregunta)
    if not _amerita_contraste(original):
        return original

    from app.hybrid_retriever import buscar_conocimiento_hibrido
    # Una excepcion del modelo no se transforma en 'no encontrado':
    # se propaga como error tecnico a la API, no como derivacion.
    hibrido = buscar_conocimiento_hibrido(pregunta)
    candidato = hibrido.get("resultado") or {}
    id_hibrido = candidato.get("id")
    anterior = (original.get("resultado") or {}).get("id")

    if id_hibrido is not None and anterior is not None:
        if int(id_hibrido) == int(anterior):
            # Consenso de dos buscadores; conserva el formato/confiabilidad
            # original, aun sin demostrar cobertura total.
            return original

    if _acuerdo_semantico(hibrido):
        LOG.info("Candidato seleccionado por contraste: tradicional=%s, hibrido=%s", anterior, id_hibrido)
        return _resultado_hibrido(hibrido)

    LOG.info("Sin acuerdo suficiente: tradicional=%s, hibrido=%s", anterior, id_hibrido)
    return _pedir_aclaracion(
        "¿Puedes darme un poco más de contexto sobre el trámite o procedimiento que necesitas?",
        "conflicto_de_busqueda_sin_cobertura_confirmada",
    )




# ============================================================
# PROTECCIONES DEL RESULTADO ASISTIDO
# ============================================================

def _aplicar_protecciones_resultado(
    pregunta: str,
    resultado: dict[str, Any]
) -> dict[str, Any]:
    """
    Aplica las protecciones posteriores a una búsqueda,
    independientemente de cómo se haya obtenido el resultado.
    """

    conocimiento = resultado.get("resultado") or {}

    if not resultado.get("encontrado") or not conocimiento.get("id"):
        return resultado

    def normalizar(texto):
        texto = unicodedata.normalize(
            "NFKD",
            str(texto).lower()
        )

        return "".join(
            caracter for caracter in texto
            if not unicodedata.combining(caracter)
        )

    consulta = normalizar(pregunta)
    titulo = normalizar(conocimiento.get("titulo") or "")

    # Seguimiento de pedidos no equivale a modificarlos o cancelarlos.
    if "consulta de estado de pedidos" in titulo:

        accion_modificacion = bool(re.search(
            r"\b(?:cambi\w*|modific\w*|actualiz\w*|correg\w*)\b",
            consulta
        ))

        menciona_direccion = bool(re.search(
            r"\bdireccion\b",
            consulta
        ))

        accion_cancelacion = bool(re.search(
            r"\b(?:cancel\w*|anul\w*)\b",
            consulta
        ))

        if (
            (accion_modificacion and menciona_direccion)
            or accion_cancelacion
        ):
            return _pedir_aclaracion(
                "El procedimiento encontrado permite consultar el "
                "seguimiento del pedido, pero no contiene instrucciones "
                "confirmadas para la modificacion o cancelacion solicitada. "
                "Se requiere revision del area responsable.",
                "cobertura_insuficiente_pedidos",
            )

    from app.response_validator import verificar_cancelacion

    validacion = verificar_cancelacion(
        pregunta,
        conocimiento
    )

    if validacion["estado"] == "cobertura_no_confirmada":
        return _pedir_aclaracion(
            "Encontre informacion relacionada, pero no un "
            "procedimiento confirmado para realizar esa cancelacion "
            "o anulacion. Se requiere revision del area responsable.",
            "cancelacion_sin_cobertura_confirmada",
        )

    return resultado


# ============================================================
# BÚSQUEDA ASISTIDA TRADICIONAL
# ============================================================

def buscar_conocimiento_asistido(
    pregunta: str
) -> dict[str, Any]:

    resultado = _buscar_conocimiento_asistido_base(pregunta)

    return _aplicar_protecciones_resultado(
        pregunta,
        resultado
    )


# ============================================================
# BÚSQUEDA ASISTIDA CON RANKING COMPARTIDO
# ============================================================

def buscar_conocimiento_asistido_con_ranking(
    pregunta: str,
    limite: int = 5
) -> dict[str, Any]:
    """
    Ejecuta las validaciones preventivas, una sola evaluación
    tradicional y las protecciones posteriores.

    Devuelve:
        {
            "busqueda": resultado protegido,
            "ranking": ranking de la misma evaluación
        }
    """

    modo = os.getenv(
        "EXPERTIA_MODO_BUSQUEDA",
        "tradicional"
    ).strip().lower()

    if modo == "rescate":
        raise RuntimeError(
            "El selector unificado DEV requiere "
            "EXPERTIA_MODO_BUSQUEDA=tradicional."
        )

    # 1. Protecciones previas.
    proteccion = _proteger_credenciales_ajenas(pregunta)
    if proteccion:
        return {"busqueda": proteccion, "ranking": []}

    aclaracion = _aclaracion_previa(pregunta)

    if aclaracion:
        return {
            "busqueda": _pedir_aclaracion(
                aclaracion,
                "pregunta_ambigua_o_multiple"
            ),
            "ranking": [],
        }

    if _consulta_demasiado_generica(pregunta):
        return {
            "busqueda": _pedir_aclaracion(
                "¿Sobre qué trámite o procedimiento necesitas información?",
                "pregunta_sin_tema_identificable",
            ),
            "ranking": [],
        }

    # 2. Una sola evaluación tradicional.
    from app.knowledge_retriever import evaluar_busqueda_y_ranking

    evaluacion = evaluar_busqueda_y_ranking(
        pregunta,
        limite=limite
    )

    # 3. Las mismas protecciones posteriores del flujo original.
    evaluacion["busqueda"] = _aplicar_protecciones_resultado(
        pregunta,
        evaluacion["busqueda"]
    )

    return evaluacion
