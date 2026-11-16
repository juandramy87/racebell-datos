"""Time2Run (cronometrador de Cazorla: Jaén, Granada, Córdoba, Sevilla). `eventos-proximos/` trae
nombre, fecha y enlace a la ficha. Si la ficha enlaza a la inscripción en RockTheSport, de su JSON-LD
salen hora, localidad, coordenadas y plazo (robots de RockTheSport prohíbe /api/ y las páginas de
registro: solo se lee la ficha pública). La provincia no la da ninguna de las dos: se deduce del
nombre o de la localidad cuando es una capital, y si no, queda pendiente."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Optional

from bs4 import BeautifulSoup

from fuentes import jsonld
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "time2run"
URL = "https://time2run.es/eventos-proximos/"
_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
          "sep": 9, "oct": 10, "nov": 11, "dic": 12}
_RTS = re.compile(r'href="https?://(?:www\.|web\.)?rockthesport\.com/(?:es/)?(?:evento|event)/([a-z0-9\-]+)')


def eventos(contenido: bytes | str) -> list[dict]:
    sopa = BeautifulSoup(contenido, "html.parser")
    salida = []
    for art in sopa.select("article"):
        titulo = art.select_one(".entry-title a, .qodef-e-title a")
        fecha = art.select_one(".qodef-e-info-date")
        m = re.search(r"(\d{1,2})\s+(\w{3})\w*\s+(\d{2,4})", fecha.get_text(" ", strip=True)) if fecha else None
        if not (titulo and m and nz.clave(m.group(2)) in _MESES):
            continue
        anyo = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
        categoria = next((k[9:] for k in art.get("class", []) if k.startswith("category-")), "")
        salida.append({"nombre": nz.nombre(titulo.get_text(" ", strip=True)), "url": titulo["href"],
                       "fecha": date(anyo, _MESES[nz.clave(m.group(2))], int(m.group(1))), "categoria": categoria})
    return salida


def enlace_rockthesport(ficha: bytes | str) -> Optional[str]:
    html = ficha.decode("utf-8", "replace") if isinstance(ficha, bytes) else ficha
    m = _RTS.search(html)
    return f"https://web.rockthesport.com/es/event/{m.group(1)}" if m else None


def _provincia_de(*textos: Optional[str]) -> Optional[str]:
    for texto in textos:
        for palabra in nz.clave(texto).split():
            if p := nz.provincia(palabra):
                return p
    return None


def completar_con_rockthesport(c: Carrera, contenido: bytes | str, url: str) -> None:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    evs = jsonld.eventos(html)
    if not evs:
        return
    ev = evs[0]
    c.url_inscripcion = url
    inicio = datetime.fromisoformat(ev["startDate"][:19])
    if inicio.date() != c.fecha:
        c.marcar(f"Time2Run da el {c.fecha:%d/%m} y RockTheSport el {inicio:%d/%m}")
    if inicio.strftime("%H:%M") != "00:00":
        c.hora = inicio.strftime("%H:%M")
    lugar = ev.get("location") or {}
    localidad = ((lugar.get("address") or {}).get("addressLocality") or lugar.get("name") or "")
    c.poblacion = nz.poblacion(localidad.split(",")[-1]) or c.poblacion  # «Plaza Mayor, 1, Güejar Sierra»
    if geo := lugar.get("geo"):
        try:
            c.coords = (float(geo["latitude"]), float(geo["longitude"]))
        except (KeyError, TypeError, ValueError):
            pass
    oferta = ev.get("offers") or {}
    oferta = oferta[0] if isinstance(oferta, list) and oferta else oferta
    for campo, destino in (("validFrom", "inscripcion_desde"), ("validThrough", "inscripcion_hasta")):
        if oferta.get(campo):
            setattr(c, destino, datetime.fromisoformat(oferta[campo][:19]))
    if "SoldOut" in str(oferta.get("availability", "")):
        c.previos.append("Inscripciones agotadas")
    if isinstance(ev.get("image"), str):
        c.cartel = ev["image"]


def leer(contenido: bytes | str, *, descargar_ficha: Callable[[str], bytes],
         descargar_rockthesport: Callable[[str], bytes]) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = [], []
    for ev in eventos(contenido):
        a_pie, modalidad = nz.clasificar(ev["nombre"], {"ocr": "ocr"}.get(ev["categoria"]))
        if not a_pie or ev["categoria"] == "fitness":  # «fitness»: pruebas híbridas, no cuentan
            descartes.append(f"no es a pie: {ev['nombre']} ({ev['categoria']})")
            continue
        c = Carrera(nombre=ev["nombre"], fecha=ev["fecha"], fuente=Fuente(ID, ev["url"]), modalidad=modalidad,
                    distancias_km=nz.distancias_del_nombre(ev["nombre"]), url_inscripcion=ev["url"])
        if rts := enlace_rockthesport(descargar_ficha(ev["url"])):
            completar_con_rockthesport(c, descargar_rockthesport(rts), rts)
        c.provincia = _provincia_de(c.poblacion, c.nombre)
        if not c.provincia:
            c.marcar("Provincia sin indicar en Time2Run: confirmarla", "pendiente_cartel")
        if not c.poblacion:
            c.marcar("Población sin indicar en Time2Run (ver el reglamento)", "pendiente_cartel")
        if not c.inscripcion_hasta:
            c.marcar("Cierre de inscripción no indicado en la fuente", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
