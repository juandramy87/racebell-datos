"""Runática (`runatica.com`): inscripciones y cronometraje de la Ribera (Alzira), Castellón (Serra d'Espadà),
la Plana de Utiel, Teruel, Tarragona y Cuenca. La portada tiene dos partes: tarjetas de «Inscripciones»
(próximas) y, tras el título «Resultados», las pasadas; solo se lee (y se guarda en caché) la primera
(`recortar`). Cada tarjeta trae nombre, ficha `/event/<slug>`, «Municipio (Provincia)», distancias y, en un
comentario HTML, la fecha con hora, las categorías y la apertura y el cierre de inscripción.
robots.txt: no existe (404). Fuera las de bici, esquí, escolares y los circuitos (agrupan varias)."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from fuentes import levante
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "runatica"
URL = "https://www.runatica.com/"
_BASE = "https://www.runatica.com"
_RESULTADOS = b'<span lang="es">Resultados</span>'

_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_TARJETA = re.compile(
    r'<h5><a href="(?P<href>[^"]+)"[^>]*>(?P<nombre>[^<]*)</a>.*?'
    r'fa-calendar-alt"></i>(?P<fecha>[^\n]*)\n.*?'
    r'fa-map-marker-alt"></i>(?P<lugar>[^\n]*)\n.*?'
    r'fa-map"></i>(?P<distancias>[^\n]*)\n'
    r'(?:.*?fa-user-tag"></i>(?P<categorias>[^\n]*)\n)?'
    r'(?:.*?calendar-check"></i>(?P<desde>[^\n]*)\n)?'
    r'(?:.*?calendar-times"></i>(?P<hasta>[^\n<]*?)\s*-->)?', re.S)
_FECHA = re.compile(r"(\d{1,2}) de (\w+) de (\d{4})(?:, a las (\d{1,2}):(\d{2}))?")
_NO_A_PIE = re.compile(r"\b(btt|ebike|bike|esqui|escolar|gravel|road|ciclismo|natacio|triatlo)\w*")
_FECHA_HORA = "%Y-%m-%d %H:%M:%S"


def recortar(contenido: bytes) -> bytes:
    """Solo la parte de inscripciones: lo que va tras «Resultados» no se guarda."""
    i = contenido.find(_RESULTADOS)
    return contenido[:i] if i >= 0 else contenido


def _fecha_hora(texto: str) -> tuple[Optional[date], Optional[str]]:
    m = _FECHA.search(texto)
    if not m or m.group(2).lower() not in _MESES:
        return None, None
    fecha = date(int(m.group(3)), _MESES[m.group(2).lower()], int(m.group(1)))
    hora = None
    if m.group(4) and (int(m.group(4)), m.group(5)) != (0, "00"):  # «a las 00:00»: sin hora
        hora = f"{int(m.group(4)):02d}:{m.group(5)}"
    return fecha, hora


def _dt(texto: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.strptime((texto or "").strip(), _FECHA_HORA)
    except ValueError:
        return None


def _lugar(texto: str) -> tuple[Optional[str], Optional[str]]:
    """«Alzira (Valencia)» → («Alzira», «Valencia»); «Costa Daurada (Tarragona)» → (None, «Tarragona»)."""
    m = re.match(r"\s*(.*?)\s*\(([^)]+)\)\s*$", texto)
    municipio, provincia = (m.group(1), nz.provincia(m.group(2))) if m else (texto.strip(), None)
    for parte in [municipio] + municipio.split("/"):  # «Eslida / Aín»: el primero que se encuentre
        hallado = nz.municipio_espana(parte.strip())
        if hallado and (not provincia or hallado[1] == provincia):
            return hallado
    return None, provincia


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    if isinstance(contenido, str):
        contenido = contenido.encode()
    html = recortar(contenido).decode("utf-8", "replace")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for m in _TARJETA.finditer(html):
        nombre = nz.nombre(m.group("nombre").strip())
        textos = (nombre, m.group("categorias") or "", m.group("distancias") or "")
        a_pie, modalidad = levante.clasificar(nombre)
        if not a_pie or _NO_A_PIE.search(nz.clave(" ".join(textos))) or nz.clave(nombre).startswith("circuito"):
            descartes.append(f"no es a pie: {nombre}")
            continue
        fecha, hora = _fecha_hora(m.group("fecha"))
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        poblacion, provincia = _lugar(m.group("lugar"))
        if not provincia:
            descartes.append(f"sin provincia: {nombre} ({m.group('lugar').strip()})")
            continue
        url = _BASE + m.group("href")
        desde, hasta = _dt(m.group("desde")), _dt(m.group("hasta"))
        # Algunas fichas arrastran plazos del año anterior: solo se fían si cuadran con la fecha.
        plazo_ok = hasta and (not desde or desde <= hasta) and hasta.date() <= fecha
        kms = set(levante.distancias(m.group("distancias") or "")) | set(levante.distancias(nombre))
        if 21.097 in kms:
            kms.discard(21.0)  # «21K» de una media maratón
        kms = sorted(kms)
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            hora=hora,
            fuente=Fuente(ID, url),
            poblacion=poblacion,
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=kms,
            inscripcion_desde=desde if plazo_ok else None,
            inscripcion_hasta=hasta if plazo_ok else None,
            url_inscripcion=url,
        )
        if not plazo_ok:
            c.marcar("Plazo de inscripción en la ficha de Runática", "pendiente_cartel")
        if not poblacion:
            c.marcar(f"Población no indicada en Runática ({m.group('lugar').strip()})", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
