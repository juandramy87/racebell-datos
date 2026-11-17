"""Línea de Salida (Cartagena, Campo de Cartagena, Mar Menor; algo de la Vega Baja): listado
`lineadesalida.net/proximas-carreras` con tarjetas «nombre · población · dd/mm/aaaa» que enlazan a
`/carreras/<slug>`. No da provincia: Murcia salvo las poblaciones conocidas de fuera (`levante`).
robots.txt lo permite todo."""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fuentes import levante
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "lineadesalida"
URL = "https://www.lineadesalida.net/proximas-carreras"
_BASE = "https://www.lineadesalida.net/"


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for enlace in sopa.select('a[href^="/carreras/"]'):
        titulo = enlace.select_one("h3")
        datos = [s.get_text(" ", strip=True) for s in enlace.select("li small")]
        url = urljoin(_BASE, enlace["href"])
        if not titulo or len(datos) < 2 or url in vistas:
            continue
        vistas.add(url)
        nombre = nz.nombre(titulo.get_text(" ", strip=True))
        fecha_m = re.search(r"(\d{2})/(\d{2})/(\d{4})", datos[-1])
        if not fecha_m:
            descartes.append(f"sin fecha: {nombre}")
            continue
        a_pie, modalidad = levante.clasificar(nombre)
        if a_pie and re.search(r"\b(bano|bany)\b", nz.clave(nombre)):
            a_pie = False  # «Baño de Navidad»: es en el mar
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        poblacion = nz.poblacion(datos[0])
        c = Carrera(
            nombre=nombre,
            fecha=date(int(fecha_m.group(3)), int(fecha_m.group(2)), int(fecha_m.group(1))),
            fuente=Fuente(ID, url),
            poblacion=poblacion,
            provincia=levante.provincia_murciana(poblacion),
            modalidad=modalidad,
            distancias_km=levante.distancias(nombre),
            url_inscripcion=url,
        )
        c.marcar("Hora y plazo de inscripción en la ficha de Línea de Salida", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
