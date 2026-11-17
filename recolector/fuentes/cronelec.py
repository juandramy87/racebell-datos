"""Cronelec (Asturias): cronometrador e inscripciones. La portada trae «Próximos eventos» (calendario
EventON) con fecha, hora, nombre, lugar con coordenadas, tipo (RUNNING, TRAIL RUNNING, BTT…) y enlace.
La página /calendario/ devuelve 403 a los robots, así que solo se lee la portada (robots.txt la permite).
Casi todo es de Asturias; la provincia se pone por las coordenadas (si caen fuera, se descarta)."""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "cronelec"
URL = "https://cronelec.es/"

_A_PIE = re.compile(r"running|trail|obstaculos|atletismo|solidaria")
# Rectángulo aproximado de Asturias.
_ASTURIAS = ((42.88, 43.67), (-7.19, -4.51))


def _en_asturias(lat: float, lon: float) -> bool:
    (la0, la1), (lo0, lo1) = _ASTURIAS
    return la0 <= lat <= la1 and lo0 <= lon <= lo1


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for ev in sopa.select("div.eventon_list_event"):
        titulo = ev.select_one(".evcal_event_title")
        inicio = ev.select_one('time[itemprop="startDate"]')
        if not titulo or not inicio:
            continue
        nombre = nz.nombre(titulo.get_text(" ", strip=True))
        tipos = [t.get_text(" ", strip=True) for t in ev.select('em[data-filter="event_type"]')]
        if tipos and not any(_A_PIE.search(nz.clave(t)) for t in tipos):
            descartes.append(f"no es a pie: {nombre} ({', '.join(tipos)})")
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        if not modalidad:
            claves = nz.clave(" ".join(tipos))
            modalidad = "trail" if "trail" in claves else "obstáculos" if "obstaculos" in claves else "asfalto"
        anyo, mes, dia = (int(x) for x in inicio["datetime"].split("-")[:3])
        info = ev.select_one(".evcal_desc")
        coords = None
        if info and (latlng := info.get("data-latlng")):
            try:
                lat, lon = (float(x) for x in latlng.split(","))
                coords = (round(lat, 4), round(lon, 4))
            except ValueError:
                pass
        if not coords or not _en_asturias(*coords):
            descartes.append(f"fuera de Asturias o sin lugar: {nombre}")
            continue
        enlace = ev.select_one('a[itemprop="url"]')
        hora = ev.select_one(".evo_time .start")
        c = Carrera(
            nombre=nombre,
            fecha=date(anyo, mes, dia),
            hora=hora.get_text(strip=True).zfill(5) if hora and re.match(r"^\d{1,2}:\d{2}$", hora.get_text(strip=True)) else None,
            fuente=Fuente(ID, enlace["href"] if enlace else URL),
            poblacion=nz.poblacion(info.get("data-location_name")) if info else None,
            provincia="Asturias",
            coords=coords,
            modalidad=modalidad,
            distancias_km=nz.distancias_del_nombre(nombre),
            url_inscripcion=enlace["href"] if enlace else None,
        )
        imagen = ev.select_one(".ev_ftImg")
        if imagen and (m := re.search(r"url\((.*?)\)", imagen.get("style", ""))):
            c.cartel = m.group(1)
        c.marcar("Precio y cierre de inscripción en la ficha de Cronelec", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
