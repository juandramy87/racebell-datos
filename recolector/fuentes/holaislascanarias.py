"""Agenda oficial de Turismo de Islas Canarias (Gobierno de Canarias): `holaislascanarias.com/eventos/`, filtrada por
la categoría «Deportivo» y la subcategoría «Deportes de Resistencia». Es la única lista común de las siete islas: trae
carreras de Gran Canaria, Lanzarote, Fuerteventura, La Palma, La Gomera y El Hierro que no salen en ningún
cronometrador que leamos (Trail Pino Santo, Bestial Race, Paris Chiquito, Llano del Camello, San Silvestres…).

El listado (una sola página con `limit=100`) da nombre, isla, fecha («06 Diciembre 2026», o solo «Ene 2027» cuando
aún no hay día) y la ficha. La ficha da la localidad, la descripción, las coordenadas y el enlace «Ir a la web del
evento» (la web oficial o la inscripción), que se usa como `url_inscripcion`. La provincia sale de la isla.
Sin día exacto o con varios días («4 al 6 Dic 2026») se descarta: no sabemos qué día es la carrera.
Solo se abren las fichas de las pruebas a pie dentro del plazo.

robots.txt: prohíbe /search/ y zonas de administración, no /eventos/; sin Crawl-delay para todos.
Es una agenda institucional (la redactan los cabildos y Turismo de Canarias), no un agregador de plataformas: si la
misma carrera sale en una plataforma, se une con ella y manda la plataforma."""
from __future__ import annotations

import html as html_lib
import re
from datetime import date
from typing import Callable, Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "holaislascanarias"
BASE = "https://www.holaislascanarias.com"
URL = (f"{BASE}/eventos/?text_field=&start_date=&end_date=&category=28&subcategory=31&island=&age="
       "&limit=100&page=0")
_PROVINCIA_ISLA = {
    "tenerife": "Santa Cruz de Tenerife", "la palma": "Santa Cruz de Tenerife", "la gomera": "Santa Cruz de Tenerife",
    "el hierro": "Santa Cruz de Tenerife", "gran canaria": "Las Palmas", "lanzarote": "Las Palmas",
    "fuerteventura": "Las Palmas", "la graciosa": "Las Palmas",
}
_MESES = {m: i for i, m in enumerate(["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov",
                                      "dic"], 1)}
_FECHA = re.compile(r"^(\d{1,2}) ([a-z]+) (\d{4})$")
# «Deportes de Resistencia» incluye bici, natación, crossfit…: lo que `nz.clasificar` no ve en el nombre.
_NO_A_PIE = re.compile(r"\b(bike|bikids|swim|open water|throwdown|crossfit|criterium|cronoescalada|thlon)\b|"
                       r"\w+thlon\b")
# Pruebas de natación cuyo nombre no lo dice («The Blue Challenge»): se ve en la descripción.
_NADO = re.compile(r"\b(a nado|natacion|aguas abiertas|nadador)")
_CORRER = re.compile(r"\b(carrera|trail|cross|run|running|maraton|milla|san silvestre|km)\b")
_REDES = re.compile(r"^https?://(www\.|m\.)?(facebook|instagram|twitter|x|tiktok)\.com/")
_COORDS = re.compile(r"google\.com/maps/place/(-?\d+\.\d+),(-?\d+\.\d+)")


def _fecha(texto: str) -> Optional[date]:
    m = _FECHA.match(nz.clave(texto))
    if not m or m.group(2)[:3] not in _MESES:
        return None
    try:
        return date(int(m.group(3)), _MESES[m.group(2)[:3]], int(m.group(1)))
    except ValueError:
        return None


def _web(url: Optional[str]) -> Optional[str]:
    """Web del evento sin rastreadores (utm_*, fbclid); las redes sociales no son una inscripción."""
    if not url or _REDES.match(url):
        return None
    base, _, consulta = url.partition("?")
    quedan = [p for p in consulta.split("&") if p and not re.match(r"(utm_[a-z]+|fbclid|igsh|locale)=", p)]
    return base + ("?" + "&".join(quedan) if quedan else "")


def listado(contenido: bytes | str) -> list[dict]:
    """[{url, nombre, isla, fecha_texto}] de cada tarjeta del listado."""
    sopa = BeautifulSoup(contenido, "html.parser")
    eventos = []
    for art in sopa.find_all("article", about=re.compile(r"/eventos/[^/]+/[^/]+/?$")):
        titulo = art.find(class_="event-title")
        fecha = art.find(class_="date-string")
        isla = art.find(class_="islands-selected")
        eventos.append({
            "url": art["about"],
            "nombre": nz.nombre((titulo.find("h2") or titulo).get_text(" ", strip=True)) if titulo else "",
            "isla": isla.find("p").get_text(" ", strip=True) if isla and isla.find("p") else "",
            "fecha_texto": fecha.get_text(" ", strip=True) if fecha else "",
        })
    return eventos


def recortar_ficha(contenido: bytes) -> bytes:
    """Guarda solo la fecha, la localidad, la descripción, el enlace a la web del evento y el mapa."""
    sopa = BeautifulSoup(contenido, "html.parser")
    partes = []
    for clase in ("wrapper-data", "buttons_zone"):
        if bloque := sopa.find(class_=clase):
            partes.append(str(bloque))
    if mapa := sopa.find("a", href=_COORDS):
        partes.append(f'<a href="{html_lib.escape(mapa["href"])}">mapa</a>')
    return ("<div>" + "".join(partes) + "</div>").encode()


def ficha(contenido: bytes | str) -> dict:
    sopa = BeautifulSoup(contenido, "html.parser")
    loc = sopa.find(class_="field--name-field-event-city")
    desc = sopa.find(class_="field--name-field-event-description")
    web = sopa.select_one(".web-event a[href]")
    mapa = sopa.find("a", href=_COORDS)
    coords = None
    if mapa:
        m = _COORDS.search(mapa["href"])
        coords = (float(m.group(1)), float(m.group(2)))
    return {
        "localidad": loc.find(class_="field__item").get_text(" ", strip=True) if loc and loc.find(class_="field__item") else None,
        "descripcion": (desc.find(class_="field__item") or desc).get_text(" ", strip=True) if desc else "",
        "web": web["href"].strip() if web else None,
        "coords": coords,
    }


def leer(contenido: bytes | str, descargar_ficha: Callable[[str], bytes], desde: date,
         hasta: date) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = [], []
    for ev in listado(contenido):
        nombre = ev["nombre"]
        fecha = _fecha(ev["fecha_texto"])
        if not fecha:
            descartes.append(f"sin día exacto ({ev['fecha_texto']}): {nombre}")
            continue
        if not desde <= fecha <= hasta:
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie or _NO_A_PIE.search(nz.clave(nombre)):
            descartes.append(f"no es a pie: {nombre}")
            continue
        provincia = _PROVINCIA_ISLA.get(nz.clave(ev["isla"]))
        if not provincia:
            descartes.append(f"sin isla: {nombre}")
            continue
        try:
            datos = ficha(descargar_ficha(ev["url"]))
        except Exception as error:  # noqa: BLE001 - una ficha caída no tumba las demás: vale con el listado
            descartes.append(f"ficha sin descargar ({error}): {nombre}")
            datos = {"localidad": None, "descripcion": "", "web": None, "coords": None}
        desc = nz.clave(datos["descripcion"])
        if _NADO.search(desc) and not _CORRER.search(nz.clave(nombre)):
            descartes.append(f"no es a pie (natación según la ficha): {nombre}")
            continue
        if not modalidad:
            a_pie_desc, mod_desc = nz.clasificar(datos["descripcion"])
            modalidad = mod_desc if a_pie_desc and mod_desc in {"trail", "montaña", "cross", "obstáculos"} else None
        localidad = datos["localidad"]
        hallado = nz.municipio_espana(localidad)
        if hallado and hallado[1] == provincia:
            poblacion = hallado[0]
        else:
            poblacion = nz.poblacion(localidad) if localidad else None
        carreras.append(Carrera(
            nombre=nombre, fecha=fecha, fuente=Fuente(ID, ev["url"]), poblacion=poblacion, provincia=provincia,
            coords=datos["coords"], modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre),
            url_inscripcion=_web(datos["web"]),
        ))
    return carreras, descartes

