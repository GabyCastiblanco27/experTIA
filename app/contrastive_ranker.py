"""Reranking léxico contrastivo para ExperTIA (solo librería estándar).

Clasifica entre los 44 conocimientos existentes comparando preguntas alternativas,
título, descripción y fragmentos de las respuestas oficiales. No genera contenido
nuevo ni consulta servicios externos. La puntuación es relativa, no probabilidad.
"""

from collections import Counter, defaultdict
from functools import lru_cache
from hashlib import sha256
from math import log, sqrt
from threading import RLock
import re

from app.normalizer import normalize, tokenize

# Configuración experimental. Mantener después de las pruebas, sin ajustar
# mediante cambios puntuales por conocimiento.
_PESOS = (0.20, 0.15, 0.10, 0.08, 0.27, 0.15, 0.05)
_PESO_COBERTURA = 0.15
_ACCIONES_EN_PRIMERA_CLAUSULA = {
    "actualizacion", "actualiza", "actualizar", "cambio", "consulta",
    "solicitud", "registro", "descarga", "ingreso", "reporte", "reportar", "validar",
}
_STOP_COBERTURA = {
    "esta", "estoy", "estan", "tengo", "quiero", "necesito", "debo", "hacer",
    "hacerlo", "puedo", "como", "cuando", "donde", "cual", "unos", "tambien",
    "porque", "para", "una", "uno", "este", "ser", "usar", "segun", "sobre",
    "pueden", "no", "si", "hay", "soy", "cuanto", "saber", "tener", "que",
    "corresponde", "registrado", "registro", "solicitud", "solicitar",
    "consulta", "consultar", "hago", "hace", "se", "lo", "pues", "debe",
}
_MUTEX = RLock()
_CACHE = {"firma": None, "modelo": None}


def _ngramas(texto):
    """N-gramas de 3 a 5 caracteres, sin cruzar límites de palabras."""
    palabras = normalize(texto).split()
    resultado = Counter()
    for palabra in palabras:
        palabra = " " + palabra + " "
        for n in (3, 4, 5):
            if len(palabra) < n:
                # sklearn char_wb permite una única muestra de palabras cortas
                resultado[palabra] += 1
            else:
                for i in range(len(palabra) - n + 1):
                    resultado[palabra[i:i+n]] += 1
    return resultado


def _fragmentos(respuesta):
    texto = re.sub(r"\bPaso\s+(\d+)\s*:", r"\nPaso \1:", respuesta or "", flags=re.I)
    partes = [p.strip() for p in re.split(
        r"(?:\n+|\s+\d+\.\s+|\s+•\s+|(?<=\.)\s+(?=[A-ZÁÉÍÓÚ]))",
        texto,
    ) if len(p.split()) >= 3]
    for i in range(len(partes)):
        for ancho in (1, 2):
            texto_fragmento = " ".join(partes[i:i+ancho])
            if len(normalize(texto_fragmento).split()) >= 3:
                yield texto_fragmento


def _cabeza(pregunta):
    cabeza = re.split(r"\bpara\b", pregunta, maxsplit=1, flags=re.I)[0]
    tokens = set(tokenize(cabeza))
    if (
        len(cabeza) < len(pregunta) and len(tokenize(cabeza)) >= 3
        and tokens & _ACCIONES_EN_PRIMERA_CLAUSULA
    ):
        return cabeza
    return pregunta


def _firma_datos(conocimientos, alternativas):
    h = sha256()
    for k in conocimientos:
        for campo in ("id", "titulo", "descripcion", "respuesta"):
            h.update(str(k.get(campo, "")).encode("utf-8"))
            h.update(b"\x00")
    for r in alternativas:
        h.update(str(r["conocimiento_id"]).encode("ascii"))
        h.update(str(r["pregunta"]).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


class _Indice:
    def __init__(self, conocimientos, alternativas):
        self.ids = [int(k["id"]) for k in conocimientos]
        # Un documento por alternativa, título, descripción y fragmento.
        documentos = []
        self.posiciones = defaultdict(lambda: defaultdict(list))
        alt_por_id = defaultdict(list)
        for r in alternativas:
            alt_por_id[int(r["conocimiento_id"])].append(r["pregunta"])
        for k in conocimientos:
            id_ = int(k["id"])
            for t in alt_por_id[id_]:
                self.posiciones[id_]["alternativas"].append(len(documentos))
                documentos.append(t)
        for k in conocimientos:
            id_ = int(k["id"])
            self.posiciones[id_]["titulo"].append(len(documentos))
            documentos.append(k.get("titulo", "") or "")
        for k in conocimientos:
            id_ = int(k["id"])
            self.posiciones[id_]["descripcion"].append(len(documentos))
            documentos.append(k.get("descripcion", "") or "")
        for k in conocimientos:
            id_ = int(k["id"])
            for frag in _fragmentos(k.get("respuesta", "") or ""):
                self.posiciones[id_]["fragmentos"].append(len(documentos))
                documentos.append(frag)
        cuentas = [_ngramas(texto) for texto in documentos]
        dfs = Counter(termino for bolsa in cuentas for termino in bolsa)
        n_docs = len(documentos)
        self.idf = {
            termino: 1.0 + log((n_docs + 1) / (df + 1))
            for termino, df in dfs.items() if df >= 2
        }
        self.postings = defaultdict(list)
        for i, bolsa in enumerate(cuentas):
            pesos = {
                termino: (1 + log(cantidad)) * self.idf[termino]
                for termino, cantidad in bolsa.items() if termino in self.idf
            }
            norma = sqrt(sum(v * v for v in pesos.values())) or 1.0
            for termino, valor in pesos.items():
                self.postings[termino].append((i, valor / norma))

        # Cobertura de términos específicos, calculada por conocimiento.
        self.palabras_base = {}
        self.palabras_respuesta = {}
        self.idf_palabras = {}
        for k in conocimientos:
            id_ = int(k["id"])
            base = " ".join([
                k.get("titulo", "") or "",
                k.get("descripcion", "") or "",
                *alt_por_id[id_]
            ])
            self.palabras_base[id_] = set(tokenize(base))
            self.palabras_respuesta[id_] = set(tokenize(k.get("respuesta", "") or ""))
        frec = Counter(t for id_ in self.ids for t in (
            self.palabras_base[id_] | self.palabras_respuesta[id_]
        ))
        self.frecuencia_palabras = frec
        self.idf_palabras = {
            t: 1 + log((len(self.ids) + 1) / (f + 1)) for t, f in frec.items()
        }
        self.n_documentos = n_docs

    def _similitudes(self, texto):
        bolsa = _ngramas(texto)
        pesos = {
            term: (1 + log(cant)) * self.idf[term]
            for term, cant in bolsa.items() if term in self.idf
        }
        norma = sqrt(sum(v * v for v in pesos.values())) or 1.0
        scores = defaultdict(float)
        for term, valor in pesos.items():
            normalizado = valor / norma
            for pos, peso in self.postings[term]:
                scores[pos] += normalizado * peso
        return scores

    def _cobertura(self, pregunta, id_):
        tokens = {t for t in tokenize(pregunta) if t not in _STOP_COBERTURA and len(t) > 2}
        if not tokens:
            return 0.0
        denom = sum(self.idf_palabras.get(t, 2.5) for t in tokens)
        conocidas = self.palabras_base[id_] | self.palabras_respuesta[id_]
        return sum(self.idf_palabras[t] for t in tokens & conocidas) / denom

    def calificar(self, pregunta, *, bonificar_solo_base=False):
        completos = self._similitudes(pregunta)
        secundarios = self._similitudes(_cabeza(pregunta))
        resultados = {}
        for id_ in self.ids:
            docs = self.posiciones[id_]
            alternativas = sorted((completos.get(pos, 0.0) for pos in docs["alternativas"]), reverse=True)
            cabeza_alt = max((secundarios.get(pos, 0.0) for pos in docs["alternativas"]), default=0.0)
            titulo_pos = docs["titulo"][0]
            descrip_pos = docs["descripcion"][0]
            fragmento = max((completos.get(pos, 0.0) for pos in docs["fragmentos"]), default=0.0)
            features = (
                alternativas[0] if alternativas else 0.0,
                sum(alternativas[:3]) / min(3, len(alternativas)) if alternativas else 0.0,
                completos.get(titulo_pos, 0.0),
                completos.get(descrip_pos, 0.0),
                fragmento,
                cabeza_alt,
                secundarios.get(titulo_pos, 0.0),
            )
            score_char = sum(a*b for a,b in zip(features, _PESOS))
            # Refuerzo limitado de identificadores poco comunes presentes en la
            # consulta y documentados en el conocimiento (ej. AX09, Workday).
            q_tokens = set(tokenize(pregunta))
            fuente_bonificacion = self.palabras_base[id_]

            if not bonificar_solo_base:
                fuente_bonificacion = (
                fuente_bonificacion | self.palabras_respuesta[id_]
            )

            raros = sum(
                 1 for t in q_tokens
                if len(t) > 2
                and self.frecuencia_palabras.get(t, 99) <= 3
                and t in fuente_bonificacion
            )

            resultados[id_] = (
                (1-_PESO_COBERTURA)*score_char
                + _PESO_COBERTURA*self._cobertura(pregunta,id_)
                + min(0.04*raros, 0.08)
            )
        return resultados

def calificar_conocimientos(
    pregunta,
    conocimientos,
    preguntas_alternativas,
    *,
    bonificar_solo_base=False,
):
    """Puntajes relativos usados para comparar candidatos.

    Por defecto conserva exactamente el comportamiento anterior.
    La opción bonificar_solo_base se reserva para el selector DEV.
    """
    firma = _firma_datos(conocimientos, preguntas_alternativas)

    with _MUTEX:
        if _CACHE["firma"] != firma:
            _CACHE["modelo"] = _Indice(
                conocimientos,
                preguntas_alternativas
            )
            _CACHE["firma"] = firma

        indice = _CACHE["modelo"]

    return indice.calificar(
        pregunta,
        bonificar_solo_base=bonificar_solo_base,
    )


def similitudes_mejores_alternativas(pregunta, conocimientos, preguntas_alternativas, ids):
    """Mejor coincidencia de pregunta alternativa por candidato, no probabilidad."""
    firma = _firma_datos(conocimientos, preguntas_alternativas)
    with _MUTEX:
        if _CACHE["firma"] != firma:
            _CACHE["modelo"] = _Indice(conocimientos, preguntas_alternativas)
            _CACHE["firma"] = firma
        indice = _CACHE["modelo"]
    similitudes = indice._similitudes(pregunta)
    return {
        int(cid): max(
            (similitudes.get(p, 0.0) for p in indice.posiciones[int(cid)]["alternativas"]),
            default=0.0,
        )
        for cid in ids
    }

