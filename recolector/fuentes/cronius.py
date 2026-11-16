"""Cronius Sport (Huelva y norte de Sevilla). La portada es una web estática con el calendario;
cada carrera enlaza a su ficha de AvaiBook Sports, de donde salen todos los datos."""
from __future__ import annotations

import re
from typing import Callable

from fuentes import avaibook
from nucleo.modelo import Carrera

ID = "cronius"
URL = "https://www.croniussport.es/"
_FICHA = re.compile(r"https://inscripciones\.croniussport\.es/inscripcion/[a-z0-9\-]+/")


def enlaces(contenido: bytes | str) -> list[str]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    return list(dict.fromkeys(_FICHA.findall(html)))  # sin repetir, en orden


def leer(contenido: bytes | str, *, descargar_ficha: Callable[[str], bytes]) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = [], []
    for url in enlaces(contenido):
        c, motivo = avaibook.leer_ficha(descargar_ficha(url), url, ID)
        if c:
            carreras.append(c)
        else:
            descartes.append(motivo)
    return carreras, descartes
