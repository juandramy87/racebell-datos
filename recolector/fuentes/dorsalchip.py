"""Dorsalchip: API pública en JSON que usa su propia web (Málaga sobre todo; también Cádiz,
Granada y Córdoba). Trae apertura y cierre de inscripción exactos."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, SIN_INSCRIPCION, Carrera, Fuente

ID = "dorsalchip"
URL = "https://publicapi.dorsalchip.es/api/ProximosEventos"

_ESTADOS = {"abierta": ABIERTA, "cerrada": CERRADA, "sininscripcion": SIN_INSCRIPCION}


def _fecha_hora(texto: Optional[str]) -> Optional[datetime]:
    if not texto or texto.startswith("0001"):
        return None
    return datetime.fromisoformat(texto)


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    """Convierte la respuesta de la API en carreras. Devuelve (carreras, descartes)."""
    datos = json.loads(contenido)
    eventos = datos["Result"] if isinstance(datos, dict) else datos
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for e in eventos:
        nombre = nz.nombre(e.get("nombre") or "")
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        provincia = nz.provincia(e.get("provincia"))
        if not provincia:
            descartes.append(f"fuera de España o sin provincia: {nombre} ({e.get('provincia')})")
            continue
        c = Carrera(
            nombre=nombre,
            fecha=date.fromisoformat(e["fecha"][:10]),
            fuente=Fuente(ID, e.get("URL_CARRERA") or URL),
            poblacion=nz.poblacion(e.get("poblacion")),
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=nz.distancias_del_nombre(nombre),
            inscripcion_desde=_fecha_hora(e.get("inscripcionDesde")),
            inscripcion_hasta=_fecha_hora(e.get("inscripcionHasta")),
            estado_fuente=_ESTADOS.get(e.get("estadoInscripcion") or ""),
            url_inscripcion=e.get("URL_CARRERA"),
            cartel=e.get("URL_CARTEL_THUMBNAIL"),
        )
        if c.estado_fuente == ABIERTA and not c.inscripcion_hasta:
            c.marcar("Inscripción abierta pero sin fecha de cierre en Dorsalchip: mirar la web del organizador",
                     "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
