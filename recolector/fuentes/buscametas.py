"""Buscametas (Vitoria-Gasteiz): plataforma de inscripción y cronometraje de Álava, Bizkaia (Encartaciones) y
alrededores. Su página `buscametas.com/inscripciones/` lista los eventos que inscribe ella misma (es la fuente
original): nombre, «Municipio (Provincia)», fecha dd/mm/aaaa, estado («abierta», «proximamente», «cerrada») y el
enlace de inscripción (`/modulos/ticket/evento.php?codigo=N`).

robots.txt prohíbe `/modulos/` y `*.php`: solo se lee el listado `/inscripciones/` y el enlace de inscripción se
guarda sin abrirlo. Su calendario general (`/calendario/…`) es un agregador de toda España y NO se usa."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from fuentes import euskadi
from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, NO_ABIERTA, Carrera, Fuente

ID = "buscametas"
URL = "https://www.buscametas.com/inscripciones/"
_BASE = "https://www.buscametas.com"
_ESTADOS = {"abierta": ABIERTA, "abiertas": ABIERTA, "proximamente": NO_ABIERTA, "cerrada": CERRADA,
            "cerradas": CERRADA, "agotada": CERRADA}
_FECHA = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_LUGAR = re.compile(r"^\s*(.*?)\s*\(([^)]+)\)\s*$")


def _lugar(texto: str) -> tuple[Optional[str], Optional[str]]:
    """«Zalla (Bizkaia)» → («Zalla», «Bizkaia»). Se respeta la localidad del listado (puede ser un barrio:
    «Sodupe», «Lezama (Álava)», de Amurrio); solo se cambia si es un municipio con otro nombre en la misma
    provincia («Vitoria» → «Vitoria-Gasteiz»)."""
    m = _LUGAR.match(texto or "")
    lugar, prov = (m.group(1), m.group(2)) if m else (texto, None)
    provincia = nz.provincia(prov)
    if provincia:
        hallado = euskadi.municipio(lugar, [provincia])
        if hallado and nz.clave(hallado[0]).startswith(nz.clave(lugar)):
            return hallado
        return nz.poblacion(lugar), provincia
    return euskadi.municipio(lugar, None) or (nz.poblacion(lugar), None)


# «Mendi Martxa» (marcha de montaña) no es carrera; «Carrera Martxa …» sí (carrera y marcha).
_MARTXA = re.compile(r"\bmartxa\b")
_CARRERA = re.compile(r"\b(carrera|lasterketa|korrika|trail|kros|cross|krosa)\b")


def _bonito(nombre: str) -> str:
    """Arregla lo que deja nz.nombre al pasar de MAYÚSCULAS: «Zalla-balma-zalla» → «Zalla-Balma-Zalla»,
    «25n» → «25N»."""
    nombre = re.sub(r"(?<=[A-Za-zÁÉÍÓÚÑáéíóúñ]-)([a-záéíóúñ])", lambda m: m.group(1).upper(), nombre)
    return re.sub(r"\b(\d+)([a-z])\b", lambda m: m.group(1) + m.group(2).upper(), nombre)


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for item in sopa.select(".insc-item"):
        titulo = item.select_one(".i2-nombre")
        if not titulo:
            continue
        nombre = _bonito(nz.nombre(titulo.get_text(" ", strip=True)))
        a_pie, modalidad = nz.clasificar(nombre)
        if _MARTXA.search(nz.clave(nombre)) and not _CARRERA.search(nz.clave(nombre)):
            a_pie = False
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        fecha_el = item.select_one(".i2-fecha")
        m = _FECHA.search(fecha_el.get_text(" ", strip=True) if fecha_el else "")
        if not m:
            descartes.append(f"sin fecha: {nombre}")
            continue
        fecha = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        lugar_el = item.select_one(".i2-loc")
        poblacion, provincia = _lugar(lugar_el.get_text(" ", strip=True) if lugar_el else "")
        if not provincia:
            descartes.append(f"fuera de España o sin provincia: {nombre}")
            continue
        k = nz.clave(nombre)
        if re.search(r"\bkros|\bcross", k):
            modalidad = "cross"
        elif re.search(r"\btrail\b", k):
            modalidad = "trail"
        elif re.search(r"mendi|igoera|erronka", k) and modalidad in (None, "asfalto"):
            modalidad = "montaña"
        enlace = item.select_one("a.i2-cta[href]")
        url = _BASE + enlace["href"] if enlace and enlace["href"].startswith("/") else (enlace["href"] if enlace else URL)
        c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, url), poblacion=poblacion, provincia=provincia,
                    modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre),
                    estado_fuente=_ESTADOS.get(nz.clave(item.get("data-status") or "").replace(" ", "")),
                    url_inscripcion=url if enlace else None)
        img = item.select_one(".i2-card-media img[src]")
        if img:
            c.cartel = _BASE + img["src"] if img["src"].startswith("/") else img["src"]
        carreras.append(c)
    return carreras, descartes
