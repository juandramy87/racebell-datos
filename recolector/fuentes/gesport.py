"""GESport Canarias (Tenerife): cronometrador. Su página «Inscripciones» (`gesportcanarias.com/web/inscripciones/`)
lista las próximas pruebas con día, mes, tipo (RUNNING, TRAIL, OCR, HYBRID, CICLISMO…) y el enlace a la
inscripción en Chronotrack Canarias (`inscripciones.chronotrackcanarias.com/inscripcion/<slug>/`), que es
AvaiBook Sports: de esa ficha salen fecha y hora, municipio, provincia, precios y plazo de inscripción
(`fuentes/avaibook.py`). robots.txt: GESport no tiene; el de Chronotrack prohíbe zonas privadas, diplomas,
dorsales y justificantes, no la ficha pública."""
from __future__ import annotations

import re
from typing import Callable

from bs4 import BeautifulSoup

from fuentes import avaibook
from nucleo import normalizar as nz
from nucleo.modelo import Carrera

ID = "gesport"
URL = "https://www.gesportcanarias.com/web/inscripciones/"
_FICHA = re.compile(r"(?:https?:)?//(inscripciones\.chronotrackcanarias\.com/inscripcion/[a-z0-9\-]+/)")
_NO_A_PIE = re.compile(r"ciclismo|bike|btt|mtb|natacion|travesia|hybrid|hibrid|triatlon|duatlon")


_MODALIDAD = {"trail": "trail", "ocr": "obstáculos", "running": "asfalto", "cross": "cross"}


def enlaces(contenido: bytes | str) -> tuple[dict[str, str], list[str]]:
    """({ficha de Chronotrack: tipo según GESport} de las pruebas a pie, descartes por tipo)."""
    sopa = BeautifulSoup(contenido, "html.parser")
    fichas: dict[str, str] = {}
    descartes: list[str] = []
    for item in sopa.select(".cbp-item"):
        titulo = item.select_one(".cbp-l-grid-masonry-projects-title")
        tipo = item.select_one(".cbp-l-grid-masonry-projects-desc")
        enlace = item.find("a", href=_FICHA)
        if not (titulo and enlace):
            continue
        texto, tipo_txt = titulo.get_text(" ", strip=True), tipo.get_text(" ", strip=True) if tipo else ""
        if _NO_A_PIE.search(nz.clave(f"{tipo_txt} {texto}")):
            descartes.append(f"no es a pie: {texto} ({tipo_txt})")
            continue
        url = "https://" + _FICHA.search(enlace["href"]).group(1)
        fichas.setdefault(url, nz.clave(tipo_txt))
    return fichas, descartes


def leer(contenido: bytes | str, *, descargar_ficha: Callable[[str], bytes]) -> tuple[list[Carrera], list[str]]:
    fichas, descartes = enlaces(contenido)
    carreras = []
    for url, tipo in fichas.items():
        try:
            c, motivo = avaibook.leer_ficha(descargar_ficha(url), url, ID)
        except RuntimeError as error:  # una ficha caída no tumba las demás
            descartes.append(f"ficha no disponible: {url} ({error})")
            continue
        if c:
            c.modalidad = c.modalidad or _MODALIDAD.get(tipo)
            carreras.append(c)
        else:
            descartes.append(motivo)
    return carreras, descartes
