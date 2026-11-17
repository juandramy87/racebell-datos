"""CanaryRun (Tenerife, sur y oeste: Arona, San Miguel, Santiago del Teide, Vilaflor, Guía de Isora): organizador e
inscripciones de carreras y travesías. Su calendario es WordPress con «The Events Calendar», con API pública
`/wp-json/tribe/events/v1/events?start_date=…` (título, fecha y hora, categorías «Trail», «Carrera Urbana»,
«Travesía»…, lugar con código postal y la web del evento). La provincia sale del código postal; las travesías a
nado se descartan por la categoría. robots.txt (Yoast): `Disallow:` vacío, todo permitido."""
from __future__ import annotations

import html as html_mod
import json
import re
from datetime import date, datetime
from typing import Optional

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "canaryrun"
BASE = "https://www.canaryrun.com"
_CANARIAS = {"Las Palmas", "Santa Cruz de Tenerife"}
_NO_A_PIE = re.compile(r"\b(travesia|natacion|nado|swim|bike|btt)\b")


def url(desde: date) -> str:
    return f"{BASE}/wp-json/tribe/events/v1/events?per_page=50&start_date={desde.isoformat()}"


def _texto(fragmento: Optional[str]) -> str:
    return html_mod.unescape(re.sub(r"<[^>]+>", " ", fragmento or "")).strip()


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    datos = json.loads(contenido)
    carreras, descartes = [], []
    for ev in datos.get("events", []):
        nombre = nz.nombre(_texto(ev.get("title")))
        categorias = " ".join(c.get("name", "") for c in ev.get("categories") or [])
        a_pie, modalidad = nz.clasificar(nombre, categorias)
        if not a_pie or _NO_A_PIE.search(nz.clave(f"{nombre} {categorias}")):
            descartes.append(f"no es a pie: {nombre}")
            continue
        try:
            inicio = datetime.strptime(ev["start_date"][:16], "%Y-%m-%d %H:%M")
        except (KeyError, ValueError):
            descartes.append(f"sin fecha: {nombre}")
            continue
        lugar = ev.get("venue") if isinstance(ev.get("venue"), dict) else {}
        provincia = nz.provincia_por_cp(lugar.get("zip")) or nz.provincia(lugar.get("province"))
        if provincia not in _CANARIAS:
            descartes.append(f"fuera de Canarias o sin lugar: {nombre}")
            continue
        poblacion = None
        for texto in (lugar.get("city"), lugar.get("venue"), lugar.get("address")):
            hallado = nz.municipio_espana(texto)
            if hallado and hallado[1] == provincia:
                poblacion = hallado[0]
                break
        for org in ev.get("organizer") or []:  # «Ayuntamiento de San Miguel de Abona» cuando el lugar es un barrio
            m = re.search(r"ayuntamiento de (?:la villa (?:historica )?de )?(.+)$", nz.clave(org.get("organizer", "")))
            hallado = nz.municipio_espana(m.group(1)) if m and not poblacion else None
            if hallado and hallado[1] == provincia:
                poblacion = hallado[0]
        poblacion = poblacion or nz.poblacion(lugar.get("city") or lugar.get("venue"))
        web = (ev.get("website") or "").strip()
        ficha = ev.get("url") or BASE
        c = Carrera(nombre=nombre, fecha=inicio.date(), fuente=Fuente(ID, ficha),
                    hora=None if ev.get("all_day") or inicio.strftime("%H:%M") == "00:00" else inicio.strftime("%H:%M"),
                    poblacion=poblacion, provincia=provincia, modalidad=modalidad,
                    distancias_km=nz.distancias_del_nombre(nombre),
                    url_inscripcion=web if web.startswith("http") and web.rstrip("/") != BASE else ficha)
        if isinstance(ev.get("image"), dict) and ev["image"].get("url"):
            c.cartel = ev["image"]["url"]
        carreras.append(c)
    return carreras, descartes
