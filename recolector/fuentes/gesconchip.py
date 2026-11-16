"""Gesconchip: listado HTML de próximas pruebas (Cádiz, Sevilla, Málaga, Jaén).
Cada prueba trae «Población - Provincia», tipo (icono) y una cuenta atrás con la fecha y hora
del cierre de inscripción (o del próximo cambio de tarifa, según el título)."""
from __future__ import annotations

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "gesconchip"
URL = "https://gesconchip.es/proximas-pruebas"

_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
          "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for prueba in sopa.select("div.listado-pruebas div.prueba"):
        enlace = prueba.find_parent("a")
        nombre = nz.nombre(prueba.select_one(".nombre").get_text(" ", strip=True))
        dia = int(prueba.select_one(".dia").get_text(strip=True))
        mes = _MESES[nz.clave(prueba.select_one(".mes").get_text(strip=True))[:3]]
        anyo = int(prueba.select_one(".anyo").get_text(strip=True))
        tipos = [img.get("title", "") for img in prueba.select(".tipos-modalidad img")]
        # El icono de tipo manda: «Carrera», «Carrera Montaña/Trail»… Si no hay icono, el nombre.
        tipos_a_pie = [t for t in tipos if re.search(r"carrera|trail|cross|montana|running", nz.clave(t))]
        if tipos:
            a_pie = bool(tipos_a_pie) and not re.search(r"\b(mtb|btt|triatlon|acuatlon|travesia)", nz.clave(nombre))
            modalidad = nz.clasificar(nombre, *tipos_a_pie)[1]
        else:
            a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre} ({', '.join(tipos)})")
            continue
        poblacion, _, provincia = prueba.select_one(".lugar").get_text(" ", strip=True).rpartition(" - ")
        if not nz.provincia(provincia):
            descartes.append(f"fuera de Andalucía: {nombre} ({provincia})")
            continue
        c = Carrera(
            nombre=nombre,
            fecha=date(anyo, mes, dia),
            fuente=Fuente(ID, enlace["href"] if enlace else URL),
            poblacion=nz.poblacion(poblacion),
            provincia=nz.provincia(provincia),
            modalidad=modalidad,
            distancias_km=nz.distancias_del_nombre(nombre),
            url_inscripcion=enlace["href"] if enlace else None,
        )
        img = prueba.select_one(".cartel-grande img")
        if img and img.get("src"):
            c.cartel = img["src"]
        contador = prueba.select_one("input.contadoresFecha")
        titulo = prueba.select_one(".contador .titulo")
        if contador and contador.get("data-fecha"):
            cuando = datetime.fromisoformat(f"{contador['data-fecha']}T{contador.get('data-hora') or '23:59:00'}")
            if titulo and "cierre" in nz.clave(titulo.get_text()):
                c.inscripcion_hasta = cuando
            else:
                c.previos.append(f"Cambio de precio el {cuando:%d/%m} a las {cuando:%H:%M}")
        if not c.inscripcion_hasta:
            c.marcar("Cierre de inscripción en la ficha de Gesconchip", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
