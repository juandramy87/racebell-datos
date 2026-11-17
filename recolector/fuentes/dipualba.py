"""Deportes Dipualba: inscripciones de los circuitos de la Diputación de Albacete (Circuito Provincial de
Carreras Populares y circuito de Trail). Listados `/deportes/pruebas-carreras-populares` y
`/deportes/pruebas-trail` con nombre, fecha, municipio y distancia; enlace a la ficha. Las páginas llevan
los carteles incrustados en base64 (varios MB): se quitan antes de guardar la copia. robots.txt: permite todo."""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "dipualba"
BASE = "https://deportes.dipualba.es"
URLS = {
    BASE + "/deportes/pruebas-carreras-populares": None,
    BASE + "/deportes/pruebas-trail": "trail",
}


def recortar(contenido: bytes) -> bytes:
    """Quita las imágenes incrustadas (data:…) para que la copia ocupe KB y no MB."""
    return re.sub(rb"data:[a-z]+/[a-z+.-]+;base64,[A-Za-z0-9+/=]+", b"", contenido)


def leer(paginas: Iterable[tuple[bytes | str, str | None]]) -> tuple[list[Carrera], list[str]]:
    """`paginas`: [(contenido, modalidad_por_defecto)], una por listado (carreras populares, trail)."""
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for contenido, modalidad_defecto in paginas:
        sopa = BeautifulSoup(contenido, "html.parser")
        for titulo in sopa.select("p.card-prueba-titulo-prueba a"):
            url = BASE + titulo["href"] if titulo["href"].startswith("/") else titulo["href"]
            if url in vistas:
                continue
            vistas.add(url)
            tarjeta = titulo.find_parent("div", class_=re.compile("align-content-end")) or titulo.parent.parent
            datos = [p.get_text(" ", strip=True) for p in tarjeta.select("li.card-prueba-lista-datos-prueba-item p")]
            nombre = nz.nombre(titulo.get_text(" ", strip=True))
            m = re.search(r"(\d{2})/(\d{2})/(\d{4})", " ".join(datos))
            if not m:
                descartes.append(f"sin fecha: {nombre}")
                continue
            a_pie, modalidad = nz.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            municipio = datos[1] if len(datos) > 1 and not re.search(r"\d", datos[1]) else None
            kms = []
            for d in datos:
                k = re.fullmatch(r"(\d{1,3}(?:[.,]\d{1,3})?) ?km", d.strip(), re.I)
                if k:
                    kms.append(float(k.group(1).replace(",", ".")))
            c = Carrera(
                nombre=nombre,
                fecha=date(int(m.group(3)), int(m.group(2)), int(m.group(1))),
                fuente=Fuente(ID, url),
                poblacion=nz.poblacion(municipio),
                provincia="Albacete",
                modalidad=modalidad_defecto or modalidad,
                distancias_km=sorted(set(kms) | set(nz.distancias_del_nombre(nombre))),
                url_inscripcion=url,
            )
            c.marcar("Cierre de inscripción en la ficha de Deportes Dipualba", "pendiente_cartel")
            carreras.append(c)
    return carreras, descartes
