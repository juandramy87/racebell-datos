"""Todofondo (portal de la Diputación de Almería): listado de próximas pruebas con nombre, fecha,
«Localidad (Provincia)» y tipo."""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "todofondo"
URL = "https://www.todofondo.net/prueba/proximas/"
_MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras, descartes = [], []
    for caja in sopa.select("div.caption"):
        enlace = caja.select_one("h3 a")
        p = caja.find("p")
        if not enlace or not p:
            continue
        nombre = nz.nombre(enlace.get_text(" ", strip=True))
        lineas = [l.strip() for l in p.get_text("\n").split("\n") if l.strip()]
        m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", lineas[0]) if lineas else None
        if not m or nz.clave(m.group(2)) not in _MESES:
            descartes.append(f"sin fecha: {nombre}")
            continue
        lugar = re.match(r"(.+?)\s*\(([^)]+)\)", lineas[1]) if len(lineas) > 1 else None
        tipo = lineas[2] if len(lineas) > 2 else ""
        a_pie, modalidad = nz.clasificar(nombre, tipo)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre} ({tipo})")
            continue
        provincia = nz.provincia(lugar.group(2)) if lugar else None
        if not provincia:
            descartes.append(f"fuera de Andalucía: {nombre}")
            continue
        url = urljoin(URL, enlace["href"])
        img = caja.find_previous("img")
        c = Carrera(nombre=nombre, fecha=date(int(m.group(3)), _MESES[nz.clave(m.group(2))], int(m.group(1))),
                    fuente=Fuente(ID, url), poblacion=nz.poblacion(lugar.group(1)), provincia=provincia,
                    modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=url,
                    cartel=urljoin(URL, img["src"]) if img and img.get("src") else None)
        c.marcar("Hora, precio y cierre en la ficha de Todofondo", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
