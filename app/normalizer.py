import re
import unicodedata


# Palabras que normalmente no aportan mucho a la búsqueda.
PALABRAS_VACIAS = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "de",
    "del",
    "al",
    "a",
    "en",
    "por",
    "para",
    "con",
    "y",
    "o",
    "que",
    "como",
    "cual",
    "cuales",
    "es",
    "son",
    "mi",
    "mis",
    "me",
    "te",
    "se",
    "puedo",
    "puede",
}


def quitar_tildes(texto):
    """
    Convierte:
    cesantías -> cesantias
    nómina -> nomina
    información -> informacion
    """

    texto = unicodedata.normalize("NFD", texto)

    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def normalizar_texto(texto):
    """
    Normaliza una pregunta del usuario.
    """

    if not texto:
        return ""

    # Convertir a minúsculas
    texto = texto.lower()

    # Quitar tildes
    texto = quitar_tildes(texto)

    # Reemplazar caracteres especiales por espacios
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)

    # Eliminar espacios repetidos
    texto = re.sub(r"\s+", " ", texto)

    # Quitar espacios al inicio y final
    texto = texto.strip()

    return texto


def obtener_palabras(texto):
    """
    Convierte un texto en una lista de palabras
    relevantes para la búsqueda.
    """

    texto_normalizado = normalizar_texto(texto)

    palabras = texto_normalizado.split()

    palabras_relevantes = [
        palabra
        for palabra in palabras
        if palabra not in PALABRAS_VACIAS
    ]

    return palabras_relevantes