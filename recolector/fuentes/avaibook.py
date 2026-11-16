"""Fichas de AvaiBook Sports (la plataforma que usan Tecnocrono, Cronius y otros cronometradores):
JSON-LD SportsEvent (fecha y hora, localidad, código postal, precios) y «Plazo de inscripción Del … al …»."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
          "sep": 9, "oct": 10, "nov": 11, "dic": 12}
_PLAZO = re.compile(
    r"Del\s+(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})\s+a las\s+(\d{1,2}:\d{2}).*?al\s+(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})\s+a las\s+(\d{1,2}:\d{2})",
    re.I | re.S)


def _dt(dia: str, mes: str, anyo: str, hora: str) -> Optional[datetime]:
    m = _MESES.get(nz.clave(mes)[:3])
    if not m:
        return None
    h, mi = map(int, hora.split(":"))
    return datetime(int(anyo), m, int(dia), h, mi)


def leer_ficha(contenido: bytes | str, url: str, fuente_id: str) -> tuple[Optional[Carrera], Optional[str]]:
    """Devuelve (carrera, motivo de descarte)."""
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    evento = None
    for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            datos = json.loads(bloque)
        except json.JSONDecodeError:
            continue
        if isinstance(datos, dict) and datos.get("@type") == "SportsEvent":
            evento = datos
            break
    if not evento:
        return None, f"sin datos de evento: {url}"
    nombre = nz.nombre(evento.get("name", ""))
    inicio = datetime.fromisoformat(evento["startDate"]).replace(tzinfo=None)
    fin = datetime.fromisoformat(evento.get("endDate") or evento["startDate"]).replace(tzinfo=None)
    if (fin - inicio).days > 3:
        return None, f"circuito o temporada, no una carrera: {nombre}"
    a_pie, modalidad = nz.clasificar(nombre)
    if not a_pie:
        return None, f"no es a pie: {nombre}"
    direccion = (evento.get("location") or {}).get("address") or {}
    provincia = nz.provincia_por_cp(direccion.get("postalCode")) or nz.provincia(direccion.get("addressRegion"))
    if not provincia:
        return None, f"fuera de España o sin provincia: {nombre} ({direccion.get('postalCode')})"
    c = Carrera(
        nombre=nombre,
        fecha=inicio.date(),
        hora=inicio.strftime("%H:%M") if inicio.strftime("%H:%M") != "00:00" else None,
        fuente=Fuente(fuente_id, url),
        poblacion=nz.poblacion(direccion.get("addressLocality")),
        provincia=provincia,
        modalidad=modalidad,
        distancias_km=nz.distancias_del_nombre(nombre),
        url_inscripcion=url,
        cartel=(evento.get("image") or [None])[0],
    )
    for oferta in evento.get("offers") or []:
        try:
            c.precios.append({"nombre": nz.nombre(oferta.get("name", "")), "euros": float(oferta["price"])})
        except (KeyError, TypeError, ValueError):
            pass
    texto = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    if m := _PLAZO.search(texto):
        c.inscripcion_desde = _dt(*m.groups()[:4])
        c.inscripcion_hasta = _dt(*m.groups()[4:])
    else:
        c.marcar("Plazo de inscripción no encontrado en la ficha", "pendiente_cartel")
    return c, None
