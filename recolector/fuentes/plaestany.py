"""Circuit de Curses Populars del Pla de l'Estany (cursesplaestany.cat, Consell Esportiu del Pla de l'Estany,
Girona): la portada lista las 6 carreras de la temporada con nombre, fecha y la página de cada una (Marxa Popular
de Banyoles, Porqueres, Fontcoberta, Camós, Run-Run de la Vall del Terri, Serinyà). Las inscripciones van por
AvaiBook Sports, enlazadas desde la página de cada carrera. robots.txt (Yoast) no prohíbe nada.

Aquí «Marxa Popular» es una carrera cronometrada del circuito (la de Banyoles son 6.600 m), no una marcha:
todas las pruebas del circuito puntúan en la clasificación, así que se aceptan aunque se llamen «marxa»."""
from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "plaestany"
URL = "https://cursesplaestany.cat/"
CIRCUIT = "Circuit de Curses Populars del Pla de l'Estany"
# «La Vall del Terri» es el nombre antiguo de Sant Miquel de Campmajor + Cornellà del Terri; la Run-Run sale de
# Cornellà del Terri.
_ALIAS = {"vall del terri": "Cornellà del Terri"}


def _municipio(nombre: str) -> Optional[tuple[str, str]]:
    k = nz.clave(nombre)
    for corto, oficial in _ALIAS.items():
        if corto in k:
            return cat.municipio(oficial)
    return cat.municipio_en(nombre)


def _km(nombre: str) -> list[float]:
    """«Marxa Popular de Banyoles – 6.600» → [6.6] (metros con punto de miles); si no, las del nombre."""
    m = re.search(r"\b(\d{1,2})\.(\d{3})\s*$", nombre)
    return [int(m.group(1)) + int(m.group(2)) / 1000] if m else cat.distancias(nombre)


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for item in sopa.select(".edgtf-linked-item"):
        titulo = item.select_one(".edgtf-section-subtitle")
        cuando = item.select_one(".edgtf-section-title")
        enlace = item.select_one("a.edgtf-linked-item-link")
        if not (titulo and cuando and enlace and enlace.get("href")):
            continue
        url = enlace["href"]
        if url in vistas:
            continue
        vistas.add(url)
        nombre = nz.nombre(cat.texto(titulo.get_text(" ", strip=True)))
        fecha = cat.fecha(cat.texto(cuando.get_text(" ", strip=True)))
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        a_pie, modalidad = cat.clasificar(nombre)
        if not a_pie and re.search(r"\bmarxa (popular|solidaria)\b", nz.clave(nombre)):
            a_pie, modalidad = True, "asfalto"  # prueba cronometrada del circuito (ver arriba)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        if cat.es_infantil(nombre):
            descartes.append(f"infantil: {nombre}")
            continue
        oficial = _municipio(nombre)
        if not oficial:
            descartes.append(f"sin municipio: {nombre}")
            continue
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, url),
            poblacion=oficial[0],
            provincia=oficial[1],
            modalidad=modalidad,
            distancias_km=_km(nombre),
            url_inscripcion=url,
        )
        c.previos.append(f"Puntúa en: {CIRCUIT}")  # la foto de la tarjeta es de archivo, no el cartel
        c.marcar("Cierre de inscripción en la página de la carrera (AvaiBook Sports)", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
