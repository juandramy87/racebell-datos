"""CronoSports (cronosports.com): inscripciones y cronometraje de carreras populares y trails del Maresme,
el Bages y Girona. La portada lista las próximas («race-card»: nombre, «📍 pueblo», fecha y hora, tipo y
precio desde). Cada ficha `/evento/<slug>` trae «Inscripcions: del dd/mm/aaaa hh:mm al dd/mm/aaaa hh:mm»."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "cronosports"
URL = "https://cronosports.com/"
_PLAZO = re.compile(r"Inscripcions:\s*del\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})\s*al\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})")


def leer(contenido: bytes | str, descargar_ficha: Optional[Callable[[str], bytes]] = None) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for tarjeta in sopa.select("div.race-card"):
        enlace = tarjeta.select_one(".race-foot a.btn")
        titulo = tarjeta.select_one("h3")
        if not (enlace and titulo):
            continue  # «Historial de curses» (ya corridas, enlazan a resultados): no se leen
        nombre = nz.nombre(cat.texto(titulo.get_text(" ", strip=True)))
        meta = [cat.texto(s.get_text(" ", strip=True)) for s in tarjeta.select(".race-meta span")]
        pueblo = next((m.replace("📍", "").strip() for m in meta if "📍" in m), None)
        cuando = next((m for m in meta if "📅" in m), "")
        tipo = next((m.replace("🏁", "").strip() for m in meta if "🏁" in m), "")
        fecha = cat.fecha(cuando)
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        a_pie, modalidad = cat.clasificar(nombre, tipo)
        if not a_pie or cat.es_infantil(nombre):
            descartes.append(f"no es a pie o infantil: {nombre} ({tipo})")
            continue
        lugar = cat.municipio(pueblo) or cat.municipio_en(f"{pueblo} {nombre}")
        if not lugar:
            descartes.append(f"sin población reconocible: {nombre} ({pueblo})")
            continue
        url = urljoin(URL, enlace["href"])
        hora = re.search(r"(\d{1,2}:\d{2})\s*h", cuando)
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, url),
            hora=hora.group(1).zfill(5) if hora else None,
            poblacion=lugar[0],
            provincia=lugar[1],
            modalidad=modalidad,
            distancias_km=cat.distancias(nombre),
            url_inscripcion=url,
            cartel=urljoin(URL, f"{enlace['href'].rstrip('/')}/poster"),
        )
        precio = tarjeta.select_one(".race-price")
        euros = re.search(r"(\d+(?:,\d+)?)\s*€", cat.texto(precio.get_text(" ", strip=True)) if precio else "")
        if euros and float(euros.group(1).replace(",", ".")) > 0:
            c.precios.append({"nombre": "Desde", "euros": float(euros.group(1).replace(",", "."))})
        if descargar_ficha:
            leer_plazo(c, descargar_ficha(url))
        if not c.inscripcion_hasta:
            c.marcar("Cierre de inscripción en la ficha de CronoSports", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes


def leer_plazo(c: Carrera, ficha: bytes | str) -> None:
    html = ficha.decode("utf-8", "replace") if isinstance(ficha, bytes) else ficha
    m = _PLAZO.search(re.sub(r"<[^>]+>", " ", html))
    if m:
        c.inscripcion_desde = datetime.strptime(m.group(1), "%d/%m/%Y %H:%M")
        c.inscripcion_hasta = datetime.strptime(m.group(2), "%d/%m/%Y %H:%M")
