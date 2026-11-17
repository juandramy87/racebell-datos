"""Federación de Atletismo de Madrid (FAM): calendario de carreras populares con permiso federativo
(`/calendario/carreras-populares?cal_year=AAAA`). Tabla con fecha «dd.mm.aa (D)», nombre, lugar
(«Parque Polvoranca (Leganés)»), documentos y tipo (Ruta, Campo a través, Trail / montaña).
Todas son de la Comunidad de Madrid. El enlace «Insc.» es la lista de inscritos (PDF): NO se usa.
robots.txt: permite todo a los rastreadores en general (solo cierra carpetas técnicas)."""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "fam"
BASE = "https://www.atletismomadrid.com"
URL = BASE + "/calendario/carreras-populares?cal_year={}"
_TIPOS = {"ruta": "asfalto", "campo a traves": "cross", "trail montana": "trail"}


def urls(desde: date, hasta: date) -> list[str]:
    """Una página por año (en diciembre también la del año siguiente)."""
    return [URL.format(a) for a in range(desde.year, hasta.year + 1)]


def _lugar(texto: str) -> str:
    """«Campus UAX (Villanueva de la Cañada)» → «Villanueva de la Cañada»; «Getafe» → «Getafe»."""
    m = re.search(r"\(([^()]+)\)\s*$", texto)
    return m.group(1) if m else texto


def leer(paginas: Iterable[bytes | str] | bytes | str) -> tuple[list[Carrera], list[str]]:
    if isinstance(paginas, (bytes, str)):
        paginas = [paginas]
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for pagina in paginas:
        sopa = BeautifulSoup(pagina, "html.parser")
        for fila in sopa.select("tr.fam-calendar-row"):
            titulo = fila.select_one("a.fam-calendar-title")
            celda_fecha = fila.select_one(".fam-calendar-table__date")
            if not titulo or not celda_fecha:
                continue
            nombre = nz.nombre(titulo.get_text(" ", strip=True))
            url = BASE + titulo["href"] if titulo["href"].startswith("/") else titulo["href"]
            if url in vistas:
                continue
            vistas.add(url)
            if "is-suspended" in (fila.get("class") or []):
                descartes.append(f"suspendida: {nombre}")
                continue
            m = re.search(r"(\d{2})\.(\d{2})\.(\d{2})", celda_fecha.get_text())
            if not m:
                continue
            tipo = fila.select_one(".fam-calendar-table__type")
            tipo = nz.clave(tipo.get("title", "")) if tipo else ""
            a_pie, modalidad = nz.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            lugar = fila.find("td", attrs={"data-label": "Lugar"})
            c = Carrera(
                nombre=nombre,
                fecha=date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1))),
                fuente=Fuente(ID, url),
                poblacion=nz.poblacion(_lugar(lugar.get_text(" ", strip=True))) if lugar else None,
                provincia="Madrid",
                modalidad=modalidad if modalidad and modalidad != "asfalto" else _TIPOS.get(tipo, modalidad),
                distancias_km=nz.distancias_del_nombre(nombre),
            )
            # El «Reglamento» suele ser la web o la inscripción de la carrera; los PDF no.
            regl = fila.select_one("a.fam-calendar-link--regulations")
            if regl and regl.get("href") and not re.search(r"\.pdf(\?|$)", regl["href"], re.I):
                c.url_inscripcion = regl["href"].replace("https:///", "https://")
            c.marcar("Cierre de inscripción en la web de la carrera (la FAM no lo da)", "pendiente_cartel")
            carreras.append(c)
    return carreras, descartes
