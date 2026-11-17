"""Circuito de Carreras de Logroño (Logroño Deporte, Ayuntamiento de Logroño): `circuito.logronodeporte.es/carreras`
lista las 12 pruebas de la temporada con nombre, organizador, «domingo, 29 de noviembre a las 11:00:00», lugar
(dentro de Logroño) y distancias («10K», «24K»). La página no dice el año: se toma el año en que ese día de la
semana cae en esa fecha, el más cercano a hoy. La ficha (`/carrera/<slug>`) enlaza a la inscripción del
organizador. robots.txt: solo prohíbe `/admin/`."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente, PENDIENTE_CARTEL

ID = "logronodeporte"
URL = "https://circuito.logronodeporte.es/carreras"
_BASE = "https://circuito.logronodeporte.es"
_MESES = {m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                      "septiembre", "octubre", "noviembre", "diciembre"], 1)}
_DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
_FECHA = re.compile(r"([a-z]+)\s+(\d{1,2})\s+de\s+([a-z]+)(?:\s+a las\s+(\d{1,2})\s+(\d{2}))?")  # sobre nz.clave
_KM_TXT = re.compile(r"(\d+(?:[.,]\d+)?)\s*[kK]\b")


def _fecha(texto: str, hoy: date) -> tuple[Optional[date], Optional[str]]:
    m = _FECHA.search(nz.clave(texto))
    if not m or m.group(3) not in _MESES:
        return None, None
    dia_semana, dia, mes = m.group(1), int(m.group(2)), _MESES[m.group(3)]
    hora = f"{int(m.group(4)):02d}:{m.group(5)}" if m.group(4) else None
    candidatas = []
    for anyo in (hoy.year - 1, hoy.year, hoy.year + 1):
        try:
            f = date(anyo, mes, dia)
        except ValueError:
            continue
        if dia_semana in _DIAS and _DIAS[f.weekday()] == dia_semana:
            candidatas.append(f)
    if not candidatas:
        return None, hora
    return min(candidatas, key=lambda f: abs((f - hoy).days)), hora


def leer(contenido: bytes | str, *, hoy: Optional[date] = None) -> tuple[list[Carrera], list[str]]:
    hoy = hoy or date.today()
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for bloque in sopa.select(".carrera"):
        enlace = bloque.select_one(".header-carrera h3 a") or bloque.find("h3")
        if not enlace:
            continue
        nombre = nz.nombre(enlace.get_text(" ", strip=True))
        fecha_el = bloque.select_one(".fecha")
        fecha, hora = _fecha(fecha_el.get_text(" ", strip=True) if fecha_el else "", hoy)
        if not fecha:
            descartes.append(f"sin fecha clara: {nombre}")
            continue
        if fecha < hoy:
            continue  # ya celebrada
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        distancias = []
        for li in bloque.select(".subcarreras li"):
            if m := _KM_TXT.fullmatch(li.get_text(" ", strip=True)):
                distancias.append(float(m.group(1).replace(",", ".")))
        url = _BASE + enlace["href"] if enlace.name == "a" and enlace.get("href", "").startswith("/") else URL
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            hora=hora if hora != "00:00" else None,
            fuente=Fuente(ID, url),
            poblacion="Logroño",
            provincia="La Rioja",
            modalidad=modalidad,
            distancias_km=sorted(set(distancias)) or nz.distancias_del_nombre(nombre),
        )
        c.marcar("Plazo y precio de inscripción en la web del organizador", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
