"""Timing Lap / Inscripciones Deportivas (Corredor del Henares y norte de Madrid: Torrejón, San Fernando, Alcalá,
Daganzo, Valdetorres…). Es una marca blanca de AvaiBook Sports: el listado
`inscripcionesdeportivas.timinglap.com/inscripcion/inscripciones-deportivas-online/listado-eventos-deportivos/`
(el que pinta el iframe de inscripcionesdeportivas.com) trae, como el de Tecnocrono, bloques schema.org
SportsEvent con fecha y hora, «28850 Torrejón de Ardoz (Madrid)», coordenadas, especialidad y
«Inscripciones abiertas desde … hasta …». Se reutiliza `tecnocrono.leer` y se cambia la fuente.
robots.txt: el de AvaiBook (prohíbe zonas privadas, diplomas, dorsales y `/ajax/`; el listado se puede leer)."""
from __future__ import annotations

from bs4 import BeautifulSoup

from fuentes import tecnocrono
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "timinglap"
URL = ("https://inscripcionesdeportivas.timinglap.com/inscripcion/inscripciones-deportivas-online/"
       "listado-eventos-deportivos/")


def _enlaces(contenido: bytes | str) -> dict[str, str]:
    """Nombre de la prueba → enlace de su ficha (el `<a class="nombre">` lleva dos `class` y bs4 se queda con
    la segunda, así que se usa el botón `itemprop="url"`)."""
    sopa = BeautifulSoup(contenido, "html.parser")
    enlaces = {}
    for ev in sopa.find_all(attrs={"itemtype": "https://schema.org/SportsEvent"}):
        nombre = ev.find(attrs={"itemprop": "name"})
        boton = ev.find("a", attrs={"itemprop": "url"}, href=True)
        if nombre and boton:
            texto = nombre.get("content") or nombre.get_text(" ", strip=True)
            enlaces[nz.nombre(texto)] = boton["href"]
    return enlaces


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = tecnocrono.leer(contenido)
    enlaces = _enlaces(contenido)
    for c in carreras:
        url = enlaces.get(c.nombre, URL)
        c.fuente = Fuente(ID, url)
        c.url_inscripcion = url
    return carreras, descartes
