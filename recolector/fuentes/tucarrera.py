"""TuCarrera.es (cronometrador de Almería): su directorio de pruebas es un JSON público
(`api/events.php`, lo mismo que pinta la portada) con fecha, nombre, localidad, provincia, web
oficial y cartel. No trae hora ni plazos: van en la web oficial de cada prueba."""
from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import urljoin

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "tucarrera"
URL = "https://www.tucarrera.es/api/events.php"
WEB = "https://www.tucarrera.es/"


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = [], []
    for ev in json.loads(contenido):
        provincia = nz.provincia(ev.get("province"))
        if not provincia:
            continue  # Alicante…: fuera de nuestra zona
        nombre = nz.nombre(ev.get("event_name") or "")
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie or re.search(r"\bride\b", nz.clave(nombre)):  # «Calar Alto Ride»: ciclismo
            descartes.append(f"no es a pie: {nombre}")
            continue
        try:
            fecha = date.fromisoformat(ev["event_date"])
        except (KeyError, ValueError):
            descartes.append(f"sin fecha: {nombre}")
            continue
        web = (ev.get("website") or "").strip() or None
        if web and not web.startswith("http"):
            web = "https://" + web
        c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, web or WEB), poblacion=nz.poblacion(ev.get("locality")),
                    provincia=provincia, modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre),
                    url_inscripcion=web)
        if ev.get("poster_large"):
            c.cartel = urljoin(WEB, ev["poster_large"])
        c.marcar("Hora y plazo de inscripción no indicados en el directorio (ver la web oficial)", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
