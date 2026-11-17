"""Championchip Levante (`chiplevante.com`): cronometrador e inscripciones de Alicante (Vega Baja, Elche,
Marina Baixa) y de Albacete y Murcia. Se leen dos páginas sin JS: la portada (lista «Próximos eventos») y
`/es/list-pruebas` (las 12 primeras tarjetas; «Cargar más» va por POST y no se usa). Cada evento trae día,
mes y año, nombre, «MUNICIPIO - PROVINCIA» y la ficha `/es/prueba/<slug>-<id>-<año>`. La ficha no da el
cierre de inscripción en un campo propio (solo tramos de precio en texto), así que no se abre.
robots.txt: no existe (404). Las marchas BTT, «Hyrace» y retos híbridos se descartan."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from fuentes import levante
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "chiplevante"
PORTADA = "https://www.chiplevante.com/"
URL = "https://www.chiplevante.com/es/list-pruebas"
_BASE = "https://www.chiplevante.com"

_MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8,
          "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
_NO_A_PIE = re.compile(r"\b(btt|hyrace|hybrid|hibrid[oa]|gravel|bike|ciclista|patinaje|uci|gran fondo world series)\b"
                       r"|^ruta\b")  # «Ruta Ermites del Camp d'Elx»: ruta a pie, no carrera


def eventos(*paginas: bytes | str) -> list[dict]:
    """Eventos de la portada y del listado, sin repetir fichas."""
    vistos: dict[str, dict] = {}
    for contenido in paginas:
        sopa = BeautifulSoup(contenido, "html.parser")
        # Listado: <article class="cartel-evento"> con .mes/.dia/.ano_calendario-grande, h2 > a y .tg-localizacion.
        for art in sopa.select("article.cartel-evento"):
            enlace = art.select_one(".tg-title a[href*='/prueba/']")
            mes, dia, anyo = (art.select_one(f".{c}_calendario-grande") for c in ("mes", "dia", "ano"))
            lugar = art.select_one(".tg-localizacion")
            if enlace and mes and dia and anyo:
                _apuntar(vistos, enlace["href"], enlace.get_text(" ", strip=True), mes, dia, anyo,
                         lugar.get_text(" ", strip=True) if lugar else "")
        # Portada: <li> con .calen (tres <p>: mes, día, año) y .prueba-cont > a > strong + span.
        for li in sopa.select("li"):
            calen = li.select_one(".calen")
            enlace = li.select_one(".prueba-cont a[href*='/prueba/']")
            if not (calen and enlace):
                continue
            ps = calen.find_all("p")
            nombre, lugar = enlace.select_one("strong"), enlace.select_one("span")
            if len(ps) == 3 and nombre:
                _apuntar(vistos, enlace["href"], nombre.get_text(" ", strip=True), *ps,
                         lugar.get_text(" ", strip=True) if lugar else "")
    return list(vistos.values())


def _apuntar(vistos: dict, href: str, nombre: str, mes, dia, anyo, lugar: str) -> None:
    url = href if href.startswith("http") else _BASE + href
    if url in vistos:
        return
    try:
        fecha = date(int(anyo.get_text(strip=True)), _MESES[mes.get_text(strip=True).upper()[:3]],
                     int(dia.get_text(strip=True)))
    except (KeyError, ValueError):
        return
    vistos[url] = {"url": url, "nombre": nombre, "fecha": fecha, "lugar": re.sub(r"\s+", " ", lugar).strip()}


def _lugar(texto: str) -> tuple[Optional[str], Optional[str]]:
    """«ALBATERA - ALICANTE» → («Albatera», «Alicante»); «CHINCHILLA DE MONTE-ARAGÓN - ALBACETE» también."""
    municipio, _, provincia = texto.rpartition(" - ")
    provincia_ok = nz.provincia(provincia)
    hallado = nz.municipio_espana(municipio or texto)
    if hallado and (not provincia_ok or hallado[1] == provincia_ok):
        return hallado[0], hallado[1]
    return nz.poblacion(municipio or None), provincia_ok


def leer(*paginas: bytes | str) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for e in eventos(*paginas):
        nombre = nz.nombre(e["nombre"])
        a_pie, modalidad = levante.clasificar(nombre)
        if not a_pie or _NO_A_PIE.search(nz.clave(nombre)):
            descartes.append(f"no es a pie: {nombre}")
            continue
        poblacion, provincia = _lugar(e["lugar"])
        if not provincia:
            descartes.append(f"sin provincia: {nombre} ({e['lugar']})")
            continue
        c = Carrera(
            nombre=nombre,
            fecha=e["fecha"],
            fuente=Fuente(ID, e["url"]),
            poblacion=poblacion,
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=levante.distancias(nombre),
            url_inscripcion=e["url"],
        )
        c.marcar("Hora y cierre de inscripción en la ficha de Championchip Levante", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
