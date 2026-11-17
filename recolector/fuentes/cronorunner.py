"""Cronorunner (pueblos de Valencia: Horta Nord y Sud, Camp de Túria, Ribera…): la API pública que pinta su web de
inscripciones, `inscripciones.cronorunner.com/api/public/events` (JSON con nombre, fecha, población, circuito y
precio mínimo). Ficha: `/evento/<slug>`. Sin robots.txt. Leída con permiso del usuario (17/11/2026).
No da provincia: se saca del municipio (tabla del INE) y, si no, Valencia."""
from __future__ import annotations

import json
from datetime import date

from fuentes import levante
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "cronorunner"
URL = "https://inscripciones.cronorunner.com/api/public/events"
_FICHA = "https://inscripciones.cronorunner.com/evento/"


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    datos = json.loads(contenido)
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for e in datos.get("editions", []):
        nombre = nz.nombre(e.get("name") or e.get("eventName") or "")
        a_pie, modalidad = levante.clasificar(nombre, e.get("eventName"))
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        lugar = (e.get("location") or "").strip()
        municipio = nz.municipio_espana(lugar) if lugar else nz.municipio_espana(nombre)
        if municipio:
            poblacion, provincia = municipio
        else:
            poblacion, provincia = (nz.poblacion(lugar) if lugar else None), "Valencia"
        url = _FICHA + e["slug"]
        c = Carrera(
            nombre=nombre,
            fecha=date.fromisoformat(e["eventDate"]),
            fuente=Fuente(ID, url),
            poblacion=poblacion,
            provincia=nz.provincia(provincia),
            modalidad=modalidad,
            distancias_km=levante.distancias(nombre),
            url_inscripcion=url,
        )
        if not poblacion:
            c.marcar("Población no indicada en Cronorunner", "pendiente_cartel")
        c.marcar("Hora y cierre de inscripción en la ficha de Cronorunner", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
