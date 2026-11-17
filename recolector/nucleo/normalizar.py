"""Limpieza de textos y clasificación de modalidades, común a todas las fuentes."""
from __future__ import annotations

import html
import re
import unicodedata
from typing import Optional

# Las 52 provincias: nombre → (comunidad, prefijo de código postal, otras formas de escribirla).
_TABLA = {
    "Almería": ("andalucia", "04", ()), "Cádiz": ("andalucia", "11", ()), "Córdoba": ("andalucia", "14", ()),
    "Granada": ("andalucia", "18", ()), "Huelva": ("andalucia", "21", ()), "Jaén": ("andalucia", "23", ()),
    "Málaga": ("andalucia", "29", ()), "Sevilla": ("andalucia", "41", ()),
    "Huesca": ("aragon", "22", ("osca",)), "Teruel": ("aragon", "44", ()), "Zaragoza": ("aragon", "50", ()),
    "Asturias": ("asturias", "33", ("principado de asturias",)),
    "Baleares": ("baleares", "07", ("illes balears", "islas baleares", "balears", "illes balears baleares")),
    "Las Palmas": ("canarias", "35", ("palmas",)),
    "Santa Cruz de Tenerife": ("canarias", "38", ("s c tenerife", "sc tenerife", "santa cruz tenerife")),
    "Cantabria": ("cantabria", "39", ()),
    "Albacete": ("castilla-la-mancha", "02", ()), "Ciudad Real": ("castilla-la-mancha", "13", ()),
    "Cuenca": ("castilla-la-mancha", "16", ()), "Guadalajara": ("castilla-la-mancha", "19", ()),
    "Toledo": ("castilla-la-mancha", "45", ()),
    "Ávila": ("castilla-y-leon", "05", ()), "Burgos": ("castilla-y-leon", "09", ()), "León": ("castilla-y-leon", "24", ()),
    "Palencia": ("castilla-y-leon", "34", ()), "Salamanca": ("castilla-y-leon", "37", ()),
    "Segovia": ("castilla-y-leon", "40", ()), "Soria": ("castilla-y-leon", "42", ()),
    "Valladolid": ("castilla-y-leon", "47", ()), "Zamora": ("castilla-y-leon", "49", ()),
    "Barcelona": ("cataluna", "08", ()), "Girona": ("cataluna", "17", ("gerona",)),
    "Lleida": ("cataluna", "25", ("lerida",)), "Tarragona": ("cataluna", "43", ()),
    "Alicante": ("valenciana", "03", ("alacant", "alicante alacant", "alacant alicante")),
    "Castellón": ("valenciana", "12", ("castello", "castellon de la plana", "castello de la plana", "castellon castello")),
    "Valencia": ("valenciana", "46", ("valencia valencia", "valencia valencia valencia")),
    "Badajoz": ("extremadura", "06", ()), "Cáceres": ("extremadura", "10", ()),
    "A Coruña": ("galicia", "15", ("la coruna", "coruna")), "Lugo": ("galicia", "27", ()),
    "Ourense": ("galicia", "32", ("orense",)), "Pontevedra": ("galicia", "36", ()),
    "Madrid": ("madrid", "28", ("comunidad de madrid",)),
    "Murcia": ("murcia", "30", ("region de murcia",)),
    "Navarra": ("navarra", "31", ("nafarroa", "comunidad foral de navarra")),
    "Álava": ("pais-vasco", "01", ("araba", "alava araba", "araba alava")),
    "Gipuzkoa": ("pais-vasco", "20", ("guipuzcoa",)),
    "Bizkaia": ("pais-vasco", "48", ("vizcaya",)),
    "La Rioja": ("la-rioja", "26", ("rioja",)),
    "Ceuta": ("ceuta", "51", ()), "Melilla": ("melilla", "52", ()),
}
COMUNIDAD = {p: c for p, (c, _, _) in _TABLA.items()}
PROVINCIA_POR_CP = {cp: p for p, (_, cp, _) in _TABLA.items()}


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def clave(texto: Optional[str]) -> str:
    """Texto reducido para comparar: minúsculas, sin tildes ni signos."""
    if not texto:
        return ""
    t = sin_tildes(texto).lower()
    t = re.sub(r"[^a-z0-9ñ ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# clave → provincia (nombre oficial y variantes).
PROVINCIAS = {clave(v): p for p, (_, _, otras) in _TABLA.items() for v in (p, *otras)}


def provincia(texto: Optional[str]) -> Optional[str]:
    """«MALAGA», «Málaga», «Vizcaya», «Illes Balears» → nombre de la provincia. None si no es una provincia española."""
    return PROVINCIAS.get(clave(texto)) if texto else None


def comunidad(nombre_provincia: Optional[str]) -> Optional[str]:
    """Identificador de la comunidad autónoma («andalucia», «cataluna», «valenciana»…) de una provincia."""
    return COMUNIDAD.get(nombre_provincia or "")


def es_andaluza(nombre_provincia: Optional[str]) -> bool:
    return comunidad(nombre_provincia) == "andalucia"


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
    t = re.sub(r"[“”\"«»⁠]", "", html.unescape(texto))
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


# Pruebas que no son a pie: se descartan. Las de _NUNCA_A_PIE aunque digan «cross» o «trail» (duatlón cross: hay bici).
_NUNCA_A_PIE = re.compile(r"\b(duatlon|duathlon|triatlon|boulder|escalada)\w*")
_NO_A_PIE = re.compile(
    r"(mountain ?bike|\bbtt|\bmtb|\bbike|\bbici|\bduatlon cross bike)|\b(ciclis|ciclot|gravel|cicloturis|natacion|nado|travesia|triatlon|acuatlon|"
    r"padel|tenis|futbol|baloncesto|golf|motor|moto|patinaje|piragu|remo|surf|escalada|canicross|"
    r"orientacion|senderis|senderos|nordic|marcha|ruta a pie|mushing|cicloturis|caminata|paseo|"
    r"hybrid|hibrid|hyrox)\w*",  # las carreras híbridas (fuerza + correr) no cuentan
)
_MODALIDADES = [
    ("obstáculos", re.compile(r"\b(ocr|obstaculo|obstacle|race\b.*playa|spartan)")),
    ("montaña", re.compile(r"\b(cxm|carrera(s)? (por|de) montana|kv\b|kilometro vertical|skyrace|montana)")),
    ("trail", re.compile(r"\b(trail|ultra|ecomaraton)")),
    ("cross", re.compile(r"\b(cross|campo a traves|pinares)")),
    ("pista", re.compile(r"\b(pista|encuentro de atletismo|milla)(?! (y|urbana|popular))")),
    ("asfalto", re.compile(r"\b(maraton|media|10 ?k|5 ?k|urbana|popular|san silvestre|carrera|legua)")),
]


def clasificar(*textos: Optional[str]) -> tuple[bool, Optional[str]]:
    """Devuelve (es_a_pie, modalidad). Con «marcha», bici, natación… es_a_pie = False."""
    t = clave(" ".join(x for x in textos if x))
    if _NUNCA_A_PIE.search(t):
        return False, None
    if re.search(r"\b(bike|btt|mtb|bici\w*|crossfit|throwdown)\b", t):  # «Trail Bike», «crossfit»: nunca a pie
        return False, None
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
    if re.search(r"\b(media|medio|mitja|mitja) maraton|\bmitja marato\b|\bmeia maratona\b", t):
        kms.append(21.097)
    elif re.search(r"\b(maraton|marato)\b", t) and not re.search(r"ecomaraton|ultra ?maraton", t):
        kms.append(42.195)
    return sorted(set(kms))



def provincia_por_cp(cp: Optional[str]) -> Optional[str]:
    return PROVINCIA_POR_CP.get((cp or "").strip()[:2]) if cp and len(cp.strip()) == 5 else None


# Municipios de toda España (INE, 1/1/2026) → provincia. Solo vale si el nombre es único en España.
_MUNICIPIOS_ESPANA: Optional[dict[str, Optional[tuple[str, str]]]] = None


def _indice_espana() -> dict[str, Optional[tuple[str, str]]]:
    global _MUNICIPIOS_ESPANA
    if _MUNICIPIOS_ESPANA is None:
        import json
        from pathlib import Path
        ruta = Path(__file__).resolve().parents[1] / "datos" / "municipios-espana.json"
        indice: dict[str, Optional[tuple[str, str]]] = {}
        for prov, nombres in json.loads(ruta.read_text()).items():
            for n in nombres:
                k = clave(n)
                n = n[:1].upper() + n[1:]  # «l'Alfàs del Pi» → «L'Alfàs del Pi», «el Campello» → «El Campello»
                previo = indice.get(k, (n, prov))
                indice[k] = (n, prov) if previo and previo[1] == prov else None  # en dos provincias: no vale
        _MUNICIPIOS_ESPANA = indice
    return _MUNICIPIOS_ESPANA


def municipio_espana(texto: Optional[str]) -> Optional[tuple[str, str]]:
    """«BILBAO» → («Bilbao», «Bizkaia»); «Pl. de España, Fonelas» → («Fonelas», «Granada»). None si no está o si
    hay pueblos iguales en varias provincias."""
    if not texto:
        return None
    indice = _indice_espana()
    for p in [texto] + [p for p in re.split(r"[,(\-–]", texto)[::-1] if p.strip()]:
        hallado = indice.get(clave(p))
        if hallado:
            return hallado
    return None


def provincia_de_municipio(texto: Optional[str]) -> Optional[str]:
    hallado = municipio_espana(texto)
    return hallado[1] if hallado else None
