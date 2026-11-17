"""Federación Extremeña de Atletismo (FAEX): «Calendario y resultados» (`atletismo-ext.com/es/calendario-NNN/AAAA`,
el número cambia cada año: se busca en el menú de la portada). Tabla HTML paginada (`?pagina=N`) con fecha,
nombre y sede; no trae tipo de prueba ni provincia. Se quitan controles, jornadas de liga, Judex, pista y
campeonatos de España (son fuera); la provincia sale de la sede (tabla de los 388 municipios de Extremadura,
de Wikipedia, más algunas pedanías). Lo que no está en la tabla (Atapuerca, Castro Urdiales…) se descarta.
robots.txt: permite /es/; prohíbe /upload/, /index.php, /?s y otras rutas que no se usan."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "faex"
WEB = "https://www.atletismo-ext.com/"
URL = WEB  # la portada: de su menú salen los calendarios de cada año
MAX_PAGINAS = 10
_NO_POPULAR = re.compile(
    r"^([ivxl]+\s+)?(jornada|control|liga)\b|\bjudex\b|campeonato de espana|\bpista\b|lanzamientos|short track|"
    r"copa de clubes|seleccion diputacion|\bmaster de invierno\b")

# Municipios de Extremadura por provincia (Wikipedia, «Anexo:Municipios de la provincia de …», 11/2026).
_MUNICIPIOS = {
    "Badajoz": (
        "Acedera|Aceuchal|Ahillones|Alange|La Albuera|Alburquerque|Alconchel|Alconera|Aljucén|Almendral|"
        "Almendralejo|Arroyo de San Serván|Atalaya|Azuaga|Badajoz|Barcarrota|Baterno|Benquerencia de la Serena|"
        "Berlanga|Bienvenida|Bodonal de la Sierra|Burguillos del Cerro|Cabeza del Buey|Cabeza la Vaca|Calamonte|"
        "Calera de León|Calzadilla de los Barros|Campanario|Campillo de Llerena|Capilla|Carmonita|El Carrascalejo|"
        "Casas de Don Pedro|Casas de Reina|Castilblanco|Castuera|Cheles|La Codosera|Cordobilla de Lácara|"
        "La Coronada|Corte de Peleas|Cristina|Don Álvaro|Don Benito|Entrín Bajo|Esparragalejo|"
        "Esparragosa de la Serena|Esparragosa de Lares|Feria|Fregenal de la Sierra|Fuenlabrada de los Montes|"
        "Fuente de Cantos|Fuente del Arco|Fuente del Maestre|Fuentes de León|Garbayuela|Garlitos|La Garrovilla|"
        "Granja de Torrehermosa|Guadiana|Guareña|La Haba|Helechosa de los Montes|Herrera del Duque|"
        "Higuera de la Serena|Higuera de Llerena|Higuera de Vargas|Higuera la Real|Hinojosa del Valle|Hornachos|"
        "Jerez de los Caballeros|La Lapa|Llera|Llerena|Lobón|Magacela|Maguilla|Malcocinado|"
        "Malpartida de la Serena|Manchita|Medellín|Medina de las Torres|Mengabril|Mérida|Mirandilla|Monesterio|"
        "Montemolín|Monterrubio de la Serena|Montijo|La Morera|La Nava de Santiago|Navalvillar de Pela|Nogales|"
        "Oliva de la Frontera|Oliva de Mérida|Olivenza|Orellana de la Sierra|Orellana la Vieja|Palomas|La Parra|"
        "Peñalsordo|Peraleda del Zaucejo|Puebla de Alcocer|Puebla de la Calzada|Puebla de la Reina|"
        "Puebla de Obando|Puebla de Sancho Pérez|Puebla del Maestre|Puebla del Prior|Pueblonuevo del Guadiana|"
        "Quintana de la Serena|Reina|Rena|Retamal de Llerena|Ribera del Fresno|Risco|La Roca de la Sierra|"
        "Salvaleón|Salvatierra de los Barros|San Pedro de Mérida|San Vicente de Alcántara|Sancti-Spíritus|"
        "Santa Amalia|Santa Marta|Los Santos de Maimona|Segura de León|Siruela|Solana de los Barros|Talarrubias|"
        "Talavera la Real|Táliga|Tamurejo|Torre de Miguel Sesmero|Torremayor|Torremejía|Trasierra|Trujillanos|"
        "Usagre|Valdecaballeros|Valdelacalzada|Valdetorres|Valencia de las Torres|Valencia del Mombuey|"
        "Valencia del Ventoso|Valle de la Serena|Valle de Matamoros|Valle de Santa Ana|Valverde de Burguillos|"
        "Valverde de Leganés|Valverde de Llerena|Valverde de Mérida|Villafranca de los Barros|"
        "Villagarcía de la Torre|Villagonzalo|Villalba de los Barros|Villanueva de la Serena|"
        "Villanueva del Fresno|Villar de Rena|Villar del Rey|Villarta de los Montes|Zafra|Zahínos|"
        "Zalamea de la Serena|La Zarza|Zarza Capilla"
    ),
    "Cáceres": (
        "Abadía|Abertura|Acebo|Acehúche|Aceituna|Ahigal|Alagón del Río|Albalá|Alcántara|Alcollarín|Alcuéscar|"
        "Aldea del Cano|La Aldea del Obispo|Aldeacentenera|Aldeanueva de la Vera|Aldeanueva del Camino|"
        "Aldehuela del Jerte|Alía|Aliseda|Almaraz|Almoharín|Arroyo de la Luz|Arroyomolinos|"
        "Arroyomolinos de la Vera|Baños de Montemayor|Barrado|Belvís de Monroy|Benquerencia|Berrocalejo|Berzocana|"
        "Bohonal de Ibor|Botija|Brozas|Cabañas del Castillo|Cabezabellosa|Cabezuela del Valle|Cabrero|Cáceres|"
        "Cachorrilla|Cadalso|Calzadilla|Caminomorisco|Campillo de Deleitosa|Campo Lugar|Cañamero|Cañaveral|"
        "Carbajo|Carcaboso|Carrascalejo|Casar de Cáceres|Casar de Palomero|Casares de las Hurdes|"
        "Casas de Don Antonio|Casas de Don Gómez|Casas de Millán|Casas de Miravete|Casas del Castañar|"
        "Casas del Monte|Casatejada|Casillas de Coria|Castañar de Ibor|Ceclavín|Cedillo|Cerezo|Cilleros|"
        "Collado de la Vera|Conquista de la Sierra|Coria|Cuacos de Yuste|La Cumbre|Deleitosa|Descargamaría|Eljas|"
        "Escurial|Fresnedoso de Ibor|Galisteo|Garciaz|Garganta la Olla|La Garganta|Gargantilla|Gargüera|"
        "Garrovillas de Alconétar|Garvín|Gata|El Gordo|La Granja|Guadalupe|Guijo de Coria|Guijo de Galisteo|"
        "Guijo de Granadilla|Guijo de Santa Bárbara|Herguijuela|Hernán-Pérez|Herrera de Alcántara|Herreruela|"
        "Hervás|Higuera de Albalat|Hinojal|Holguera|Hoyos|Huélaga|Ibahernando|Jaraicejo|Jaraíz de la Vera|"
        "Jarandilla de la Vera|Jarilla|Jerte|Ladrillar|Logrosán|Losar de la Vera|Madrigal de la Vera|Madrigalejo|"
        "Madroñera|Majadas|Malpartida de Cáceres|Malpartida de Plasencia|Marchagaz|Mata de Alcántara|Membrío|"
        "Mesas de Ibor|Miajadas|Millanes|Mirabel|Mohedas de Granadilla|Monroy|Montánchez|Montehermoso|Moraleja|"
        "Morcillo|Navaconcejo|Navalmoral de la Mata|Navalvillar de Ibor|Navas del Madroño|Navezuelas|Nuñomoral|"
        "Oliva de Plasencia|Palomero|Pasarón de la Vera|Pedroso de Acim|Peraleda de la Mata|Peraleda de San Román|"
        "Perales del Puerto|Pescueza|La Pesga|Piedras Albas|Pinofranqueado|Piornal|Plasencia|Plasenzuela|Portaje|"
        "Portezuelo|Pozuelo de Zarzón|Pueblonuevo de Miramontes|Puerto de Santa Cruz|Rebollar|Riolobos|"
        "Robledillo de Gata|Robledillo de la Vera|Robledillo de Trujillo|Robledollano|Romangordo|Rosalejo|Ruanes|"
        "Salorino|Salvatierra de Santiago|San Martín de Trevejo|Santa Ana|Santa Cruz de la Sierra|"
        "Santa Cruz de Paniagua|Santa Marta de Magasca|Santiago de Alcántara|Santiago del Campo|"
        "Santibáñez el Alto|Santibáñez el Bajo|Saucedilla|Segura de Toro|Serradilla|Serrejón|Sierra de Fuentes|"
        "Talaván|Talaveruela de la Vera|Talayuela|Tejeda de Tiétar|Tiétar|Toril|Tornavacas|El Torno|"
        "Torre de Don Miguel|Torre de Santa María|Torrecilla de los Ángeles|Torrecillas de la Tiesa|"
        "Torrejón el Rubio|Torrejoncillo|Torremenga|Torremocha|Torreorgaz|Torrequemada|Trujillo|Valdastillas|"
        "Valdecañas de Tajo|Valdefuentes|Valdehúncar|Valdelacasa de Tajo|Valdemorales|Valdeobispo|"
        "Valencia de Alcántara|Valverde de la Vera|Valverde del Fresno|Vegaviana|Viandar de la Vera|"
        "Villa del Campo|Villa del Rey|Villamesías|Villamiel|Villanueva de la Sierra|Villanueva de la Vera|"
        "Villar de Plasencia|Villar del Pedroso|Villasbuenas de Gata|Zarza de Granadilla|Zarza de Montánchez|"
        "Zarza la Mayor|Zorita"
    ),}
# Pedanías y entidades locales que la FAEX pone como sede.
_PEDANIAS = {"barbano": ("Barbaño", "Badajoz"), "lacara": ("Lácara", "Badajoz"), "guadajira": ("Guadajira", "Badajoz"),
             "regina": ("Regina", "Badajoz"), "santa marta de los barros": ("Santa Marta de los Barros", "Badajoz"),
             "valdelacalzada": ("Valdelacalzada", "Badajoz"),
             "pueblonuevo": ("Pueblonuevo del Guadiana", "Badajoz"), "vegas altas": ("Vegas Altas", "Badajoz"),
             "rosalejo": ("Rosalejo", "Cáceres"), "tietar": ("Tiétar", "Cáceres"), "alagon": ("Alagón del Río", "Cáceres")}
_TABLA = {nz.clave(m): (m, p) for p, nombres in _MUNICIPIOS.items() for m in nombres.split("|")} | _PEDANIAS


def municipio(sede: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """(municipio, provincia) de la sede; (None, None) si no es de Extremadura."""
    t = nz.clave(re.sub(r"\(.*?\)", "", sede or "")).strip()
    if t in _TABLA:
        return _TABLA[t]
    # «La Garrovilla» / «Garrovilla, La»
    sin_articulo = re.sub(r"^(la|el|los|las) ", "", t)
    for k, v in _TABLA.items():
        if re.sub(r"^(la|el|los|las) ", "", k) == sin_articulo:
            return v
    return None, None


def calendarios(portada: bytes | str, hoy: date) -> list[str]:
    """URLs del calendario de este año y del siguiente (si ya existe)."""
    html = portada.decode("utf-8", "replace") if isinstance(portada, bytes) else portada
    años = {int(a): ruta for ruta, a in re.findall(r'href="(/es/calendario-\d+/(\d{4}))"', html)}
    return [urljoin(WEB, años[a]) for a in (hoy.year, hoy.year + 1) if a in años]


def otras_paginas(primera: bytes | str, url: str) -> list[str]:
    html = primera.decode("utf-8", "replace") if isinstance(primera, bytes) else primera
    numeros = sorted({int(n) for n in re.findall(r"\?pagina=(\d+)", html)} - {1})
    return [f"{url}?pagina={n}" for n in numeros[:MAX_PAGINAS - 1]]


def bajar_paginas(bajar, hoy: date) -> list[bytes]:
    paginas = []
    for url in calendarios(bajar(URL), hoy):
        primera = bajar(url)
        paginas.append(primera)
        paginas.extend(bajar(u) for u in otras_paginas(primera, url))
    return paginas


def leer(paginas: list[bytes | str]) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for pagina in paginas:
        sopa = BeautifulSoup(pagina, "html.parser")
        for fila in sopa.select("tbody tr"):
            celdas = fila.find_all("td")
            enlace = fila.find("a", href=True)
            if len(celdas) < 3:
                continue
            m = re.search(r"(\d{2}/\d{2}/\d{4})", celdas[0].get_text(" ", strip=True))
            nombre = nz.nombre(celdas[1].get_text(" ", strip=True))
            sede = celdas[2].get_text(" ", strip=True)
            url = urljoin(WEB, enlace["href"]) if enlace else None
            if not m or not nombre or (url or nombre) in vistas:
                continue
            vistas.add(url or nombre)
            if "Del " in celdas[0].get_text():
                descartes.append(f"varios días (campeonato, no popular): {nombre}")
                continue
            if _NO_POPULAR.search(nz.clave(nombre)):
                descartes.append(f"competición federada, no popular: {nombre}")
                continue
            a_pie, modalidad = nz.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            poblacion, provincia = municipio(sede)
            if not provincia:
                descartes.append(f"sede fuera de Extremadura o desconocida: {nombre} ({sede})")
                continue
            c = Carrera(nombre=nombre, fecha=datetime.strptime(m.group(1), "%d/%m/%Y").date(),
                        fuente=Fuente(ID, url or URL), poblacion=poblacion, provincia=provincia,
                        modalidad=modalidad or "asfalto",
                        distancias_km=nz.distancias_del_nombre(re.sub(r"(?i)medio marat", "Media Marat", nombre)))
            c.marcar("Hora y cierre de inscripción en el reglamento de la FAEX", "pendiente_cartel")
            carreras.append(c)
    return carreras, descartes
