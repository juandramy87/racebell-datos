"""Curses.cat (cronometrador de Girona): «Calendari de curses i marxes» con las próximas ~30 pruebas, casi
todas de Girona y el Empordà. Cada `article.cc-cursa` trae nombre, fecha «Dijous 03/12/2026», lugar,
distancias, tipo (`data-tipus`: trail, cursa popular, urbana, marxa, btt…) y enlace a su web.
Las marchas, caminadas y BTT se descartan (salvo «cursa i marxa»)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "cursescat"
URL = "https://www.curses.cat/calendari/"


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for art in sopa.select("article.cc-cursa"):
        enlace = art.select_one("a.cc-nom")
        if not enlace:
            continue
        nombre = nz.nombre(cat.texto(enlace.get_text(" ", strip=True)))
        tipo = cat.texto(art.get("data-tipus"))
        datos = {}
        for span in art.select(".cc-meta span"):
            icono = span.find("i")
            clase = " ".join(icono.get("class", [])) if icono else ""
            clave = "fecha" if "calendar" in clase else "lugar" if "geo" in clase else "distancias" if "signpost" in clase else None
            if clave:
                datos[clave] = cat.texto(span.get_text(" ", strip=True))
        fecha = cat.fecha(datos.get("fecha", ""))
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        a_pie, modalidad = cat.clasificar(nombre, tipo)
        if not a_pie or cat.es_infantil(nombre):
            descartes.append(f"no es a pie o infantil: {nombre} ({tipo})")
            continue
        if re.search(r"\bvirtual\b", nz.clave(nombre)):
            descartes.append(f"virtual: {nombre}")
            continue
        lugar = cat.municipio(datos.get("lugar")) or cat.municipio_en(nombre)
        if not lugar:
            descartes.append(f"sin población reconocible: {nombre} ({datos.get('lugar')})")
            continue
        web = enlace.get("href") or URL
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            # Muchas carreras enlazan solo a la portada de curses.cat: la ficha es entonces el calendario.
            fuente=Fuente(ID, web if web.rstrip("/") != "https://www.curses.cat" else URL),
            poblacion=lugar[0],
            provincia=lugar[1],
            modalidad=modalidad,
            distancias_km=sorted(set(cat.distancias(nombre)) | set(_km(datos.get("distancias", "")))),
        )
        c.marcar("Inscripción y cierre en la web de la carrera", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes


def _km(texto: str) -> list[float]:
    """«6km, 13km , 22km I 46KM» → [6, 13, 22, 46]; «10 km, 5 km» → [5, 10]."""
    kms = [float(x.replace(",", ".")) for x in re.findall(r"(\d{1,3}(?:[.,]\d)?) ?k(?:m|\b)", texto.lower())]
    return [{21.0: 21.097, 42.0: 42.195}.get(k, k) for k in kms]
