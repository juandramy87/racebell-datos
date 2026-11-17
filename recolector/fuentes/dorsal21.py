"""Dorsal21 (cronometrador de Murcia; sus inscripciones van por BabelSport): portada `dorsal21.com`
con una tarjeta por prueba: `<time datetime>`, nombre, población, estado («Consultar inscripción»,
«Próximamente») y enlaces a reglamento e inscripción. No da provincia: Murcia salvo las poblaciones
conocidas de fuera (`levante`). Sin robots.txt (redirige a la portada)."""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fuentes import levante
from nucleo import normalizar as nz
from nucleo.modelo import NO_ABIERTA, Carrera, Fuente

ID = "dorsal21"
URL = "https://www.dorsal21.com/"
# Pruebas solo para menores («Cross Alcantarilla Benjamín Alevín Infantil»).
_MENORES = re.compile(r"\b(benjamin|alevin|infantil|prebenjamin|chupetin)\b")


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for art in sopa.select("article.d21-event"):
        titulo = art.select_one("h3")
        cuando = art.select_one("time[datetime]")
        if not (titulo and cuando):
            continue
        nombre = nz.nombre(re.sub(r"^cartel de\s+", "", titulo.get_text(" ", strip=True), flags=re.I))
        a_pie, modalidad = levante.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        if _MENORES.search(nz.clave(nombre)) and not re.search(r"\b(absoluto|popular|senior)\b", nz.clave(nombre)):
            descartes.append(f"solo para menores: {nombre}")
            continue
        lugar = art.select_one(".d21-location")
        poblacion = nz.poblacion(lugar.get_text(" ", strip=True)) if lugar else None
        inscribir = next((a["href"] for a in art.select(".d21-event-actions a[href]")
                          if "inscr" in nz.clave(a.get_text())), None)
        estado = nz.clave((art.select_one(".d21-status") or titulo).get_text())
        c = Carrera(
            nombre=nombre,
            fecha=date.fromisoformat(cuando["datetime"][:10]),
            fuente=Fuente(ID, inscribir or URL),
            poblacion=poblacion,
            provincia=levante.provincia_murciana(poblacion),
            modalidad=modalidad,
            distancias_km=levante.distancias(nombre),
            url_inscripcion=inscribir,
            estado_fuente=NO_ABIERTA if "proximamente" in estado else None,
        )
        cartel = art.select_one(".d21-poster img[src]")
        if cartel and "generico" not in cartel["src"]:
            c.cartel = urljoin(URL, cartel["src"])
        c.marcar("Hora y plazo de inscripción en la ficha de BabelSport/Dorsal21", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
