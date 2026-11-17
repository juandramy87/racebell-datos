"""Cronoline Canarias (Cronoline Eventos, Lanzarote y Fuerteventura; algo de La Palma): `cronolinecanarias.com/eventos/`
lista sus pruebas con nombre, fecha («12 diciembre, 2026»), modalidad (clase `event-modality-running|trail|…`) y
enlace a la ficha; las próximas van primero (clase `status-future`). Inscribe en RaceResult o en la web de cada
carrera. No da el lugar: se saca del nombre (municipio o localidad conocida de las islas) y, si no sale, la
prueba se descarta. robots.txt: no tiene (404). Las fichas casi no traen datos, así que no se abren."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente, PENDIENTE_CARTEL

ID = "cronoline"
URL = "https://www.cronolinecanarias.com/eventos/"
_CANARIAS = {"Las Palmas", "Santa Cruz de Tenerife"}
_MESES = {m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                      "septiembre", "octubre", "noviembre", "diciembre"], 1)}
_FECHA = re.compile(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})")
_NO_A_PIE = {"ciclismo", "duatlon", "mountain-bike", "natacion", "socios", "triatlon"}
_MODALIDAD = {"trail": "trail", "running": None}
# Localidades que no son municipio (para sacar el municipio del nombre de la prueba).
_LOCALIDADES = {
    "corralejo": ("Corralejo", "La Oliva"), "costa teguise": ("Costa Teguise", "Teguise"),
    "playa blanca": ("Playa Blanca", "Yaiza"), "puerto del carmen": ("Puerto del Carmen", "Tías"),
    "el islote": ("El Islote", "San Bartolomé"), "munique": ("Muñique", "Teguise"),
    "caleta de fuste": ("Caleta de Fuste", "Antigua"), "morro jable": ("Morro Jable", "Pájara"),
    "gran tarajal": ("Gran Tarajal", "Tuineje"), "la vegueta": ("La Vegueta", "Tinajo"),
}


def _lugar(nombre: str) -> Optional[tuple[str, str]]:
    """(población, provincia) a partir del nombre, solo si es de Canarias."""
    t = nz.clave(nombre)
    for clave_loc, (pob, municipio) in _LOCALIDADES.items():
        if re.search(rf"\b{clave_loc}\b", t):
            hallado = nz.municipio_espana(municipio)
            if hallado and hallado[1] in _CANARIAS:
                return pob, hallado[1]
    palabras = nombre.split()
    # Prueba con grupos de 1 a 3 palabras seguidas («Puerto del Rosario», «San Bartolomé», «Haría»).
    for n in (3, 2, 1):
        for i in range(len(palabras) - n + 1):
            trozo = " ".join(palabras[i:i + n])
            hallado = nz.municipio_espana(trozo)
            if hallado and hallado[1] in _CANARIAS and len(nz.clave(trozo)) > 3:
                return hallado
    return None


def leer(contenido: bytes | str, *, hoy: Optional[date] = None) -> tuple[list[Carrera], list[str]]:
    hoy = hoy or date.today()
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for art in sopa.select("article.type-event"):
        titulo = art.select_one(".entry-title a")
        fecha_el = art.select_one(".start_date")
        if not (titulo and fecha_el):
            continue
        nombre = nz.nombre(titulo.get_text(" ", strip=True))
        m = _FECHA.search(nz.clave(fecha_el.get_text(" ", strip=True)))
        if not m or m.group(2) not in _MESES:
            descartes.append(f"sin fecha clara: {nombre}")
            continue
        fecha = date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
        if fecha < hoy:
            continue
        clases = art.get("class", [])
        modalidades = {c.removeprefix("event-modality-") for c in clases if c.startswith("event-modality-")}
        if modalidades & _NO_A_PIE:
            descartes.append(f"no es a pie: {nombre} ({', '.join(sorted(modalidades))})")
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        if re.search(r"\bcopa\b|\bcircuito\b|\bliga\b", nz.clave(nombre)):
            descartes.append(f"circuito, no una carrera: {nombre}")
            continue
        lugar = _lugar(nombre)
        if not lugar:
            descartes.append(f"sin lugar en el nombre: {nombre}")
            continue
        ver = art.select_one("a.link_event_view")
        url = ver["href"] if ver else titulo["href"]
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, url),
            poblacion=lugar[0],
            provincia=lugar[1],
            modalidad=modalidad or next((_MODALIDAD[x] for x in modalidades if _MODALIDAD.get(x)), None),
            distancias_km=nz.distancias_del_nombre(nombre),
        )
        c.marcar("Hora, distancias e inscripción en la web de la carrera", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
