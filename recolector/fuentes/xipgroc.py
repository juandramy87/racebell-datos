"""Championchip Catalunya (xipgroc.cat, el «xip groc»): calendario de las carreras que cronometra, casi todas
populares de asfalto y cros del área de Barcelona y algunas de Girona. Se piden las publicadas entre dos fechas
(`/ca/cursas?q[data_gteq]=…&q[data_lteq]=…`, 15 por página). Cada carrera trae nombre, fecha, web oficial,
icono de tipo («c» cursa, «v» trail/muntanya, «n» natació, «b» bici, «w» caminada) y las distancias con su
enlace de inscripción. NO trae el pueblo: se saca del nombre con la tabla de municipios catalanes.
Las clasificaciones («resultats») no se abren nunca."""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, PENDIENTE_CARTEL, Carrera, Fuente

ID = "xipgroc"
BASE = "https://xipgroc.cat/ca/cursas"
MAX_PAGINAS = 8
_ICONO_A_PIE = {"c": None, "v": "trail"}  # «n» natació, «b» bici, «w» caminada: fuera
# Casi todas son de Barcelona ciudad: barrios y carreras clásicas que no llevan el nombre del municipio.
_BARCELONA = re.compile(r"\b(sagrera|sant andreu|sant antoni|sant marti|clot|gracia|sants|sarria|poblenou|"
                        r"nou barris|horta|montjuic|jean bouin|nassos|mercabarna|diagonal|bombers barcelona)\b")


def url(desde: date, hasta: date, pagina: int = 1) -> str:
    q = {"q[data_gteq]": desde.isoformat(), "q[data_lteq]": hasta.isoformat(), "q[publicada_eq]": "1"}
    return BASE + "?" + urlencode(({"page": pagina} if pagina > 1 else {}) | q)


def otras_paginas(contenido: bytes | str, desde: date, hasta: date) -> list[str]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    numeros = sorted({int(n) for n in re.findall(r"[?&](?:amp;)?page=(\d+)", html)} - {1})
    return [url(desde, hasta, n) for n in numeros[:MAX_PAGINAS - 1]]


def leer(paginas: list[bytes | str]) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for pagina in paginas:
        sopa = BeautifulSoup(pagina, "html.parser")
        for art in sopa.select("article.cursa"):
            if art.get("id") in vistas:
                continue
            vistas.add(art.get("id"))
            titulo = art.select_one("a.title-link")
            parrafo = art.select_one(".cursa-content > p")
            if not (titulo and parrafo):
                continue
            nombre = nz.nombre(cat.texto(titulo.get_text(" ", strip=True)))
            fecha = cat.fecha(parrafo.get_text(" ", strip=True))
            if not fecha:
                descartes.append(f"sin fecha: {nombre}")
                continue
            icono = (art.select_one(".cursa-content > span.icon") or art).get_text(strip=True)[:1]
            if icono not in _ICONO_A_PIE or "swimming" in art.get("class", []):
                descartes.append(f"no es a pie (icono «{icono}»): {nombre}")
                continue
            if cat.es_infantil(nombre):
                descartes.append(f"infantil o escolar: {nombre}")
                continue
            a_pie, modalidad = cat.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            # Cada distancia es un enlace «…/inscripcio/…» (abierta) o «…/resultats…» (ya corrida).
            pruebas = [(cat.texto(a.get_text(" ", strip=True)), a["href"]) for a in art.select("a.main-link")]
            inscripcion = next((urljoin(BASE, h) for _, h in pruebas if "/inscripcio/" in h), None)
            oficial = (titulo.get("href") or "").strip() or None
            lugar = cat.municipio_en(nombre)
            if not lugar and _BARCELONA.search(nz.clave(nombre)):
                lugar = ("Barcelona", "Barcelona")
            c = Carrera(
                nombre=nombre,
                fecha=fecha,
                fuente=Fuente(ID, inscripcion or oficial or BASE),
                poblacion=lugar[0] if lugar else None,
                provincia=lugar[1] if lugar else None,
                modalidad=modalidad or _ICONO_A_PIE[icono],
                distancias_km=sorted(set(cat.distancias(nombre)) | {k for t, _ in pruebas for k in _km(t)}),
                url_inscripcion=inscripcion,
            )
            if not lugar:
                c.comunidad = "cataluna"  # Championchip Catalunya: sin pueblo en el listado
                c.marcar("Población no indicada en Championchip (solo el nombre de la carrera)", PENDIENTE_CARTEL)
            if inscripcion:
                c.estado_fuente = ABIERTA
            c.marcar("Cierre de inscripción en la web de la carrera", PENDIENTE_CARTEL)
            carreras.append(c)
    return carreras, descartes


def _km(texto: str) -> list[float]:
    """«12,3K» → [12.3]; «Mitja» → [21.097]; «Infantils», «Dorsal 0», «Caminada» → []."""
    t = nz.clave(texto)
    m = re.fullmatch(r"(\d{1,3}(?: \d)?) ?k(m)?", t.replace(",", " "))
    if m:
        km = float(m.group(1).replace(" ", "."))
        return [{21.0: 21.097, 42.0: 42.195}.get(km, km)]
    return [21.097] if t == "mitja" else []
