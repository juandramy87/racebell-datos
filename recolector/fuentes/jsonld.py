"""Lector genérico de fichas con JSON-LD schema.org (SportsEvent o Event): lo usan Inscrik,
Deportime, Runnink y otras plataformas."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Optional

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente


def eventos(html: str) -> list[dict]:
    salida = []
    for bloque in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            datos = json.loads(bloque)
        except json.JSONDecodeError:
            continue
        candidatos = datos if isinstance(datos, list) else datos.get("@graph", [datos]) if isinstance(datos, dict) else []
        salida += [d for d in candidatos if isinstance(d, dict) and d.get("@type") in ("SportsEvent", "Event")]
    return salida


def recortar(datos: bytes) -> bytes:
    """Deja de una ficha solo los bloques JSON-LD y el og:title: lo único que se lee. Así ni la caché
    ni las muestras guardan nada más de la página (listas de inscritos, comentarios…)."""
    html = datos.decode("utf-8", "replace")
    trozos = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>.*?</script>', html, re.S)
    trozos += re.findall(r'<meta[^>]*property="og:title"[^>]*>', html)
    return ("<html><head>\n" + "\n".join(trozos) + "\n</head></html>\n").encode()


def leer_ficha(contenido: bytes | str, url: str, fuente_id: str, provincia_si_falta: Optional[str] = None
               ) -> tuple[Optional[Carrera], Optional[str]]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    evs = eventos(html)
    if not evs:
        return None, f"sin datos de evento: {url}"
    ev = evs[0]
    nombre = nz.nombre(ev.get("name", ""))
    if "EventCancelled" in str(ev.get("eventStatus", "")):
        return None, f"cancelada: {nombre}"
    inicio = datetime.fromisoformat(ev["startDate"]).replace(tzinfo=None)
    fin = datetime.fromisoformat(ev.get("endDate") or ev["startDate"]).replace(tzinfo=None)
    if (fin - inicio).days > 3:
        return None, f"circuito o temporada, no una carrera: {nombre}"
    a_pie, modalidad = nz.clasificar(nombre, ev.get("sport") or "")
    if not a_pie:
        return None, f"no es a pie: {nombre}"
    lugar = ev.get("location") or {}
    lugar = lugar[0] if isinstance(lugar, list) else lugar
    direccion = lugar.get("address") or {}
    if isinstance(direccion, str):
        direccion = {"addressLocality": direccion}
    provincia = (nz.provincia(direccion.get("addressRegion")) or nz.provincia_por_cp(direccion.get("postalCode"))
                 or nz.provincia(direccion.get("addressLocality")) or provincia_si_falta)
    municipio = None
    if not provincia:
        municipio = nz.municipio_espana(direccion.get("addressLocality")) or nz.municipio_espana(lugar.get("name"))
        provincia = municipio[1] if municipio else None
    if not provincia:
        return None, f"fuera de España o sin provincia: {nombre} ({direccion.get('addressRegion')})"
    c = Carrera(
        nombre=nombre,
        fecha=inicio.date(),
        hora=inicio.strftime("%H:%M") if inicio.strftime("%H:%M") != "00:00" else None,
        fuente=Fuente(fuente_id, url),
        poblacion=municipio[0] if municipio else nz.poblacion(direccion.get("addressLocality")),
        provincia=provincia,
        modalidad=modalidad,
        distancias_km=nz.distancias_del_nombre(nombre),
        url_inscripcion=url,
    )
    imagen = ev.get("image")
    c.cartel = imagen[0] if isinstance(imagen, list) and imagen else imagen if isinstance(imagen, str) else None
    if geo := lugar.get("geo"):
        try:
            c.coords = (float(geo["latitude"]), float(geo["longitude"]))
        except (KeyError, TypeError, ValueError):
            pass
    ofertas = ev.get("offers") or []
    ofertas = ofertas if isinstance(ofertas, list) else [ofertas]
    desde, hasta = [], []
    for o in ofertas:
        try:
            c.precios.append({"nombre": nz.nombre(o.get("name") or "General"), "euros": float(o["price"])})
        except (KeyError, TypeError, ValueError):
            pass
        if o.get("validFrom"):
            desde.append(datetime.fromisoformat(o["validFrom"]).replace(tzinfo=None))
        if o.get("validThrough"):
            hasta.append(datetime.fromisoformat(o["validThrough"]).replace(tzinfo=None))
    c.inscripcion_desde = min(desde) if desde else None
    c.inscripcion_hasta = max(hasta) if hasta else None
    # RockTheSport pone «SoldOut» en TODAS sus fichas, también en las abiertas: ahí no se hace caso.
    if fuente_id != "rockthesport" and ofertas and all("SoldOut" in str(o.get("availability", "")) for o in ofertas):
        c.previos.append("Inscripciones agotadas")
    if fin.date() != inicio.date():
        c.marcar(f"La fuente da inicio ({inicio:%d/%m %H:%M}) y fin ({fin:%d/%m %H:%M}) en días distintos: "
                 "confirmar el día de la carrera")
    if not c.inscripcion_hasta:
        c.marcar("Cierre de inscripción no indicado en la ficha", "pendiente_cartel")
    return c, None
