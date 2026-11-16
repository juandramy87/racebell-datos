"""Deportime (Jaén sobre todo). Listado `proximas-carreras/` + ficha con JSON-LD (fecha y hora, precio,
estado). La ficha no trae nombre ni lugar en el JSON-LD: el nombre sale de og:title y la provincia
se supone Jaén (marcado para revisar)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Callable

from bs4 import BeautifulSoup

from fuentes import jsonld
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "deportime"
URL = "https://deportime.es/proximas-carreras/"
PROVINCIA_SUPUESTA = "Jaén"
_FICHA = re.compile(r'href="(https://deportime\.es/events/[a-z0-9\-]+/)"')


def leer_ficha(contenido: bytes | str, url: str) -> tuple[Carrera | None, str | None]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    evs = jsonld.eventos(html)
    titulo = BeautifulSoup(html, "html.parser").find("meta", property="og:title")
    nombre = nz.nombre((titulo.get("content") if titulo else "").split(" - DeporTime")[0])
    if not evs or not nombre:
        return None, f"sin datos de evento: {url}"
    ev = evs[0]
    if "EventCancelled" in str(ev.get("eventStatus", "")):
        return None, f"cancelada: {nombre}"
    a_pie, modalidad = nz.clasificar(nombre)
    if not a_pie:
        return None, f"no es a pie: {nombre}"
    inicio = datetime.fromisoformat(ev["startDate"]).replace(tzinfo=None)
    c = Carrera(nombre=nombre, fecha=inicio.date(), fuente=Fuente(ID, url), provincia=PROVINCIA_SUPUESTA,
                hora=inicio.strftime("%H:%M") if inicio.strftime("%H:%M") != "00:00" else None,
                modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=url)
    oferta = ev.get("offers") or {}
    oferta = oferta[0] if isinstance(oferta, list) and oferta else oferta
    try:
        if float(oferta.get("price")) > 0:
            c.precios.append({"nombre": "General", "euros": float(oferta["price"])})
    except (TypeError, ValueError):
        pass
    if "SoldOut" in str(oferta.get("availability", "")):
        c.previos.append("Inscripciones agotadas")
    c.marcar(f"Provincia supuesta ({PROVINCIA_SUPUESTA}) y población desconocida: Deportime no las da",
             "pendiente_cartel")
    c.marcar("Cierre de inscripción no indicado en la ficha", "pendiente_cartel")
    return c, None


def leer(contenido: bytes | str, *, descargar_ficha: Callable[[str], bytes]) -> tuple[list[Carrera], list[str]]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    carreras, descartes = [], []
    for url in dict.fromkeys(_FICHA.findall(html)):
        slug = url.rstrip("/").split("/")[-1].replace("-", " ")
        if not nz.clasificar(slug)[0]:
            descartes.append(f"no es a pie: {slug}")
            continue
        c, motivo = leer_ficha(descargar_ficha(url), url)
        (carreras.append(c) if c else descartes.append(motivo))
    return carreras, descartes
