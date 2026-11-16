"""Alcanza tu Meta (Murcia y Levante almeriense): calendario con fecha, hora, «Localidad, Provincia»,
estado y cierre de inscripción («hasta el 17 nov · 14:00»). Se guardan las de cualquier provincia española."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, Carrera, Fuente

ID = "alcanzatumeta"
URL = "https://alcanzatumeta.es/calendario"
_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
          "sep": 9, "oct": 10, "nov": 11, "dic": 12}
_HASTA = re.compile(r"hasta el (\d{1,2}) (\w{3})\w*\s*·\s*(\d{1,2}:\d{2})")


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras, descartes = [], []
    for card in sopa.select("article.atmc-card"):
        h3 = card.select_one("h3 a")
        donde = card.select_one(".atmc-where")
        cuando = card.select_one("time.atmc-date")
        if not (h3 and donde and cuando):
            continue
        nombre = nz.nombre(h3.get_text(" ", strip=True))
        poblacion, _, provincia = donde.get_text(" ", strip=True).rpartition(",")
        if not nz.provincia(provincia):
            continue  # Murcia y resto: fuera de nuestra zona (sin anotarlo, son muchas)
        a_pie, modalidad = nz.clasificar(nombre, card.get("data-modality") or "")
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        fecha = date.fromisoformat(cuando["datetime"][:10])
        hora = re.search(r"·\s*(\d{1,2}:\d{2})", (card.select_one(".atmc-when") or donde).get_text())
        url = urljoin("https://alcanzatumeta.es/", h3["href"])
        c = Carrera(nombre=nombre, fecha=fecha, hora=hora.group(1).zfill(5) if hora else None,
                    fuente=Fuente(ID, url), poblacion=nz.poblacion(poblacion), provincia=nz.provincia(provincia),
                    modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=url,
                    estado_fuente={"open": ABIERTA, "closed": CERRADA}.get(card.get("data-status") or ""))
        estado = card.select_one(".atmc-status")
        if estado and (m := _HASTA.search(estado.get_text(" ", strip=True))) and nz.clave(m.group(2)) in _MESES:
            mes = _MESES[nz.clave(m.group(2))]
            anyo = fecha.year - (1 if mes > fecha.month else 0)
            h, mi = map(int, m.group(3).split(":"))
            c.inscripcion_hasta = datetime(anyo, mes, int(m.group(1)), h, mi)
        img = card.select_one(".atmc-poster img")
        c.cartel = img.get("src") if img else None
        carreras.append(c)
    return carreras, descartes
