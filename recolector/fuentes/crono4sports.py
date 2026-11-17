"""Crono4Sports (Safor, Valencia, Alicante, Castellón): listado `crono4sports.com/eventos` (Livewire;
sin JS salen las 12 primeras) más la portada, que a veces enseña alguna más. Cada tarjeta trae nombre,
día y mes (sin año), «Población, Provincia» y una etiqueta (Running, Trail, Natación, OCR, Híbrido, Sup).
La ficha `/evento/<slug>` da la fecha con año, la hora, las distancias («Adultos · 8500 mts») y la
apertura y el cierre de inscripción de cada prueba. robots.txt lo permite todo menos historico, clasificacion
e inscritos (que no se leen)."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from fuentes import levante
from nucleo.modelo import Carrera, Fuente

ID = "crono4sports"
URL = "https://crono4sports.com/eventos"
PORTADA = "https://crono4sports.com/"

_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
          "sep": 9, "oct": 10, "nov": 11, "dic": 12}
_ETIQUETAS_NO_A_PIE = {"natacion", "hibrido", "sup"}
_FECHA_HORA = re.compile(r"(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})")


def tarjetas(*paginas: bytes | str) -> list[dict]:
    """Tarjetas de eventos del listado y de la portada, sin repetir enlaces."""
    vistas: dict[str, dict] = {}
    for contenido in paginas:
        sopa = BeautifulSoup(contenido, "html.parser")
        for card in sopa.select('div[wire\\:key^="ev-"]'):
            titulo = card.select_one("h3")
            enlace = card.select_one('a[href*="/evento/"]')
            if not (titulo and enlace) or enlace["href"] in vistas:
                continue
            etiqueta = card.select_one("span.absolute.top-2.left-2")
            dia_mes = card.select_one("span.absolute.top-2.right-2")
            lugar = card.select_one("i.ti-map-pin")
            vistas[enlace["href"]] = {
                "url": enlace["href"],
                "nombre": titulo.get_text(" ", strip=True),
                "etiqueta": etiqueta.get_text(strip=True) if etiqueta else "",
                "dia_mes": dia_mes.get_text(" ", strip=True) if dia_mes else "",
                "lugar": lugar.parent.get_text(" ", strip=True) if lugar else "",
            }
        # Carrusel de la portada: tarjetas `<a>` con etiqueta, fecha con año y población (sin provincia).
        for enlace in sopa.select('a.group[href*="/evento/"]'):
            titulo = enlace.select_one("h3")
            if not titulo or enlace["href"] in vistas:
                continue
            etiqueta = enlace.select_one("span.self-start")
            dia_mes = enlace.select_one("i.ti-calendar")
            lugar = enlace.select_one("i.ti-map-pin")
            vistas[enlace["href"]] = {
                "url": enlace["href"],
                "nombre": titulo.get_text(" ", strip=True),
                "etiqueta": etiqueta.get_text(strip=True) if etiqueta else "",
                "dia_mes": dia_mes.parent.get_text(" ", strip=True) if dia_mes else "",
                "lugar": lugar.parent.get_text(" ", strip=True) if lugar else "",
            }
    return list(vistas.values())


def _fecha_listado(dia_mes: str, hoy: date) -> Optional[date]:
    m = re.match(r"(\d{1,2})\s+(\w{3})\w*(?:\s+(\d{4}))?", nz.clave(dia_mes))
    if not m or m.group(2) not in _MESES:
        return None
    mes = _MESES[m.group(2)]
    anyo = int(m.group(3)) if m.group(3) else hoy.year + (1 if mes < hoy.month - 1 else 0)  # «6 ENE» visto en noviembre → año siguiente
    return date(anyo, mes, int(m.group(1)))


def _lugar(texto: str) -> tuple[Optional[str], Optional[str]]:
    texto = re.sub(r"\s+", " ", texto).strip()
    poblacion, coma, provincia = texto.rpartition(",")
    if not coma:  # solo la población (carrusel de la portada); la provincia sale de la ficha
        return nz.poblacion(texto), None
    return nz.poblacion(poblacion.strip()), nz.provincia(provincia.strip())


def leer_ficha(contenido: bytes | str, c: Carrera) -> None:
    """Completa la carrera con la fecha exacta, la hora, distancias y plazos de la ficha."""
    sopa = BeautifulSoup(contenido, "html.parser")
    cabecera = sopa.select_one("h1")
    caja = cabecera.find_next("div") if cabecera else None
    if caja:
        for span in caja.find_all("span"):
            icono = span.find("i")
            texto = span.get_text(" ", strip=True)
            clases = " ".join(icono.get("class", [])) if icono else ""
            if "ti-calendar" in clases:
                m = re.match(r"(\d{1,2}) (\w{3})\w* (\d{4})", nz.clave(texto))
                if m and m.group(2) in _MESES:
                    c.fecha = date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
            elif "ti-clock" in clases:
                m = re.search(r"(\d{1,2}):(\d{2})", texto)
                if m:
                    c.hora = f"{int(m.group(1)):02d}:{m.group(2)}"
            elif "ti-map-pin" in clases:
                poblacion, provincia = _lugar(texto)
                c.poblacion = poblacion or c.poblacion
                c.provincia = provincia or c.provincia
    texto = sopa.get_text(" ", strip=True)
    kms = []
    for valor, unidad in re.findall(r"·\s*(\d+(?:[.,]\d+)?)\s*(mts|m|km)\b", texto, re.I):
        km = float(valor.replace(",", ".")) / (1000 if unidad.lower() in ("mts", "m") else 1)
        if km >= 1:  # las de menores (cientos de metros) no cuentan
            kms.append(round(km, 3))
    if kms:
        c.distancias_km = sorted(set(kms))
    aperturas = [datetime(int(a), int(m), int(d), int(h), int(mi))
                 for d, m, a, h, mi in re.findall(r"Apertura:\s*" + _FECHA_HORA.pattern, texto)]
    cierres = [datetime(int(a), int(m), int(d), int(h), int(mi))
               for d, m, a, h, mi in re.findall(r"Cierre:\s*" + _FECHA_HORA.pattern, texto)]
    if aperturas:
        c.inscripcion_desde = min(aperturas)
    if cierres:
        c.inscripcion_hasta = max(cierres)


def leer(*paginas: bytes | str, descargar_ficha: Optional[Callable[[str], bytes]] = None,
         hoy: Optional[date] = None) -> tuple[list[Carrera], list[str]]:
    """`paginas`: el listado /eventos y la portada. Con `descargar_ficha` se abre la ficha de cada carrera a pie."""
    hoy = hoy or date.today()
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for t in tarjetas(*paginas):
        nombre = nz.nombre(t["nombre"])
        etiqueta = nz.clave(t["etiqueta"])
        a_pie, modalidad = levante.clasificar(nombre, t["etiqueta"] if etiqueta in ("trail", "ocr") else None)
        if etiqueta in _ETIQUETAS_NO_A_PIE or re.search(r"\b(bany|bano|travess?ia)\b", nz.clave(nombre)):
            a_pie = False
        if not a_pie:
            descartes.append(f"no es a pie: {nombre} ({t['etiqueta'] or 'sin etiqueta'})")
            continue
        poblacion, provincia = _lugar(t["lugar"])
        fecha = _fecha_listado(t["dia_mes"], hoy)
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, t["url"]), poblacion=poblacion,
                    provincia=provincia, modalidad=modalidad if etiqueta != "ocr" else "obstáculos",
                    distancias_km=levante.distancias(nombre), url_inscripcion=t["url"])
        if descargar_ficha:
            try:
                leer_ficha(descargar_ficha(t["url"]), c)
            except Exception as error:  # la ficha rota no tumba el listado
                c.marcar(f"No se pudo leer la ficha de Crono4Sports: {error}", "pendiente_cartel")
        if not c.provincia:
            descartes.append(f"fuera de España o sin provincia: {nombre} ({t['lugar']})")
            continue
        if not c.inscripcion_hasta:
            c.marcar("Cierre de inscripción en la ficha de Crono4Sports", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
