"""Montur Eventos (organizador de Albox, Almería): «Próximos eventos» de WordPress (Mage Event Manager). Cada tarjeta
lleva data-title, data-city-name, data-category («- Almería») y data-date («abril 18, 2027»), y la hora en el pie
(«10:00 am - …»). Publica sus carreras por montaña con meses de antelación. Se quitan senderismo y marchas."""
from __future__ import annotations

import html
import re
from datetime import date

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "montur"
URL = "https://montureventos.com/proximos-eventos/"
_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_FECHA = re.compile(r"(\w+) (\d{1,2}), (\d{4})")
_HORA = re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)", re.I)


def _hora(texto: str) -> str | None:
    m = _HORA.search(texto)
    if not m:
        return None
    h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0)
    return f"{h:02d}:{m.group(2)}"


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras, descartes = [], []
    for t in sopa.select("div.filter_item[data-title][data-date]"):
        nombre = nz.nombre(html.unescape(t["data-title"]).strip(" ."))
        provincia = nz.provincia((t.get("data-category") or "").strip(" -"))
        m = _FECHA.match(t["data-date"].strip())
        if not (provincia and m and nz.clave(m.group(1)) in _MESES):
            descartes.append(f"sin provincia andaluza o sin fecha: {nombre}")
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie or re.search(r"senderismo", nombre, re.I):
            descartes.append(f"no es una carrera a pie: {nombre}")
            continue
        enlace = t.select_one("a[href]")
        url = enlace["href"] if enlace else URL
        c = Carrera(nombre=nombre, fecha=date(int(m.group(3)), _MESES[nz.clave(m.group(1))], int(m.group(2))),
                    hora=_hora(t.get_text(" ", strip=True)), fuente=Fuente(ID, url),
                    poblacion=nz.poblacion(t.get("data-city-name")), provincia=provincia, modalidad=modalidad,
                    distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=url)
        fondo = t.select_one("[data-bg-image]")
        c.cartel = fondo["data-bg-image"] if fondo else None
        carreras.append(c)
    return carreras, descartes
