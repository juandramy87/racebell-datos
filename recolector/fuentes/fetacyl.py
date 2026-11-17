"""Federación de Atletismo de Castilla y León (FETACYL): calendario autonómico
(`fetacyl.org/calendario-autonomico/`). Es un FullCalendar (plugin FooEvents) que trae TODOS los eventos en un JSON
dentro de la página (`var localObj = '{… "events": […]}'`): título, fecha y enlace a la ficha. Mezcla carreras
populares (cross, ruta, trail, San Silvestres) con campeonatos de pista, marcha y controles federados, que se quitan.
La ficha de cada prueba (`fetacyl.org/<slug>/`) dice «LUGAR: Laguna de Duero (VA)» y el organizador; solo se abre
la de las carreras que caen en el periodo pedido y se guarda recortada (sin los enlaces de inscritos ni resultados).
Los calendarios provinciales (`/go/calendario-<provincia>/`) son PDF en Google Drive: no se leen.
robots.txt: solo pone Crawl-delay a MSNBot y bingbot; no prohíbe nada."""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Callable, Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "fetacyl"
URL = "https://www.fetacyl.org/calendario-autonomico/"

# Abreviaturas de provincia que usa la federación en «LUGAR: Pueblo (VA)».
_PROVINCIAS = {"AV": "Ávila", "BU": "Burgos", "LE": "León", "PA": "Palencia", "SA": "Salamanca", "SG": "Segovia",
               "SE": "Segovia", "SO": "Soria", "VA": "Valladolid", "ZA": "Zamora"}
# Eventos federados que no son una carrera popular.
_NO_POPULAR = re.compile(r"\bcto\b|campeonato|control|pista|marcha|jornada|encuentro|liga|curso|clubes|"
                         r"juegos escolares|lanzamiento|combinadas|reunion|clinic|tecnificacion|concentracion|"
                         r"\bsub ?\d|asamblea|gala")


def eventos(contenido: bytes | str) -> list[dict]:
    """Los eventos del JSON del calendario: [{"title", "start", "url", …}]."""
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    todos: list[dict] = []
    for bloque in re.findall(r"var localObj = '(.*?)';\s*\n", html, re.S):
        try:
            datos = json.loads(bloque.replace('\\"', '"').replace("\\\\", "\\"))
        except json.JSONDecodeError:
            continue
        todos.extend(datos.get("events") or [])
    return todos


def recortar_ficha(contenido: bytes) -> bytes:
    """Solo «FECHA DE LA PRUEBA … LUGAR … ORGANIZADOR …» (sin enlaces a inscritos ni resultados)."""
    sopa = BeautifulSoup(contenido, "html.parser")
    for s in sopa(["script", "style"]):
        s.decompose()
    texto = re.sub(r"\s+", " ", sopa.get_text(" "))
    m = re.search(r"FECHA DE LA PRUEBA:.*?(?=ENLACES:|Menu |$)", texto)
    return m.group(0).strip().encode("utf-8") if m else b""


def lugar_de_ficha(contenido: bytes | str) -> tuple[Optional[str], Optional[str]]:
    """«… LUGAR: Laguna de Duero (VA) ORGANIZADOR: …» → («Laguna de Duero», «Valladolid»)."""
    texto = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    m = re.search(r"LUGAR:\s*(.*?)\s*(?:ORGANIZADOR:|ENLACES:|$)", texto)
    if not m or not m.group(1).strip():
        return None, None
    lugar = m.group(1).strip()
    m2 = re.match(r"(.*?)\s*\(([^()]+)\)\s*$", lugar)
    pueblo, codigo = (m2.group(1), m2.group(2).strip().upper()) if m2 else (lugar, "")
    provincia = _PROVINCIAS.get(codigo) or nz.provincia(codigo) or nz.provincia_de_municipio(pueblo)
    return nz.poblacion(pueblo) if pueblo else None, provincia


def leer(contenido: bytes | str, descargar_ficha: Optional[Callable[[str], bytes]] = None,
         desde: Optional[date] = None, hasta: Optional[date] = None) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for ev in eventos(contenido):
        try:
            fecha = date.fromisoformat(ev["start"][:10])
        except (KeyError, ValueError):
            continue
        if (desde and fecha < desde) or (hasta and fecha > hasta):
            continue
        nombre = nz.nombre(ev.get("title", ""))
        url = ev.get("url") or URL
        if not nombre or url in vistas:
            continue
        vistas.add(url)
        if _NO_POPULAR.search(nz.clave(nombre)):
            descartes.append(f"no es carrera popular: {nombre}")
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        poblacion = provincia = None
        if descargar_ficha and url != URL:
            try:
                poblacion, provincia = lugar_de_ficha(descargar_ficha(url))
            except Exception as error:  # sin ficha se intenta con el nombre
                descartes.append(f"ficha sin leer: {nombre} ({error})")
        if not provincia and (hallado := nz.municipio_espana(nombre)):
            poblacion, provincia = hallado
        if not provincia:
            descartes.append(f"sin lugar: {nombre}")
            continue
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, url),
            poblacion=poblacion,
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=nz.distancias_del_nombre(nombre),
        )
        c.marcar("Cierre de inscripción en el reglamento (la FETACYL no lo da)", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
