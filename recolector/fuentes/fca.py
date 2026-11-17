"""Federació Catalana d'Atletisme (fcatletisme.cat): calendario de competiciones de la web (WordPress con
The Events Calendar), leído con su API REST pública `wp-json/tribe/events/v1/events` (JSON, 50 por página).
Se quedan las de las categorías Ruta, Cros y Trail-Muntanya (fuera pista, marcha atlética y controles) y
se quitan los campeonatos de España, Europa o del Mundo (solo federados, casi siempre fuera de Cataluña).
El lugar es el «recinte» (municipio): la provincia se saca de la tabla de municipios catalanes o del
paréntesis «Atapuerca (Burgos)»."""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Optional
from urllib.parse import urlencode

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "fca"
API = "https://fcatletisme.cat/wp-json/tribe/events/v1/events"
MAX_PAGINAS = 6
_CATEGORIAS = {"ruta": None, "cros": "cross", "trail muntanya": "trail"}
# Campeonatos de España/Europa/Mundo, controles y la Copa Catalana de Promoció («(CCP)», categorías de chavales).
_NO_POPULAR = re.compile(r"\b(campionat d (espanya|europa)|campionat del mon|copa d europa|control|cic|ccp|promocio)\b")


def url(desde: date, hasta: date, pagina: int = 1) -> str:
    q = {"start_date": desde.isoformat(), "end_date": f"{hasta.isoformat()} 23:59:59", "per_page": 50}
    return API + "?" + urlencode(q | ({"page": pagina} if pagina > 1 else {}))


def otras_paginas(contenido: bytes | str, desde: date, hasta: date) -> list[str]:
    total = int(json.loads(contenido).get("total_pages") or 1)
    return [url(desde, hasta, n) for n in range(2, min(total, MAX_PAGINAS) + 1)]


def leer(paginas: list[bytes | str]) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistos: set = set()
    for pagina in paginas:
        for ev in json.loads(pagina).get("events", []):
            if ev.get("id") in vistos:
                continue
            vistos.add(ev.get("id"))
            nombre = nz.nombre(cat.texto(ev.get("title")))
            categorias = [nz.clave(c.get("name")) for c in ev.get("categories", [])]
            buenas = [c for c in categorias if c in _CATEGORIAS]
            if not buenas:
                continue  # pista, marcha atlética, promoción… (no se anota: son la mayoría)
            if _NO_POPULAR.search(nz.clave(nombre)) or "marxa" in categorias:
                descartes.append(f"federada o marcha atlética: {nombre}")
                continue
            if cat.es_infantil(nombre):
                descartes.append(f"infantil o escolar: {nombre}")
                continue
            a_pie, modalidad = cat.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            poblacion, provincia = _lugar(ev.get("venue") or {})
            if not provincia:
                descartes.append(f"sin provincia española: {nombre} ({(ev.get('venue') or {}).get('venue')})")
                continue
            web = cat.texto(ev.get("website")) or None
            c = Carrera(
                nombre=nombre,
                fecha=date.fromisoformat(ev["start_date"][:10]),
                fuente=Fuente(ID, ev.get("url") or API),
                poblacion=poblacion,
                provincia=provincia,
                modalidad=modalidad if modalidad not in (None, "asfalto") or not _CATEGORIAS[buenas[0]] else _CATEGORIAS[buenas[0]],
                distancias_km=cat.distancias(nombre),
                url_inscripcion=web if web and "atletismorfea" not in web else None,
            )
            hora = ev.get("start_date", "")[11:16]
            if not ev.get("all_day") and hora and hora != "00:00":
                c.hora = hora
            c.marcar("Inscripción y cierre en la web de la carrera", PENDIENTE_CARTEL)
            carreras.append(c)
    return carreras, descartes


def _lugar(recinte: dict) -> tuple[Optional[str], Optional[str]]:
    """«Cardedeu» → (Cardedeu, Barcelona); «Atapuerca (Burgos)» → (Atapuerca, Burgos); «Belgrado (SRB)» → (None, None)."""
    nombre = cat.texto(recinte.get("city") or recinte.get("venue"))
    hallado = cat.municipio(nombre)
    if hallado:
        return hallado
    m = re.match(r"^(.*?)\s*\(([^)]+)\)$", nombre)
    if m and nz.provincia(m.group(2)):
        return nz.poblacion(m.group(1)), nz.provincia(m.group(2))
    if nz.provincia(recinte.get("province") or recinte.get("stateprovince")):
        return nz.poblacion(nombre), nz.provincia(recinte.get("province") or recinte.get("stateprovince"))
    if nz.provincia(nombre):  # capitales: «Valencia», «Madrid», «Badajoz»
        return nz.provincia(nombre), nz.provincia(nombre)
    return None, None
