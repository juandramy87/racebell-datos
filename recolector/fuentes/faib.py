"""Federació d'Atletisme de les Illes Balears (FAIB): calendario de competiciones (`faib.es/calendari/`).
La página trae todo el calendario en un JSON dentro de un <script> (`var calendar_data = {...}`) con título,
fecha y hora, enlace a la ficha y un color por isla. Se pide filtrado por modalidad (`?modalitat_filter=ruta`,
`cros`, `trail`: la pista no interesa). La ficha solo dice la isla; el municipio se saca del nombre.
Recoge pruebas que no se inscriben en Elitechip (Sa Sobrassada, Son Fusteret, San Silvestre Palma…).
robots.txt: solo prohíbe /wp-admin/."""
from __future__ import annotations

import json
import re
from datetime import datetime

from fuentes.elitechip import PROVINCIA, municipio, solo_infantil
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "faib"
URL = "https://www.faib.es/calendari/?modalitat_filter={}"
MODALIDADES = {"ruta": "asfalto", "cros": "cross", "trail": "trail"}
URLS = [URL.format(m) for m in MODALIDADES]
_ISLAS = {"#ff9900": "Mallorca", "#00ff5e": "Menorca", "#00bfff": "Eivissa", "#00f2ff": "Formentera"}
# Controles, ligas de pista, finales escolares… no son carreras populares.
_NO_POPULAR = re.compile(r"^(me|ma|ei|fo)?\s*-?\s*(control|jornada|final insular)|\bcontrol (cros|pista)\b|"
                         r"\bjornada de lliga\b|\batletisme adaptat\b|\bpista\b")


def _eventos(contenido: bytes | str) -> list[dict]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    m = re.search(r"var calendar_data = (\{.*?\});\s*\n", html, re.S)
    return json.loads(m.group(1)).get("events", []) if m else []


def leer(paginas: list[bytes | str]) -> tuple[list[Carrera], list[str]]:
    """`paginas` en el mismo orden que URLS (ruta, cros, trail)."""
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set = set()
    for pagina, modalidad_pagina in zip(paginas, MODALIDADES.values()):
        for ev in _eventos(pagina):
            url = ev.get("permalink") or ""
            if url in vistas:
                continue
            vistas.add(url)
            nombre = nz.nombre(re.sub(r"\s+", " ", ev.get("title") or ""))
            # «Cursa S’Hostal 2026 – Campeonato IB … de Media Maratón»: el campeonato va aparte del nombre.
            nombre = re.split(r"\s+[–-]\s+(?:campeonato|campionat|cto)\b", nombre, flags=re.I)[0].strip()
            dia = (ev.get("start") or "")[:10]
            if (dia, nz.clave(nombre)) in vistas:  # varias pruebas de un mismo evento («3 Días Trail Ibiza»)
                continue
            vistas.add((dia, nz.clave(nombre)))
            if _NO_POPULAR.search(nz.clave(nombre)):
                descartes.append(f"control o competición de pista, no popular: {nombre}")
                continue
            if solo_infantil(nombre):
                descartes.append(f"solo infantil: {nombre}")
                continue
            a_pie, modalidad = nz.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            if modalidad_pagina and modalidad in (None, "asfalto"):
                modalidad = modalidad_pagina
            inicio = datetime.fromisoformat(ev["start"][:19])
            c = Carrera(
                nombre=nombre,
                fecha=inicio.date(),
                fuente=Fuente(ID, url),
                # La FAIB pone la hora local con «+00:00»; las 00:xx son «sin hora».
                hora=f"{inicio:%H:%M}" if inicio.hour >= 6 else None,
                poblacion=municipio(nombre),
                provincia=PROVINCIA,
                modalidad=modalidad,
                distancias_km=nz.distancias_del_nombre(nombre),
            )
            if not c.poblacion:
                isla = _ISLAS.get((ev.get("color") or "").lower())
                if isla == "Formentera":
                    c.poblacion = "Formentera"
                else:
                    c.marcar(f"Municipio no indicado en la FAIB (isla: {isla or '¿?'})", "pendiente_cartel")
            c.marcar("Cierre de inscripción en el reglamento de la FAIB", "pendiente_cartel")
            carreras.append(c)
    return carreras, descartes
