"""Sportmaniacs (toda España; en Andalucía sobre todo Huelva y Sevilla). El listado
`/es/races?page=N` trae nombre, fechas y localidad, pero no la provincia: esa sale del JSON-LD
de la ficha (addressRegion). Para no abrir cientos de fichas de fuera de Andalucía:
  - solo se abren las fichas de carreras a pie dentro del plazo pedido;
  - lo que ya se sabe de cada ficha («fuera de Andalucía» o su provincia) se recuerda en
    `datos/sportmaniacs-provincias.json`, así cada día solo se abren las fichas nuevas.
robots.txt prohíbe /app y las clasificaciones (/results, /rankings): no se usan."""
from __future__ import annotations

import re
from datetime import date
from typing import Callable, Optional

from bs4 import BeautifulSoup

from fuentes import jsonld
from nucleo import normalizar as nz
from nucleo.modelo import Carrera

ID = "sportmaniacs"
URL = "https://sportmaniacs.com/es/races?page={}"
WEB = "https://sportmaniacs.com"
MAX_PAGINAS = 15
FUERA = ""  # valor del recuerdo para las fichas de fuera de Andalucía


def tarjetas(contenido: bytes | str) -> list[dict]:
    """Tarjetas del listado: {url, slug, nombre, fecha, lugar}."""
    sopa = BeautifulSoup(contenido, "html.parser")
    salida = []
    for art in sopa.select("article"):
        enlace = art.select_one('a[href*="/races/"]')
        cuando = art.select_one("time[datetime]")
        titulo = art.select_one(".card-title")
        if not (enlace and cuando and titulo):
            continue
        pie = art.select_one(".card-footer")
        lugar = pie.get_text(" ", strip=True).split(" - ")[-1] if pie else ""
        lugar = re.sub(r"^.*?\d{4}\s*", "", lugar).strip()  # quita las fechas que preceden al lugar
        ruta = enlace["href"]
        salida.append({"url": WEB + ruta if ruta.startswith("/") else ruta,
                       "slug": ruta.rstrip("/").split("/")[-1],
                       "nombre": nz.nombre(titulo.get_text(" ", strip=True)),
                       "fecha": date.fromisoformat(cuando["datetime"][:10]),
                       "lugar": lugar or None})
    return salida


def bajar_paginas(descargar: Callable[[str], bytes], hasta: date) -> list[bytes]:
    """Descarga páginas del listado (ordenado por fecha) hasta pasar de `hasta` o quedarse sin tarjetas."""
    paginas = []
    for n in range(1, MAX_PAGINAS + 1):
        pagina = descargar(URL.format(n))
        tj = tarjetas(pagina)
        if not tj:
            break
        paginas.append(pagina)
        if min(t["fecha"] for t in tj) > hasta:
            break
    return paginas


def leer(paginas: list[bytes | str], *, descargar_ficha: Callable[[str], bytes], desde: date, hasta: date,
         recuerdo: Optional[dict[str, str]] = None) -> tuple[list[Carrera], list[str]]:
    """`recuerdo` (slug → provincia, o "" si es de fuera) se consulta y se completa aquí."""
    recuerdo = {} if recuerdo is None else recuerdo
    carreras, descartes, vistas = [], [], set()
    for pagina in paginas:
        for t in tarjetas(pagina):
            if t["slug"] in vistas or not (desde <= t["fecha"] <= hasta):
                continue
            vistas.add(t["slug"])
            if not nz.clasificar(t["nombre"])[0]:
                descartes.append(f"no es a pie: {t['nombre']}")
                continue
            if recuerdo.get(t["slug"]) == FUERA:
                continue  # ya se sabe que es de fuera de Andalucía: ni se abre la ficha
            c, motivo = jsonld.leer_ficha(descargar_ficha(t["url"]), t["url"], ID)
            if c is None:
                if motivo and motivo.startswith("fuera de Andalucía"):
                    recuerdo[t["slug"]] = FUERA
                else:
                    descartes.append(motivo)
                continue
            recuerdo[t["slug"]] = c.provincia
            if c.cartel and "default" in c.cartel:
                c.cartel = None  # imagen genérica de Sportmaniacs, no es el cartel
            carreras.append(c)
    return carreras, descartes
