"""Inscrik (Almería, Granada, Jaén): la portada lista los eventos; cada ficha trae JSON-LD
con fecha, provincia y precios. robots.txt prohíbe /api/ y las rutas de inscripción: no se usan."""
from __future__ import annotations

import re
from typing import Callable
from urllib.parse import urljoin

from fuentes import jsonld
from nucleo import normalizar as nz
from nucleo.modelo import Carrera

ID = "inscrik"
URL = "https://inscrik.com/"
_FICHA = re.compile(r'href="(/evento/[a-z0-9\-]+/)"')


def leer(contenido: bytes | str, *, descargar_ficha: Callable[[str], bytes]) -> tuple[list[Carrera], list[str]]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    carreras, descartes = [], []
    for ruta in dict.fromkeys(_FICHA.findall(html)):
        slug = ruta.strip("/").split("/")[-1].replace("-", " ")
        if not nz.clasificar(slug)[0]:  # natación, senderismo…: ni se abre la ficha
            descartes.append(f"no es a pie: {slug}")
            continue
        url = urljoin(URL, ruta)
        c, motivo = jsonld.leer_ficha(descargar_ficha(url), url, ID)
        (carreras.append(c) if c else descartes.append(motivo))
    return carreras, descartes
