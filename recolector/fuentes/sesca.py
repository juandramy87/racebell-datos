"""Sesca (crono.sesca.es): listado HTML con nombre, población, fecha y metros. Provincia de Cádiz.
El cierre de inscripción está en la normativa en PDF de cada ficha (se lee aparte)."""
from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "sesca"
URL = "https://crono.sesca.es/"
PROVINCIA_SUPUESTA = "Cádiz"

_FECHA = re.compile(r"(\d{2}/\d{2}/\d{2,4})(?:\s+(\d{1,2}:\d{2}))?")


def _campos(bloque) -> dict[str, str]:
    campos = {}
    for div in bloque.find_all("div"):
        etiqueta = div.find("span", class_="etiqueta")
        texto = div.find("span", class_="texto")
        if etiqueta and texto:
            campos[nz.clave(etiqueta.get_text())] = texto.get_text(" ", strip=True)
    return campos


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for h2 in sopa.find_all("h2"):
        enlace = h2.find("a", href=re.compile(r"idCarrera="))
        if not enlace:
            continue
        nombre = nz.nombre(enlace.get_text(" ", strip=True))
        # Los datos están en el siguiente bloque con «Población:», «Fecha:» y «Metros:».
        bloque = h2.find_next(lambda tag: tag.name == "div" and tag.find("span", class_="etiqueta"))
        campos = _campos(bloque) if bloque else {}
        m = _FECHA.search(campos.get("fecha", ""))
        if not m:
            descartes.append(f"sin fecha: {nombre}")
            continue
        formato = "%d/%m/%y" if len(m.group(1)) == 8 else "%d/%m/%Y"
        fecha = datetime.strptime(m.group(1), formato).date()
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        url = urljoin(URL, enlace["href"])
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            hora=m.group(2).zfill(5) if m.group(2) else None,
            fuente=Fuente(ID, url),
            poblacion=nz.poblacion(campos.get("poblacion")),
            provincia=PROVINCIA_SUPUESTA,
            modalidad=modalidad,
            distancias_km=nz.km_desde_metros(campos.get("metros")) or nz.distancias_del_nombre(nombre),
            url_inscripcion=url,
        )
        img = bloque.find_previous("img") if bloque else None
        if img and img.get("src"):
            c.cartel = urljoin(URL, img["src"])
        c.marcar("Cierre de inscripción en la normativa (PDF) de la ficha", PENDIENTE_CARTEL)
        c.marcar(f"Provincia supuesta ({PROVINCIA_SUPUESTA}): Sesca no la indica", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
