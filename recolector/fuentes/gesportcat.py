"""Gesport (gesport.cat, Maresme): organización, inscripciones y cronometraje. Lleva el Circuit Maresmenc de Cros
(Consell Esportiu del Maresme y ayuntamientos: Canet, Santa Susanna, Tordera, Calella, Arenys, Llavaneres, Pineda,
Malgrat, Alella) y carreras sueltas del Maresme (5K de Sant Vicenç de Montalt, Caldes 3 Viles…).
Se leen dos páginas: el calendario del circuito (`/circuit-maresmenc-cros/`, una línea por cros: «Dissabte 28 de
novembre 2026. 9è Cros de Pineda») y la portada («Properes curses»: enlace a la página de la carrera y fecha);
de cada carrera suelta se abre su página solo para el título. No es «GESport Canarias» (`gesport`).
robots.txt solo prohíbe /wp-admin/."""
from __future__ import annotations

import re
from datetime import date
from typing import Callable, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "gesportcat"
URL = "https://gesport.cat/"
URL_CIRCUIT = "https://gesport.cat/circuit-maresmenc-cros/"
CIRCUIT = "Circuit Maresmenc de Cros"
_FECHA = re.compile(r"(\d{1,2}) (?:de |d['’ ]?)?([a-zç]{3,})(?: de)? (\d{4})")  # tras nz.clave, «d’» → «d »
# Los cros del circuito se llaman por el nombre corto del pueblo («Cros de Pineda», «Cros dels Arenys»).
_PUEBLOS_MARESME = {
    "pineda": "Pineda de Mar", "malgrat": "Malgrat de Mar", "canet": "Canet de Mar", "arenys": "Arenys de Mar",
    "llavaneres": "Sant Andreu de Llavaneres", "premia": "Premià de Mar", "vilassar": "Vilassar de Mar",
}
_NO_ES_CARRERA = ("circuit", "wp-content", "inscripcions-resultats", "cronometratge", "contacte", "qui-som",
                  "serveis", "curses", "politica", "mi-cuenta", "feed", "wp-json")


def _fecha(texto: str) -> Optional[date]:
    m = _FECHA.search(nz.clave(texto))
    if not m:
        return None
    mes = cat.MESES.get(m.group(2)[:3])
    return date(int(m.group(3)), mes, int(m.group(1))) if mes else None


def _municipio(nombre: str) -> Optional[tuple[str, str]]:
    k = nz.clave(nombre)
    for corto, oficial in _PUEBLOS_MARESME.items():
        if re.search(rf"\b(de |d |dels |del )?{corto}\b", k) and not re.search(rf"{corto} (de|d) ", k):
            return cat.municipio(oficial)
    return cat.municipio_en(nombre)


def _carrera(nombre: str, fecha: date, url: str, inscripcion: str) -> tuple[Optional[Carrera], Optional[str]]:
    nombre = nz.nombre(cat.texto(nombre))
    a_pie, modalidad = cat.clasificar(nombre)
    if not a_pie:
        return None, f"no es a pie: {nombre}"
    if cat.es_infantil(nombre):
        return None, f"infantil: {nombre}"
    oficial = _municipio(nombre)
    if not oficial:
        return None, f"sin municipio: {nombre}"
    c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, url), poblacion=oficial[0], provincia=oficial[1],
                modalidad=modalidad, distancias_km=cat.distancias(nombre), url_inscripcion=inscripcion)
    c.marcar("Cierre de inscripción en la web de Gesport", "pendiente_cartel")
    return c, None


def leer_circuit(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    """Calendario del Circuit Maresmenc de Cros: una carrera por línea; las «AJORNAT» (aplazadas) no."""
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for li in sopa.select("li"):
        texto = cat.texto(li.get_text(" ", strip=True))
        fecha = _fecha(texto)
        if not fecha or "cros" not in nz.clave(texto):
            continue
        resto = re.split(r"\b\d{4}\b\s*\.?", texto, maxsplit=1)[-1]  # lo que va tras el año
        nombre = re.split(r"\.\s+|\s+Reglament", resto.strip(" ."), maxsplit=1)[0].strip(" .")
        if "ajornat" in nz.clave(texto) or "anul" in nz.clave(texto):
            descartes.append(f"aplazada o anulada: {nombre}")
            continue
        c, motivo = _carrera(nombre, fecha, URL_CIRCUIT, URL_CIRCUIT)
        if c:
            c.previos.append(f"Puntúa en: {CIRCUIT}")
            carreras.append(c)
        else:
            descartes.append(motivo)
    return carreras, descartes


def enlaces_portada(contenido: bytes | str) -> list[tuple[str, date]]:
    """«Properes curses» de la portada: (página de la carrera en gesport.cat, fecha). La fecha va después de los
    enlaces de su bloque, así que se asigna al último enlace de carrera visto; las de webs ajenas no se leen."""
    texto = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    inicio = texto.find("Properes curses")
    fin = texto.find("CRONOMETRATGE", inicio)
    bloque = texto[inicio:fin if fin > 0 else None] if inicio >= 0 else ""
    pares: list[tuple[str, date]] = []
    ultimo: Optional[str] = None
    for m in re.finditer(r'href="([^"]+)"|>([^<>]{6,40})<', bloque):
        if m.group(1):
            url = m.group(1)
            web = urlparse(url)
            ultimo = url if web.netloc == "gesport.cat" and web.path.strip("/") and \
                not any(p in web.path for p in _NO_ES_CARRERA) else None
        elif ultimo:
            fecha = cat.fecha(cat.texto(m.group(2))) or _fecha(cat.texto(m.group(2)))
            if fecha and not re.search(r"\d+ i \d+", m.group(2)):
                if ultimo not in [u for u, _ in pares]:
                    pares.append((ultimo, fecha))
                ultimo = None
    return pares


def titulo_pagina(contenido: bytes | str) -> Optional[str]:
    sopa = BeautifulSoup(contenido, "html.parser")
    t = sopa.title.get_text(" ", strip=True) if sopa.title else ""
    t = re.sub(r"\s*[–\-]\s*Gesport\s*$", "", cat.texto(t)).strip()
    return t or None


def leer(portada: bytes | str, circuit: bytes | str, *, descargar_ficha: Callable[[str], bytes]
         ) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = leer_circuit(circuit)
    for url, fecha in enlaces_portada(portada):
        nombre = titulo_pagina(descargar_ficha(url))
        if not nombre:
            descartes.append(f"sin título: {url}")
            continue
        c, motivo = _carrera(nombre, fecha, url, url)
        if c:
            carreras.append(c)
        else:
            descartes.append(motivo)
    return carreras, descartes
