"""Ruta 091: circuito de carreras solidarias de la Policía Nacional (Córdoba, Écija, Elche…).
Una sola página con todas: nombre («Carrera Solidaria Ruta 091 <Ciudad> <año>»), estado, fecha y
hora, lugar de salida y distancias. La ciudad sale del nombre; solo se guardan las andaluzas."""
from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, NO_ABIERTA, Carrera, Fuente

ID = "ruta091"
URL = "https://ruta091.es/carreras"
# Ciudades del circuito que no son capital de provincia.
_PROVINCIA_DE = {"ecija": "Sevilla", "jerez de la frontera": "Cádiz", "algeciras": "Cádiz", "marbella": "Málaga",
                 "linares": "Jaén", "motril": "Granada", "el ejido": "Almería", "lucena": "Córdoba"}
_ESTADOS = {"abierto": ABIERTA, "cerrado": CERRADA, "finalizado": CERRADA, "proximamente": NO_ABIERTA}


def _km(texto: str) -> list[float]:
    """«Adultos 6,3 Km. - 11- 15 años 800 m.» → [6.3] (las de niños no cuentan)."""
    return sorted({float(x.replace(",", ".")) for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*km", texto, re.I)})


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras, descartes = [], []
    for bloque in sopa.select("div.single-product"):
        titulo = bloque.select_one(".product-price h2")
        cuando = bloque.select_one(".icon-time")
        if not (titulo and cuando):
            continue
        nombre = nz.nombre(titulo.get_text(" ", strip=True))
        m = re.search(r"Ruta 091\s+(.+?)\s+\d{4}\s*$", nombre)
        ciudad = m.group(1) if m else ""
        provincia = nz.provincia(ciudad) or _PROVINCIA_DE.get(nz.clave(ciudad))
        if not provincia:
            continue  # Elche, Pamplona, Melilla…: fuera de nuestra zona
        f = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2})", cuando.parent.get_text(" ", strip=True))
        if not f:
            descartes.append(f"sin fecha: {nombre}")
            continue
        inicio = datetime.strptime(f"{f.group(1)} {f.group(2)}", "%d/%m/%Y %H:%M")
        estado = bloque.select_one(".sale-flash")
        enlace = next((a["href"] for a in bloque.select("a[href]") if "inscrip" in a["href"]), None)
        c = Carrera(nombre=nombre, fecha=inicio.date(), hora=inicio.strftime("%H:%M"), fuente=Fuente(ID, URL),
                    poblacion=ciudad, provincia=provincia, modalidad="asfalto", url_inscripcion=enlace or URL,
                    estado_fuente=_ESTADOS.get(nz.clave(estado.get_text()) if estado else ""))
        if road := bloque.select_one(".icon-road"):
            c.distancias_km = _km(road.parent.get_text(" ", strip=True))
        if img := bloque.select_one(".product-image img[src]"):
            c.cartel = urljoin(URL, img["src"])
        c.marcar("Cierre de inscripción no indicado (ver el reglamento)", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
