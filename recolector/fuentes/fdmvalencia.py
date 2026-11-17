"""Fundación Deportiva Municipal de València: calendario del Circuit de Carreres Caixa Popular y del
resto de carreras de la ciudad (`carreras.fdmvalencia.es/es/calendario/`, WordPress + JetEngine).
Cada bloque trae fecha «dd/mm/aaaa», hora «8:30 h», nombre, «Distancia: …» y el enlace «Más información».
Todas son en València capital. robots.txt solo prohíbe /wp-admin/."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from fuentes import levante
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "fdmvalencia"
URL = "https://carreras.fdmvalencia.es/es/calendario/"
OTRAS = "https://carreras.fdmvalencia.es/es/otras-carreras/"


def _km(texto: str) -> list[float]:
    t = texto.replace(".", "").replace(",", ".") if re.search(r"\d\.\d{3}\s*m", texto) else texto.replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(km|k|m)\b", t, re.I)
    if not m:
        return []
    valor = float(m.group(1))
    return [round(valor / 1000, 3) if m.group(2).lower() == "m" else valor]


def leer(*paginas: bytes | str) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[tuple[str, date]] = set()
    for contenido in paginas:
        sopa = BeautifulSoup(contenido, "html.parser")
        for item in sopa.select("div.jet-listing-grid__item"):
            texto = item.get_text(" ", strip=True)
            fecha_m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", texto)
            titulo = item.select_one("div.elementor-heading-title")
            if not (fecha_m and titulo):
                continue
            nombre = nz.nombre(titulo.get_text(" ", strip=True))
            fecha = date(int(fecha_m.group(3)), int(fecha_m.group(2)), int(fecha_m.group(1)))
            if (nz.clave(nombre), fecha) in vistas:
                continue
            vistas.add((nz.clave(nombre), fecha))
            distancia = re.search(r"Distancia:\s*([^|]+?)(?:\s{2,}|$)", " ".join(
                s.get_text(" ", strip=True) for s in item.select("span.elementor-heading-title")))
            distancia_txt = distancia.group(1) if distancia else ""
            a_pie, modalidad = levante.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            if re.search(r"\bedades\b", nz.clave(distancia_txt)) or re.search(r"\bmini\b", nz.clave(nombre)):
                descartes.append(f"solo para menores: {nombre}")
                continue
            hora_m = re.search(r"\b(\d{1,2}):(\d{2})\s*h\b", texto)
            enlace = next((a["href"] for a in item.select("a[href]") if "informaci" in nz.clave(a.get_text())
                           or "informacio" in nz.clave(a.get_text())), None)
            c = Carrera(
                nombre=nombre,
                fecha=fecha,
                fuente=Fuente(ID, enlace or URL),
                hora=f"{int(hora_m.group(1)):02d}:{hora_m.group(2)}" if hora_m else None,
                poblacion="Valencia",
                provincia="Valencia",
                modalidad=modalidad or "asfalto",
                distancias_km=sorted(set(_km(distancia_txt) + levante.distancias(nombre))),
            )
            img = item.select_one("img[src]")
            if img:
                c.cartel = img["src"]
            c.marcar("Plazo de inscripción en la web de la carrera (FDM València)", "pendiente_cartel")
            carreras.append(c)
    return carreras, descartes
