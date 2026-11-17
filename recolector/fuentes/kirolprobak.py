"""Kirolprobak (País Vasco y Navarra): la portada lista las próximas pruebas (fecha, nombre, hora y
tipo) y cada una enlaza a su ficha de inscripción, que es AvaiBook Sports
(`inscripcion.kirolprobak.com/inscripcion/<slug>/`): JSON-LD con fecha, hora, localidad, código postal
y precios, y «Plazo de inscripción Del … al …». Sin robots.txt en la portada; el de las fichas solo
prohíbe zonas privadas y ficheros de inscritos."""
from __future__ import annotations

import re
from typing import Callable

from bs4 import BeautifulSoup

from fuentes import avaibook
from nucleo import normalizar as nz
from nucleo.modelo import Carrera

ID = "kirolprobak"
URL = "https://www.kirolprobak.com/es"
_FICHA = re.compile(r"^(https://inscripcion\.kirolprobak\.com/inscripcion/[a-z0-9\-]+/)")
# Tipos de la portada que no son a pie («TRIATHLON-SPRINT», «CICLISMO-…», «NATACIÓN-…»…).
_OTRO_DEPORTE = re.compile(r"triathlon|triatlon|duatlon|duathlon|ciclismo|btt|mtb|natacion|acuatlon|"
                           r"senderismo|marcha|patinaje|remo|piragu|surf|padel|futbol|hyrox")


def proximas(contenido: bytes | str) -> dict[str, tuple[str, list[str]]]:
    """{ficha: (nombre, [tipos de la portada])} de las próximas pruebas, en orden («ATLETISMO-RUTA»,
    «MONTAÑA - CARRERAS»…). Una prueba sale una vez por cada distancia u hora de salida."""
    sopa = BeautifulSoup(contenido, "html.parser")
    salida: dict[str, tuple[str, list[str]]] = {}
    for fila in sopa.select("tr"):
        # Solo las filas de «próximas»: llevan la fecha en su propia celda (las ya celebradas, no).
        if not fila.select_one("td span.d-block"):
            continue
        enlace = fila.select_one("th a[href]")
        if not enlace or not (m := _FICHA.match(enlace["href"])):
            continue  # pruebas que se inscriben fuera de Kirolprobak
        insignia = fila.select_one("th span.badge-primary")
        nombre, tipos = salida.setdefault(m.group(1), (enlace.get_text(" ", strip=True), []))
        tipos.append(insignia.get_text(" ", strip=True) if insignia else "")
    return salida


def enlaces(contenido: bytes | str) -> tuple[list[str], list[str]]:
    """Fichas de las próximas pruebas, sin repetir y en orden. Las que por su tipo no son a pie se
    descartan aquí, sin abrir la ficha. Devuelve (enlaces, descartes)."""
    urls, descartes = [], []
    for url, (nombre, tipos) in proximas(contenido).items():
        if all(t and _OTRO_DEPORTE.search(nz.clave(t)) for t in tipos):
            descartes.append(f"no es a pie: {nombre} ({', '.join(sorted(set(tipos)))})")
        else:
            urls.append(url)
    return urls, descartes


def limpiar_ficha(contenido: bytes | str) -> str:
    """Algunas fichas llevan saltos de línea sin escapar dentro del texto del JSON-LD (la descripción),
    y eso no es JSON válido: se cambian por espacios solo dentro de ese bloque."""
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    return re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)',
                  lambda m: m.group(1) + re.sub(r"[\r\n\t]+", " ", m.group(2)) + m.group(3), html, flags=re.S)


def _modalidad_del_tipo(tipos: list[str]) -> str | None:
    t = nz.clave(" ".join(tipos))
    for patron, modalidad in (("campo a traves|cross", "cross"), ("montana", "montaña"), ("trail", "trail"),
                              ("ruta|10 km|media maraton|maraton|5 km", "asfalto"), ("pista", "pista")):
        if re.search(patron, t):
            return modalidad
    return None


def leer(contenido: bytes | str, *, descargar_ficha: Callable[[str], bytes]) -> tuple[list[Carrera], list[str]]:
    urls, descartes = enlaces(contenido)
    tipos = {url: t for url, (_, t) in proximas(contenido).items()}
    carreras = []
    for url in urls:
        # Con «?lang=es» la ficha sale en castellano (si no, a veces en euskera y no se lee el plazo).
        c, motivo = avaibook.leer_ficha(limpiar_ficha(descargar_ficha(url + "?lang=es")), url, ID)
        if c:
            c.modalidad = c.modalidad or _modalidad_del_tipo(tipos.get(url, []))
            carreras.append(c)
        else:
            descartes.append(motivo)
    return carreras, descartes
