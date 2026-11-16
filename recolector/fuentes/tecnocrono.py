"""Tecnocrono (en AvaiBook Sports): listado HTML con datos schema.org SportsEvent.
Sierra de Cádiz y algo de Sevilla y Huelva. Trae «Inscripciones abiertas desde … hasta …»."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "tecnocrono"
URL = "https://www.avaibooksports.com/listado-tecnocrono.php"

_PLAZO = re.compile(r"desde\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})\s*hasta\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})", re.I)
_LUGAR = re.compile(r"^\s*(?:\d{5}\s+)?(.*?)\s*\(([^)]+)\)\s*$")


def _dt(texto: str) -> datetime:
    return datetime.strptime(texto, "%d/%m/%Y %H:%M")


def _prop(nodo, nombre: str) -> Optional[str]:
    el = nodo.find(attrs={"itemprop": nombre})
    if not el:
        return None
    return el.get("content") or el.get_text(" ", strip=True)


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for ev in sopa.find_all(attrs={"itemtype": "https://schema.org/SportsEvent"}):
        nombre = nz.nombre(_prop(ev, "name") or "")
        inicio = datetime.fromisoformat(_prop(ev, "startDate"))
        fin = datetime.fromisoformat(_prop(ev, "endDate") or _prop(ev, "startDate"))
        especialidad = _prop(ev, "especialidad") or ""
        if (fin - inicio).days > 3:
            descartes.append(f"circuito o temporada, no una carrera: {nombre}")
            continue
        a_pie, modalidad = nz.clasificar(nombre, especialidad)
        if a_pie:
            modalidad = nz.clasificar(nombre)[1] or modalidad  # el nombre manda sobre la especialidad
        if not a_pie or clave_otro(especialidad):
            descartes.append(f"no es a pie: {nombre} ({especialidad})")
            continue
        poblacion = provincia = None
        lugar = ev.find(attrs={"itemprop": "address"})
        if lugar and (m := _LUGAR.match(lugar.get_text(" ", strip=True))):
            poblacion, provincia = nz.poblacion(m.group(1)), nz.provincia(m.group(2))
        if not provincia:
            descartes.append(f"fuera de España o sin provincia: {nombre}")
            continue
        coords = None
        lat, lon = _prop(ev, "latitude"), _prop(ev, "longitude")
        if lat and lon:
            a, b = float(lat), float(lon)
            # La fuente da latitud y longitud al revés: en Andalucía la latitud ronda 36-38.
            coords = (b, a) if abs(a) < abs(b) else (a, b)
        desde = hasta = None
        if m := _PLAZO.search(ev.get_text(" ", strip=True)):
            desde, hasta = _dt(m.group(1)), _dt(m.group(2))
        enlace = ev.find("a", class_="nombre")
        url = enlace["href"] if enlace else URL
        c = Carrera(
            nombre=nombre,
            fecha=inicio.date(),
            hora=inicio.strftime("%H:%M") if inicio.strftime("%H:%M") != "00:00" else None,
            fuente=Fuente(ID, url),
            poblacion=poblacion,
            provincia=provincia,
            coords=coords,
            modalidad=modalidad or ("montaña" if "montana" in nz.clave(especialidad) else None),
            distancias_km=nz.distancias_del_nombre(nombre),
            inscripcion_desde=desde,
            inscripcion_hasta=hasta,
            url_inscripcion=url,
        )
        carreras.append(c)
    return carreras, descartes


def clave_otro(especialidad: str) -> bool:
    """La especialidad «Otro», «Evento», «Campamento»… no es una carrera a pie."""
    return nz.clave(especialidad) in {"otro", "evento", "campamento", "actividad", "excursiones"}
