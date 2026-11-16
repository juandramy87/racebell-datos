"""FAA, carreras populares (atletismofaa.es/carreraspopulares/): toda Andalucía.
Solo trae fecha, un nombre corto y el cartel (enlazado a la inscripción). El resto
(población, precio, cierre, previos) está en el cartel: se marca para leerlo aparte."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "faa"
URL = "https://atletismofaa.es/carreraspopulares/"

_MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
_FECHA = re.compile(r"(\d{1,2})(?:\s*-\s*\d{1,2})?\s+([a-záéíóú]+)\s+(\d{4})", re.I)


def _mejor_cartel(img) -> Optional[str]:
    """La imagen grande del cartel: la de mayor anchura en srcset, o la original."""
    srcset = img.get("data-srcset") or ""
    candidatos = re.findall(r"(\S+)\s+(\d+)w", srcset)
    if candidatos:
        return max(candidatos, key=lambda c: int(c[1]))[0]
    return img.get("data-orig-src") or img.get("src")


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for columna in sopa.select("div.fusion_builder_column_1_4"):
        texto = columna.get_text("\n", strip=True)
        m = _FECHA.search(texto)
        if not m or nz.clave(m.group(2)) not in _MESES:
            continue
        fecha = date(int(m.group(3)), _MESES[nz.clave(m.group(2))], int(m.group(1)))
        resto = [l for l in texto.split("\n") if l.strip() and not _FECHA.search(l)]
        if not resto:
            continue
        nombre = nz.nombre(resto[0])
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        enlace = columna.find("a", href=True)
        img = columna.find("img")
        url_inscripcion = enlace["href"] if enlace else None
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, url_inscripcion or URL),
            modalidad=modalidad,
            url_inscripcion=url_inscripcion,
            cartel=_mejor_cartel(img) if img else None,
        )
        c.marcar("Población, precio, cierre y previos solo en el cartel", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
