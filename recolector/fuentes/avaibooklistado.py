"""Ayuda común para los listados por organizador de AvaiBook Sports
(`avaibooksports.com/listado-<organizador>.php`): el mismo HTML con datos schema.org SportsEvent que lee
`fuentes/tecnocrono.py`, con «Inscripciones abiertas desde … hasta …» (cierre exacto), lugar «CP Municipio
(Provincia)» y coordenadas. El nombre del organizador es el dominio de su web de inscripciones sin el punto
ni guiones (p. ej. `conchipcanarias`, `empat`). robots.txt de AvaiBook: solo prohíbe zonas privadas,
diplomas, dorsales y justificantes, no el listado ni la ficha pública.

Sirve para cualquier comunidad: basta con añadir un módulo con su ID y su URL."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from fuentes import tecnocrono
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

# Productos que el organizador vende como si fueran pruebas (medallas, camisetas, donativos, dorsal 0…).
_NO_CARRERA = re.compile(r"\breserva\b|medall|camiseta|donacion|dorsal 0|dorsal cero|\bcena\b|\bmenu\b")


def _fichas(contenido: bytes | str) -> list[str]:
    """Enlace de cada evento del listado, en el mismo orden que los lee `tecnocrono.leer`."""
    sopa = BeautifulSoup(contenido, "html.parser")
    urls = []
    for ev in sopa.find_all(attrs={"itemtype": "https://schema.org/SportsEvent"}):
        enlace = ev.find("a", href=re.compile(r"/inscripcion/[^/]+/"))
        url = None
        if enlace:
            m = re.search(r"(https?://[^/]+/inscripcion/[^/]+/)", enlace["href"])
            url = m.group(1) if m else None
        elif otro := ev.find("a", href=re.compile(r"^https?://")):
            url = otro["href"]  # la prueba se inscribe en la web del organizador
        urls.append((nz.nombre(tecnocrono._prop(ev, "name") or ""), url))
    return urls


def leer(contenido: bytes | str, fuente_id: str, url_listado: str) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = tecnocrono.leer(contenido)
    enlaces = dict(_fichas(contenido))
    buenas = []
    for c in carreras:
        if _NO_CARRERA.search(nz.clave(c.nombre)):
            descartes.append(f"no es una carrera: {c.nombre}")
            continue
        url = enlaces.get(c.nombre) or url_listado
        c.fuente = Fuente(fuente_id, url)
        c.url_inscripcion = url
        buenas.append(c)
    return buenas, descartes
