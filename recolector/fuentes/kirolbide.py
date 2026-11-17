"""Kirolbide Pro: agenda deportiva de la Diputación Foral de Bizkaia (`bizkaia.eus/es/kirolbidepro/agenda`).

Es la fuente original de casi todas las carreras de Bizkaia (las inscribe cada club donde quiere: Buscametas,
Kirolprobak, RockTheSport, su web…), incluidas las ~25 San Silvestres de los pueblos. La página trae en el propio
HTML un JSON con las «ocurrencias» (un día de un evento): título, fecha, municipio, deportes y enlace a la ficha.

Cómo se lee sin saltarse nada:
- robots.txt prohíbe `/*Buscador?krk-kbp-*` (el buscador general), no la agenda ni sus fichas.
- La agenda admite filtros por GET: deporte (Atletismo y Carreras de montaña), día (`fecha_busqueda`, un día
  exacto) y municipio. Cada respuesta trae como mucho 15 ocurrencias; el «ver más» es un POST con sesión que NO se
  usa. Por eso se pide día a día, y si un día tiene más de 15 (el 31/12) se parte la lista de municipios en dos,
  y otra vez si hace falta.
- La ficha (`/-/evento-detalle/<slug>`) da la hora, el organizador y el enlace de inscripción. Se guarda solo el
  bloque de esos datos (`recortar_ficha`).
Solo se guardan los datos públicos de la carrera."""
from __future__ import annotations

import html as html_mod
import json
import re
from datetime import date, timedelta
from typing import Callable, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from fuentes import euskadi
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "kirolbide"
BASE = "https://www.bizkaia.eus"
URL = BASE + "/es/kirolbidepro/agenda"
_PORTLET = "net_bizkaia_iybiwkgc_AgendaNuevaPortlet_INSTANCE_PXa6ElTd6cKR"
_NS = f"_{_PORTLET}_"
DEPORTES = {"13532638": "Atletismo", "13943699": "Carreras de montaña"}
POR_PAGINA = 15
# Deportes que, si son los únicos además de «Otros»/«Marchas», no son una carrera a pie.
_A_PIE = {"Atletismo", "Carreras de montaña", "Larga distancia"}
_OCURRENCIAS = re.compile(r"ocurrencias:\s*JSON\.parse\(\s*'(.*?)'\s*\)", re.S)
_TOTAL = re.compile(r"totalResultados:\s*(\d+)")
_HEX = re.compile(r"\\x([0-9a-fA-F]{2})")


def url_dia(dia: date, municipios: Optional[list[str]] = None) -> str:
    """Agenda filtrada por un día exacto y los deportes a pie (y, si hace falta, por municipios)."""
    params = {"p_p_id": _PORTLET, "p_p_lifecycle": "0", "p_p_state": "normal", "p_p_mode": "view",
              _NS + "busquedaManual": "1", _NS + "deporte": ",".join(DEPORTES),
              _NS + "fecha_busqueda": dia.strftime("%d/%m/%Y")}
    if municipios:
        params[_NS + "municipio"] = ",".join(municipios)
    return URL + "?" + urlencode(params)


def ocurrencias(contenido: bytes | str) -> tuple[list[dict], int]:
    """(ocurrencias de la página, total de resultados de la búsqueda)."""
    texto = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    m = _OCURRENCIAS.search(texto)
    total = _TOTAL.search(texto)
    if not m:
        return [], int(total.group(1)) if total else 0
    lista = json.loads(_HEX.sub(lambda h: chr(int(h.group(1), 16)), m.group(1)))
    return lista, int(total.group(1)) if total else len(lista)


def municipios_del_formulario(contenido: bytes | str) -> list[str]:
    """Códigos de los municipios del desplegable de la agenda (incluido «-1», fuera de Bizkaia)."""
    sopa = BeautifulSoup(contenido, "html.parser")
    sel = sopa.find("select", attrs={"name": _NS + "municipio"})
    return [o["value"] for o in sel.find_all("option") if o.get("value")] if sel else []


def _texto(fragmento: Optional[str]) -> str:
    """Quita las etiquetas («<span lang="eu">…</span>», «<abbr>») y los espacios de ancho cero."""
    t = BeautifulSoup(fragmento or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"[​‌‍﻿]", "", html_mod.unescape(t)).strip()


def recortar_ficha(contenido: bytes) -> bytes:
    """De la ficha solo interesa la lista de datos (hora, lugar, organizador, inscripción)."""
    sopa = BeautifulSoup(contenido, "html.parser")
    for ul in sopa.select("ul.d-flex.flex-column"):
        if ul.find(string=re.compile(r"Horario|Localizaci|Ordutegia|Kokapena")) or ul.find("a", string=re.compile(
                r"Inscripci|Izen")):
            return str(ul).encode()
    return b""


def leer_ficha(contenido: bytes | str) -> dict:
    """{"hora": "17:45", "inscripcion": "https://…"} de la ficha (ya recortada o entera)."""
    sopa = BeautifulSoup(contenido, "html.parser")
    datos: dict = {}
    for li in sopa.find_all("li"):
        etiqueta = li.find("span", class_="sr-only")
        etiqueta = etiqueta.get_text(strip=True) if etiqueta else ""
        valores = [s for s in li.find_all("span") if "sr-only" not in (s.get("class") or [])
                   and "bipoicon" not in (s.get("class") or [])]
        valor = valores[-1].get_text(" ", strip=True) if valores else ""
        if etiqueta.startswith(("Horario", "Ordutegia")) and (m := re.search(r"\b(\d{1,2})[:.](\d{2})\b", valor)):
            datos["hora"] = f"{int(m.group(1)):02d}:{m.group(2)}"
        enlace = li.find("a", href=re.compile(r"^https?://"))
        if enlace and re.search(r"inscripci|izen", enlace.get_text(" ", strip=True), re.I):
            datos["inscripcion"] = enlace["href"]
    return datos


def _ocurrencias_del_dia(bajar: Callable[[str], bytes], dia: date, municipios: list[str],
                         filtro: Optional[list[str]] = None) -> list[dict]:
    lista, total = ocurrencias(bajar(url_dia(dia, filtro)))
    if total <= len(lista) or not municipios:
        return lista
    # Más de 15 ese día: se parte la lista de municipios en dos y se pide cada mitad.
    grupo = filtro or municipios
    if len(grupo) == 1:
        return lista
    mitad = len(grupo) // 2
    return (_ocurrencias_del_dia(bajar, dia, municipios, grupo[:mitad])
            + _ocurrencias_del_dia(bajar, dia, municipios, grupo[mitad:]))


def carrera_de(oc: dict) -> tuple[Optional[Carrera], Optional[str]]:
    nombre = nz.nombre(_texto(oc.get("titulo")))
    deportes = set(oc.get("deporteList") or [])
    if not deportes & _A_PIE:
        return None, f"no es a pie: {nombre} ({', '.join(sorted(deportes))})"
    a_pie, modalidad = nz.clasificar(nombre)
    if not a_pie:
        return None, f"no es a pie: {nombre}"
    try:
        fecha = date.fromisoformat(oc["fecha"])
    except (KeyError, TypeError, ValueError):
        return None, f"sin fecha: {nombre}"
    lugar = _texto(oc.get("ubicacion"))
    hallado = euskadi.municipio(lugar, None) or euskadi.municipio(nombre)
    if oc.get("fueraBizkaia") and not hallado:
        return None, f"fuera de Bizkaia sin municipio claro: {nombre} ({lugar})"
    poblacion, provincia = hallado if hallado else (nz.poblacion(lugar), "Bizkaia")
    if lugar and hallado and not nz.municipio_espana(lugar) and "-" not in lugar:
        poblacion = nz.poblacion(lugar)  # barrio o pueblo pequeño («Sodupe», de Güeñes): se deja como lo da la agenda
    if not modalidad or modalidad == "asfalto":
        k = nz.clave(nombre)
        if re.search(r"\bkros|\bcross", k):
            modalidad = "cross"
        elif "Carreras de montaña" in deportes and "Atletismo" not in deportes:
            modalidad = modalidad if modalidad in ("trail",) else "montaña"
        elif re.search(r"mendi lasterketa|igoera", k):
            modalidad = "montaña"
    url = BASE + (oc.get("friendlyURL") or "")
    c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, url), poblacion=poblacion, provincia=provincia,
                modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre))
    if oc.get("imagenURL"):
        c.cartel = BASE + oc["imagenURL"]
    return c, None


def leer(bajar: Callable[[str], bytes], desde: date, hasta: date, *,
         bajar_ficha: Optional[Callable[[str], bytes]] = None) -> tuple[list[Carrera], list[str]]:
    """Pide la agenda día a día de `desde` a `hasta`. `bajar_ficha` (opcional) abre la ficha de cada carrera para la
    hora y el enlace de inscripción; debe guardar solo lo de `recortar_ficha`."""
    municipios: list[str] = []
    vistas: dict[str, dict] = {}  # eventoId → primera ocurrencia en el periodo (un evento de dos días sale dos veces)
    dia = desde
    while dia <= hasta:
        if not municipios:
            municipios = municipios_del_formulario(bajar(url_dia(dia)))
        for oc in _ocurrencias_del_dia(bajar, dia, municipios):
            vistas.setdefault(str(oc.get("eventoId") or oc.get("friendlyURL")), oc)
        dia += timedelta(days=1)
    carreras, descartes = [], []
    for oc in vistas.values():
        c, motivo = carrera_de(oc)
        if not c:
            descartes.append(motivo)
            continue
        if bajar_ficha:
            try:
                datos = leer_ficha(bajar_ficha(c.fuente.url))
            except RuntimeError as error:
                descartes.append(f"ficha sin leer ({error}): {c.nombre}")
                datos = {}
            c.hora = datos.get("hora") or c.hora
            c.url_inscripcion = datos.get("inscripcion")
        carreras.append(c)
    return carreras, descartes
