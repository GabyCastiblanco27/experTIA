
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

from app.expertia_selector_pgvector_dev import (
    seleccionar as seleccionar_base,
    _resultado_rescate,
)
from app.repository import obtener_conocimientos

CONFIG = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "coberturas_hibridas_dev.json"
)


def normalizar(texto):
    texto = unicodedata.normalize(
        "NFKD", str(texto or "").lower()
    )
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    return " ".join(re.findall(r"[a-z0-9]+", texto))


def contiene(texto, frase):
    return (
        " " + normalizar(frase) + " "
        in " " + normalizar(texto) + " "
    )


def validar_regla(pregunta, conocimiento):
    try:
        datos = json.loads(
            CONFIG.read_text(encoding="utf-8-sig")
        )
        regla = datos["reglas"].get(
            str(int(conocimiento["id"]))
        )

        if not regla:
            return False

        respuesta = conocimiento.get("respuesta") or ""

        huella = hashlib.sha256(
            normalizar(respuesta).encode("utf-8")
        ).hexdigest()

        return (
            huella == regla["huella_respuesta"]
            and all(
                any(
                    contiene(pregunta, expresion)
                    for expresion in grupo
                )
                for grupo in regla["grupos"]
            )
            and not any(
                contiene(pregunta, expresion)
                for expresion in regla["excluir"]
            )
            and all(
                contiene(respuesta, evidencia)
                for evidencia in regla["evidencias"]
            )
        )

    except (OSError, ValueError, KeyError, TypeError):
        return False



# EXPERTIA_ALIAS_VIAJE_ALOJAMIENTO_V1

def _alias_viaje_alojamiento(pregunta, diagnostico):
    """Solo amplia una consulta muy concreta; nunca fuerza un ID."""
    if diagnostico.get("motivo") != "evidencia_no_concluyente":
        return None
    if diagnostico.get("tradicional_id_candidato") != 31:
        return None
    if 31 not in (diagnostico.get("vector_top3") or []):
        return None

    palabras = set(normalizar(pregunta).split())
    viaje = bool(palabras & {
        "viajar", "viaje", "viajes", "viajo", "viajando", "comision",
    })
    trabajo = bool(palabras & {
        "trabajo", "laboral", "laborales", "empresa",
        "corporativo", "corporativa", "corporativos", "corporativas",
    })
    alojamiento = bool(palabras & {
        "hotel", "hoteles", "alojamiento", "hospedaje", "hospedarme",
    })
    exclusion = bool(palabras & {
        "cancelar", "cancelacion", "anular", "reembolso", "devolucion",
        "vacaciones", "vacacional", "reclamo", "queja",
    })
    if not (viaje and trabajo and alojamiento) or exclusion:
        return None

    # Confirmar la respuesta con AMBOS motores, aplicando sus reglas actuales.
    # No se acepta un rescate experimental ni se modifica ningún umbral.
    alternativa = '¿Cómo solicito alojamiento y hotel para un viaje corporativo de trabajo?'
    resultado_alias, diag_alias = seleccionar_base(alternativa)
    conocimiento = resultado_alias.get("resultado") or {}
    if not (
        resultado_alias.get("encontrado")
        and int(conocimiento.get("id") or 0) == 31
        and diag_alias.get("tradicional_id_aceptado") == 31
        and diag_alias.get("vector_id_candidato") == 31
        and diag_alias.get("decision") == "RESPUESTA"
    ):
        return None

    diag_confirmado = {
        **diag_alias,
        "motivo": "normalizacion_contextual_viaje_alojamiento",
        "pregunta_original_preservada": True,
        "alias_contextual_aplicado": True,
        "cobertura_certificada": False,
    }
    return resultado_alias, diag_confirmado


def seleccionar(pregunta):
    resultado, diagnostico = seleccionar_base(pregunta)

    entorno = os.getenv("EXPERTIA_ENTORNO", "").strip().lower()
    reglas_habilitadas = (
        entorno == "dev"
        or (
            entorno == "prod"
            and os.getenv("EXPERTIA_HIBRIDO_REGLAS_PROD", "0") == "1"
        )
    )
    if not reglas_habilitadas:
        return resultado, diagnostico

    if os.getenv("EXPERTIA_RESCATES_CONSENSO_DEV", "0") != "0":
        return resultado, diagnostico

    if diagnostico.get("estado_vectorial") == "NO_DISPONIBLE":
        return resultado, diagnostico

    # Mantener las aclaraciones originales protegidas.
    if diagnostico.get("motivo") == "proteccion_existente":
        return resultado, diagnostico

    respuesta_alias = _alias_viaje_alojamiento(pregunta, diagnostico)
    if respuesta_alias is not None:
        return respuesta_alias

    # Permitir revisar aclaraciones provisionales del h?brido.
    if resultado.get("requiere_aclaracion"):
        if diagnostico.get("motivo") not in (
            "evidencia_no_concluyente",
            "evidencia_insuficiente",
        ):
            return resultado, diagnostico

    arbitro = diagnostico.get("arbitro_sombra") or {}
    pre = diagnostico.get("prevalidacion_consenso") or {}

    if not (
        arbitro.get("consenso_estricto") is True
        and pre.get("validaciones_tecnicas_superadas") is True
        and pre.get("id_candidato") is not None
    ):
        return resultado, diagnostico

    candidato_id = int(pre["id_candidato"])

    candidato = next(
        (
            c for c in obtener_conocimientos()
            if int(c["id"]) == candidato_id
        ),
        None,
    )

    if candidato is not None and validar_regla(pregunta, candidato):
        diag = {
            **diagnostico,
            "decision": "RESPUESTA_HIBRIDA_REGLA_DEV",
            "motivo": "consenso_y_regla_documental_acotada",
            "cobertura_certificada": False,
            "cobertura_validada_por_reglas": True,
            "pendiente_validacion_productiva": True,
        }

        respuesta = _resultado_rescate(candidato, diag)

        conocimiento = respuesta.get("resultado") or {}
        detalle = conocimiento.setdefault("detalle_ranking", {})
        detalle["metodo"] = "rescate_acotado_dev"

        return respuesta, diag

    # Desacuerdo sin cobertura suficiente:
    # no entregar un procedimiento diferente como definitivo.
    conocimiento_actual = resultado.get("resultado") or {}
    id_actual = conocimiento_actual.get("id")

    if (
        resultado.get("encontrado")
        and id_actual is not None
        and int(id_actual) != candidato_id
    ):
        diag = {
            **diagnostico,
            "decision": "ACLARACION",
            "motivo": "desacuerdo_sin_alcance_documental",
            "cobertura_certificada": False,
            "requiere_revision_humana": True,
        }

        return {
            "encontrado": False,
            "confianza": 0.0,
            "resultado": None,
            "requiere_aclaracion": True,
            "mensaje": (
                "Encontr? informaci?n relacionada, pero necesito "
                "que precises el tr?mite o documento solicitado."
            ),
        }, diag

    return resultado, diagnostico


# EXPERTIA_RESCATE_DUAL_DOCUMENTAL_V1
from app.rescate_documental_dual_dev import aplicar_rescate as _aplicar_rescate_dual_documental
_seleccionar_antes_rescate_dual_documental = seleccionar

def seleccionar(pregunta):
    resultado, diagnostico = _seleccionar_antes_rescate_dual_documental(pregunta)
    return _aplicar_rescate_dual_documental(pregunta, resultado, diagnostico)
