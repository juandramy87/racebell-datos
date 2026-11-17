"""Ayuda común para la ciudad de Madrid: sus 21 distritos y 131 barrios oficiales (Ayuntamiento de Madrid) y
los nombres de zona que usan las carreras («Sanchinarro», «Las Tablas», «Vallekas», «La Elipa»…).

Muchas fichas de carreras de la capital dan como lugar el barrio y no el municipio («Hortaleza», «La Elipa»,
«Puerta Bonita», «Embajadores») o lo dejan vacío y solo lo dice el nombre («10K / 5K Sanchinarro»).
`nz.municipio_espana` no los conoce (no son municipios), así que se pierden «sin provincia».
Con esta tabla se reconocen como Madrid (municipio) / Madrid (provincia).

Algunos barrios se llaman como un municipio de otra provincia (Hellín, Salvador…) o como una palabra corriente
(Sol, Pilar, Goya, Castilla, Estrella…): esos solo valen si las coordenadas caen en el término de Madrid."""
from __future__ import annotations

import re
from typing import Optional

from nucleo import normalizar as nz

MADRID = ("Madrid", "Madrid")

DISTRITOS = (
    "Centro|Arganzuela|Retiro|Salamanca|Chamartín|Tetuán|Chamberí|Fuencarral-El Pardo|Fuencarral|El Pardo|"
    "Moncloa-Aravaca|Moncloa|Aravaca|Latina|Carabanchel|Usera|Puente de Vallecas|Moratalaz|Ciudad Lineal|"
    "Hortaleza|Villaverde|Villa de Vallecas|Vicálvaro|San Blas-Canillejas|San Blas|Canillejas|Barajas"
)

# Barrios oficiales (división de 2017) y nombres de zona habituales, sin repetir los distritos.
BARRIOS = (
    # Centro
    "Palacio|Embajadores|Cortes|Justicia|Universidad|Sol|Lavapiés|Malasaña|Chueca|La Latina|"
    # Arganzuela
    "Imperial|Acacias|Chopera|Legazpi|Delicias|Palos de Moguer|Atocha|Madrid Río|Matadero|Méndez Álvaro|"
    # Retiro
    "Pacífico|Adelfas|Estrella|Ibiza|Jerónimos|Niño Jesús|Parque del Retiro|"
    # Salamanca
    "Recoletos|Goya|Fuente del Berro|Guindalera|Lista|Castellana|"
    # Chamartín
    "El Viso|Prosperidad|Ciudad Jardín|Hispanoamérica|Nueva España|Castilla|Pinar de Chamartín|"
    # Tetuán
    "Bellas Vistas|Cuatro Caminos|Castillejos|Almenara|Valdeacederas|Berruguete|"
    # Chamberí
    "Gaztambide|Arapiles|Trafalgar|Almagro|Ríos Rosas|Vallehermoso|"
    # Fuencarral-El Pardo
    "Fuentelarreina|Peñagrande|Pilar|Barrio del Pilar|La Paz|Valverde|Mirasierra|El Goloso|Las Tablas|"
    "Montecarmelo|Tres Olivos|Arroyo del Fresno|Dehesa de la Villa|Ciudad de los Poetas|Poetas|"
    # Moncloa-Aravaca
    "Casa de Campo|Argüelles|Ciudad Universitaria|Valdezarza|Valdemarín|El Plantío|"
    # Latina
    "Los Cármenes|Puerta del Ángel|Lucero|Aluche|Campamento|Cuatro Vientos|Las Águilas|"
    # Carabanchel
    "Comillas|Opañel|San Isidro|Vista Alegre|Puerta Bonita|Buenavista|Abrantes|PAU de Carabanchel|"
    # Usera
    "Orcasitas|Orcasur|San Fermín|Almendrales|Moscardó|Zofío|Pradolongo|"
    # Puente de Vallecas
    "Entrevías|San Diego|Palomeras Bajas|Palomeras Sureste|Palomeras|Portazgo|Numancia|Vallecas|Vallekas|"
    # Moratalaz
    "Pavones|Horcajo|Marroquina|Media Legua|Fontarrón|Vinateros|"
    # Ciudad Lineal
    "Ventas|Pueblo Nuevo|Quintana|La Concepción|San Pascual|San Juan Bautista|Colina|Atalaya|Costillares|"
    "La Elipa|Elipa|Pinar de la Elipa|"
    # Hortaleza
    "Palomas|Piovera|Canillas|Pinar del Rey|Apóstol Santiago|Valdefuentes|Sanchinarro|Valdebebas|"
    "Virgen del Cortijo|Manoteras|Conde de Orgaz|Mar de Cristal|Parque Juan Carlos I|Campo de las Naciones|"
    # Villaverde
    "San Andrés|San Cristóbal|Butarque|Los Rosales|Los Ángeles|"
    # Villa de Vallecas
    "Casco Histórico de Vallecas|Santa Eugenia|Ensanche de Vallecas|Valdecarros|"
    # Vicálvaro
    "Casco Histórico de Vicálvaro|Valdebernardo|Valderrivas|El Cañaveral|"
    # San Blas-Canillejas
    "Simancas|Hellín|Amposta|Arcos|Rosas|Rejas|Salvador|"
    # Barajas
    "Alameda de Osuna|Aeropuerto|Casco Histórico de Barajas|Timón|Corralejos"
)

# Nombres que también son una palabra corriente o un municipio de otra provincia: solo con coordenadas.
_DUDOSOS = {nz.clave(n) for n in (
    "Centro|Retiro|Salamanca|Latina|Palacio|Cortes|Justicia|Universidad|Sol|Imperial|Acacias|Delicias|Atocha|"
    "Pacífico|Adelfas|Estrella|Ibiza|Recoletos|Goya|Lista|Castellana|Prosperidad|Castilla|Nueva España|"
    "Almenara|Trafalgar|Almagro|Pilar|La Paz|Valverde|El Goloso|Lucero|Campamento|Comillas|San Isidro|"
    "Vista Alegre|Buenavista|Numancia|Horcajo|Ventas|Pueblo Nuevo|Quintana|La Concepción|San Pascual|"
    "Colina|Atalaya|Palomas|Canillas|San Andrés|San Cristóbal|Los Rosales|Los Ángeles|Simancas|Hellín|"
    "Amposta|Arcos|Rosas|Rejas|Salvador|Aeropuerto|Timón|Poetas|Elipa|Matadero|Moncloa|Castillejos|"
    "Valdeacederas|Berruguete|Arapiles|San Fermín|Moscardó|Marroquina|Media Legua|Fontarrón|Vinateros|"
    "Costillares|San Diego|Portazgo|Abrantes|Opañel|Pavones|San Juan Bautista|Corralejos|Rejas|Piovera|Zofío"
).split("|")}

_NOMBRES = sorted({n for n in (DISTRITOS + "|" + BARRIOS).split("|") if n}, key=len, reverse=True)
_CLAVES = {nz.clave(n): n for n in _NOMBRES}

# Término municipal de Madrid, en grueso (incluye algo de los municipios vecinos: por eso no basta solo).
_LAT = (40.312, 40.644)
_LON = (-3.889, -3.518)


def en_termino(coords: Optional[tuple[float, float]]) -> bool:
    if not coords:
        return False
    lat, lon = coords
    return _LAT[0] <= lat <= _LAT[1] and _LON[0] <= lon <= _LON[1]


def barrio(texto: Optional[str]) -> Optional[str]:
    """El distrito o barrio de Madrid que aparece en el texto (el nombre más largo), o None.
    «10K / 5K Sanchinarro 2027» → «Sanchinarro»; «Casco Histórico de Barajas» → «Casco Histórico de Barajas»."""
    if not texto:
        return None
    k = " " + nz.clave(texto.replace("-", " ")) + " "
    for n in _NOMBRES:
        kn = nz.clave(n.replace("-", " "))
        if kn and f" {kn} " in k:
            return n
    return None


def lugar(*textos: Optional[str], coords: Optional[tuple[float, float]] = None) -> Optional[tuple[str, str]]:
    """(«Madrid», «Madrid») si alguno de los textos nombra un barrio o distrito de la capital y las coordenadas
    (si las hay) caen en el término. Sin coordenadas solo valen los nombres que no se confunden."""
    if coords and not en_termino(coords):
        return None
    for texto in textos:
        b = barrio(texto)
        if not b:
            continue
        if nz.clave(b) in _DUDOSOS and not coords:
            continue
        return MADRID
    return None


def es_de_madrid(poblacion: Optional[str]) -> bool:
    """Para comparar con otras fuentes: «Embajadores», «Puerta Bonita», «Madrid» → True."""
    if not poblacion:
        return False
    return nz.clave(poblacion) == "madrid" or nz.clave(poblacion) in _CLAVES


def palabras_slug(slug: str) -> str:
    return re.sub(r"[-_]+", " ", slug)
