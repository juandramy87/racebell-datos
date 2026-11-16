"""Ola! Rivers (organizador y cronometrador: Málaga, Cádiz, Córdoba, Almería…). La página
`proximas-pruebas/` lista cada prueba con fecha, comunidad, provincia, tipo, lugar y la fecha de
fin de inscripción del contador (`data-date`). Solo se guardan las de Andalucía."""
from __future__ import annotations

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "olarivers"
URL = "https://olarivers.com/proximas-pruebas/"
_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def _campo(texto: str, etiqueta: str) -> str:
    m = re.search(rf"{etiqueta}:\s*(.*?)\s*(?:\n|$)", texto)
    return m.group(1).strip() if m else ""


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras, descartes, vistas = [], [], set()
    for bloque in sopa.select("div.list-evento"):
        titulo = bloque.select_one("a[href*='/eventos/']")
        fecha_p = titulo.find_next_sibling("p") if titulo else None
        datos = bloque.select_one(".boxright .boxleft") or bloque
        if not (titulo and fecha_p):
            continue
        url = titulo["href"]
        if url in vistas:  # las destacadas salen arriba y otra vez en su mes
            continue
        vistas.add(url)
        texto = datos.get_text("\n", strip=True).replace(":\n", ": ")
        nombre = nz.nombre(titulo.get_text(" ", strip=True))
        provincia = nz.provincia(_campo(texto, "Provincia"))
        if not provincia:
            continue  # resto de España
        tipo = _campo(texto, "Tipo de prueba")
        a_pie, modalidad = nz.clasificar(nombre, tipo)
        if not a_pie or nz.clave(tipo) in ("evento hibrido", "otras"):
            descartes.append(f"no es a pie: {nombre} ({tipo})")
            continue
        m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", fecha_p.get_text(" ", strip=True))
        if not m or nz.clave(m.group(2)) not in _MESES:
            descartes.append(f"fecha ilegible: {nombre}")
            continue
        c = Carrera(nombre=nombre, fecha=date(int(m.group(3)), _MESES[nz.clave(m.group(2))], int(m.group(1))),
                    fuente=Fuente(ID, url), poblacion=nz.poblacion(_campo(texto, "Lugar")), provincia=provincia,
                    modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=url)
        contador = bloque.select_one("[data-date]")
        if contador and contador["data-date"]:
            try:
                c.inscripcion_hasta = datetime.fromisoformat(contador["data-date"])
            except ValueError:
                pass
        if not c.inscripcion_hasta:
            c.marcar("Cierre de inscripción no indicado en el listado", "pendiente_cartel")
        if img := bloque.select_one("img.wp-post-image[src]"):
            c.cartel = img["src"]
        carreras.append(c)
    return carreras, descartes
