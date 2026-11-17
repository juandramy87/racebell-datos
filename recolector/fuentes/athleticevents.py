"""Athletic Events (athleticevents.net, Tarragona): organizador e inscripciones de carreras del Tarragonès, Baix
Penedès y Alt Camp (Sant Silvestre de Tarragona, La Marató de 3Cat de Tarragona, Altafulla, Vila-seca,
Torredembarra, l'Arboç…). La página «Properes curses» lista cada prueba con nombre, pueblo y fecha
(«31 Desembre 2026»). robots.txt solo prohíbe zonas internas (/admin/, /bd/, /diploma/…), no el listado.
Solo se lee el listado; no se abren las clasificaciones."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "athleticevents"
URL = "https://www.athleticevents.net/properes-curses"
# Abreviaturas y formas que usan en los nombres o en el campo del pueblo.
_ALIAS = {"tgn": "Tarragona", "perafort i pugdelfi": "Perafort", "perafort i puigdelfi": "Perafort"}


def _municipio(pueblo: str, nombre: str) -> tuple[str, str] | None:
    k = nz.clave(pueblo)
    if k in _ALIAS:
        return cat.municipio(_ALIAS[k])
    return cat.municipio(pueblo) or cat.municipio_en(nombre) or nz.municipio_espana(pueblo)


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for enlace in sopa.select("#lista a[href*='/cursa/']"):
        url = urljoin(URL, enlace["href"])
        titulo = enlace.select_one(".panel-heading")
        pie = [d.get_text(" ", strip=True) for d in enlace.select(".panel-footer-info > div")]
        if not titulo or len(pie) < 2 or url in vistas:
            continue
        vistas.add(url)
        nombre = nz.nombre(cat.texto(titulo.get_text(" ", strip=True)))
        fecha = cat.fecha(pie[1])
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        a_pie, modalidad = cat.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        if cat.es_infantil(nombre):
            descartes.append(f"infantil: {nombre}")
            continue
        oficial = _municipio(cat.texto(pie[0]), nombre)
        if not oficial:
            descartes.append(f"sin municipio: {nombre} ({pie[0]})")
            continue
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, url),
            poblacion=oficial[0],
            provincia=oficial[1],
            modalidad=modalidad,
            distancias_km=cat.distancias(nombre),
            url_inscripcion=url,
        )
        img = enlace.select_one(".panel-body img")
        if img and img.get("src"):
            c.cartel = urljoin(URL, img["src"])
        c.marcar("Cierre de inscripción en la ficha de Athletic Events", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
