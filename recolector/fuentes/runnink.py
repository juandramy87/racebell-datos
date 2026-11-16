"""Runnink (Cádiz): calendario con modalidad, nombre, «Población (Provincia)» y fecha con hora.
robots.txt pide Crawl-delay 10: solo se lee la página del calendario."""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "runnink"
URL = "https://runnink.com/calendario/"
_MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
_TARJETA = re.compile(r"^(?P<tipo>.*?) \| (?P<nombre>.*?) \| 📍 \| (?P<pob>.*?)\s*\((?P<prov>[^)]+)\) \| 📅 \| "
                      r"\w+ (?P<d>\d{1,2}) de (?P<m>\w+) de (?P<a>\d{4})(?: - (?P<h>\d{1,2}:\d{2})h)?", re.S)


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras, descartes = [], []
    for tarjeta in sopa.select("div.card"):
        enlace = tarjeta.find("a", href=lambda h: h and "/evento/" in h)
        if not enlace:
            continue
        m = _TARJETA.match(re.sub(r"\s+", " ", tarjeta.get_text(" | ", strip=True)))
        if not m or nz.clave(m["m"]) not in _MESES:
            descartes.append(f"no se entiende la tarjeta: {enlace['href']}")
            continue
        nombre = nz.nombre(m["nombre"])
        a_pie, modalidad = nz.clasificar(nombre, m["tipo"])
        if not a_pie or "hibrida" in nz.clave(m["tipo"]):
            descartes.append(f"no es a pie: {nombre} ({m['tipo']})")
            continue
        provincia = nz.provincia(m["prov"])
        if not provincia:
            descartes.append(f"fuera de España o sin provincia: {nombre}")
            continue
        img = tarjeta.find("img")
        c = Carrera(nombre=nombre, fecha=date(int(m["a"]), _MESES[nz.clave(m["m"])], int(m["d"])),
                    hora=m["h"].zfill(5) if m["h"] else None, fuente=Fuente(ID, enlace["href"]),
                    poblacion=nz.poblacion(m["pob"]), provincia=provincia,
                    modalidad=modalidad or ("obstáculos" if "obstac" in nz.clave(m["tipo"]) else None),
                    distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=enlace["href"],
                    cartel=img.get("src") if img else None)
        c.marcar("Precio y cierre de inscripción en la ficha de Runnink", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
