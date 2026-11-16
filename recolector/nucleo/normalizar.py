"""Limpieza de textos y clasificación de modalidades, común a todas las fuentes."""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

PROVINCIAS = {
    "almeria": "Almería",
    "cadiz": "Cádiz",
    "cordoba": "Córdoba",
    "granada": "Granada",
    "huelva": "Huelva",
    "jaen": "Jaén",
    "malaga": "Málaga",
    "sevilla": "Sevilla",
}


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def clave(texto: Optional[str]) -> str:
    """Texto reducido para comparar: minúsculas, sin tildes ni signos."""
    if not texto:
        return ""
    t = sin_tildes(texto).lower()
    t = re.sub(r"[^a-z0-9ñ ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def provincia(texto: Optional[str]) -> Optional[str]:
    """«MALAGA», «Málaga», «malaga » → «Málaga». Devuelve None si no es andaluza."""
    return PROVINCIAS.get(clave(texto)) if texto else None


def es_andaluza(nombre_provincia: Optional[str]) -> bool:
    return nombre_provincia in PROVINCIAS.values()


def poblacion(texto: Optional[str]) -> Optional[str]:
    """Pone en formato título las poblaciones que vienen en mayúsculas."""
    if not texto:
        return None
    t = re.sub(r"\s+", " ", texto).strip(" ,.-")
    if not t:
        return None
    if t.isupper():
        menores = {"de", "del", "la", "las", "el", "los", "y", "en"}
        palabras = t.lower().split(" ")
        t = " ".join(p if (i and p in menores) else p[:1].upper() + p[1:] for i, p in enumerate(palabras))
    return t


_ROMANO = re.compile(r"^[IVXLCDM]+[ªº]?$")
_SIGLAS = {"CXM", "KV", "UMA", "OCR", "CD", "AD", "CA", "UD", "FAA", "10K", "5K", "21K", "42K", "BTT", "UCS"}


def nombre(texto: str) -> str:
    """Quita comillas y espacios raros; si viene TODO EN MAYÚSCULAS lo pasa a formato título
    respetando números romanos y siglas («XIII CARRERA LA CORDOBARIA» → «XIII Carrera La Cordobaria»)."""
    t = re.sub(r"[“”\"«»⁠]", "", texto)
    t = re.sub(r"\s+", " ", t).strip(" -·")
    letras = [c for c in t if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) > 0.8:
        menores = {"de", "del", "la", "las", "el", "los", "y", "en", "a", "por", "con"}
        palabras = []
        for i, p in enumerate(t.split(" ")):
            limpia = p.strip(".,:;()")
            if _ROMANO.match(limpia) or limpia.upper() in _SIGLAS:
                palabras.append(p.replace("CXM", "CxM"))
            elif i and p.lower() in menores:
                palabras.append(p.lower())
            else:
                palabras.append(p[:1].upper() + p[1:].lower())
        t = " ".join(palabras)
    return t


# Pruebas que no son a pie: se descartan.
_NO_A_PIE = re.compile(
    r"(mountain ?bike|\bbtt|\bmtb|\bbike|\bbici|\bduatlon cross bike)|\b(ciclis|ciclot|gravel|cicloturis|natacion|nado|travesia|triatlon|acuatlon|"
    r"padel|tenis|futbol|baloncesto|golf|motor|moto|patinaje|piragu|remo|surf|escalada|canicross|"
    r"orientacion|senderis|senderos|nordic|marcha|ruta a pie|mushing|cicloturis|caminata|paseo|"
    r"hybrid|hibrid|hyrox)\w*",  # las carreras híbridas (fuerza + correr) no cuentan
)
_MODALIDADES = [
    ("duatlón", re.compile(r"\bduatlon")),
    ("obstáculos", re.compile(r"\b(ocr|obstaculo|obstacle|race\b.*playa|spartan)")),
    ("montaña", re.compile(r"\b(cxm|carrera(s)? (por|de) montana|kv\b|kilometro vertical|skyrace|montana)")),
    ("trail", re.compile(r"\b(trail|ultra|ecomaraton)")),
    ("cross", re.compile(r"\b(cross|campo a traves|pinares)")),
    ("pista", re.compile(r"\b(pista|encuentro de atletismo|milla)")),
    ("asfalto", re.compile(r"\b(maraton|media|10 ?k|5 ?k|urbana|popular|san silvestre|carrera|legua)")),
]


def clasificar(*textos: Optional[str]) -> tuple[bool, Optional[str]]:
    """Devuelve (es_a_pie, modalidad). Con «marcha», bici, natación… es_a_pie = False."""
    t = clave(" ".join(x for x in textos if x))
    if _NO_A_PIE.search(t) and not re.search(r"\b(cross|trail|cxm|carrera a pie|carrera y marcha|marcha y carrera)\b", t):
        return False, None
    for modalidad, patron in _MODALIDADES:
        if patron.search(t):
            return True, modalidad
    return True, None


def km_desde_metros(metros: Optional[str]) -> list[float]:
    try:
        m = float(str(metros).replace(",", "."))
    except (TypeError, ValueError):
        return []
    if m <= 0:
        return []
    return [round(m / 1000, 3)]


def distancias_del_nombre(nombre: str) -> list[float]:
    """«5Km y 10Km …» → [5, 10]; «Media Maratón» → [21.097]; «Maratón» → [42.195]."""
    t = clave(nombre)
    kms = [float(x.replace(",", ".")) for x in re.findall(r"\b(\d{1,3}(?:[.,]\d)?) ?km?\b", t)]
    if "media maraton" in t:
        kms.append(21.097)
    elif re.search(r"\bmaraton\b", t) and not re.search(r"ecomaraton|ultra ?maraton", t):
        kms.append(42.195)
    return sorted(set(kms))


PROVINCIA_POR_CP = {"04": "Almería", "11": "Cádiz", "14": "Córdoba", "18": "Granada", "21": "Huelva",
                    "23": "Jaén", "29": "Málaga", "41": "Sevilla"}


def provincia_por_cp(cp: Optional[str]) -> Optional[str]:
    return PROVINCIA_POR_CP.get((cp or "").strip()[:2]) if cp and len(cp.strip()) == 5 else None
