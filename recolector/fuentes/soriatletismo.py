"""Delegación Soriana de Atletismo (`soriatletismo.com`): competiciones de la temporada en una tabla
(`/competiciones/temporada/<n>/temporada-<año>`) con fecha «dd/mm/aaaa», nombre, lugar «GARRAY (SORIA)» y tipo
(Ruta, Cross, Pista). Las temporadas tienen un número que no se adivina: se sacan de los enlaces de la portada.
Trae las populares de los pueblos de Soria (Cerco a Numancia, Legua de Bayubas, San Silvestre del Royo…).
robots.txt: no tiene (404)."""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "soriatletismo"
BASE = "https://soriatletismo.com"
PORTADA = BASE + "/"
_NO_POPULAR = re.compile(r"\bcto\b|campeonato|control|jornada|encuentro|juegos escolares|pista|liga")
_TIPOS_A_PIE = {"ruta", "cross"}


def temporadas(portada: bytes | str, desde: date, hasta: date) -> list[str]:
    """Enlaces de las temporadas que tocan el periodo («temporada-2026», y «temporada-2026-27» si la hubiera)."""
    sopa = BeautifulSoup(portada, "html.parser")
    urls = []
    for a in sopa.find_all("a", href=re.compile(r"/competiciones/temporada/\d+/")):
        anyos = [int(x) for x in re.findall(r"(20\d\d)", a["href"])]
        if anyos and any(desde.year <= y <= hasta.year for y in anyos) and a["href"] not in urls:
            urls.append(a["href"])
    return urls


def _ciudad_del_nombre(nombre: str):
    """«XLI Medio Maratón Ciudad de Soria Abel Antón» → («Soria», «Soria»)."""
    m = re.search(r"(?:ciudad|villa) de (\w+(?: de \w+)?)", nombre, re.I)
    if not m:
        return None
    return nz.municipio_espana(m.group(1)) or nz.municipio_espana(m.group(1).split()[0])


def leer(paginas: Iterable[bytes | str] | bytes | str) -> tuple[list[Carrera], list[str]]:
    if isinstance(paginas, (bytes, str)):
        paginas = [paginas]
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for pagina in paginas:
        sopa = BeautifulSoup(pagina, "html.parser")
        for fila in sopa.select("table tbody tr"):
            celda_fecha = fila.select_one(".team-standings__drawn")
            enlace = fila.select_one(".team-standings__team a[href]")
            nombre_el = fila.select_one(".team-meta__name")
            if not celda_fecha or not enlace or not nombre_el:
                continue
            m = re.search(r"(\d{2})/(\d{2})/(\d{4})", celda_fecha.get_text())
            if not m or enlace["href"] in vistas:
                continue
            vistas.add(enlace["href"])
            nombre = nz.nombre(nombre_el.get_text(" ", strip=True))
            tipo_el = fila.select_one(".team-standings__win")
            tipo = nz.clave(tipo_el.get_text(" ", strip=True)) if tipo_el else ""
            if tipo not in _TIPOS_A_PIE or _NO_POPULAR.search(nz.clave(nombre)):
                descartes.append(f"no es carrera popular: {nombre} ({tipo})")
                continue
            a_pie, modalidad = nz.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            lugar_el = fila.select_one(".team-meta__place")
            lugar = lugar_el.get_text(" ", strip=True) if lugar_el else ""
            m_lugar = re.match(r"(.*?)\s*\(([^()]+)\)\s*$", lugar)
            pueblo = m_lugar.group(1) if m_lugar else lugar
            provincia = (nz.provincia(m_lugar.group(2)) if m_lugar else None) or nz.provincia_de_municipio(pueblo)
            if not provincia:
                hallado = nz.municipio_espana(nombre) or _ciudad_del_nombre(nombre)
                if not hallado:
                    descartes.append(f"sin lugar: {nombre} ({lugar})")
                    continue
                pueblo, provincia = hallado
            c = Carrera(
                nombre=nombre,
                fecha=date(int(m.group(3)), int(m.group(2)), int(m.group(1))),
                fuente=Fuente(ID, enlace["href"]),
                poblacion=nz.poblacion(pueblo),
                provincia=provincia,
                modalidad=modalidad or ("cross" if tipo == "cross" else None),
                distancias_km=nz.distancias_del_nombre(nombre),
            )
            c.marcar("Cierre de inscripción en el reglamento de la prueba", "pendiente_cartel")
            carreras.append(c)
    return carreras, descartes
