"""Federación Navarra de Atletismo (fnaf.es/calendario): tabla con fecha, tipo (Ruta, Cross, Trail
Running, Pista…), ámbito (Autonómico, JDN = Juegos Deportivos de Navarra…), nombre y lugar. Sin
robots.txt. Solo se lee la primera página (unas 10 competiciones, ~5 semanas desde hoy): las demás
se piden con «postback» de ASP.NET y no con un enlace. Fuera pista, JDN (escolares) y marcha."""
from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "fnaf"
URL = "https://www.fnaf.es/calendario"

_TIPO_MODALIDAD = {"ruta": "asfalto", "cross": "cross", "trail running": "trail"}


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for fila in sopa.select("tr"):
        celdas = [td.get_text(" ", strip=True) for td in fila.find_all("td", recursive=False)]
        if len(celdas) < 6 or not (m := re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", celdas[1])):
            continue
        tipo, ambito, nombre, lugar = celdas[2], celdas[3], nz.nombre(celdas[4]), celdas[5]
        modalidad = _TIPO_MODALIDAD.get(nz.clave(tipo))
        if not modalidad:
            descartes.append(f"no es carrera a pie de calle o monte: {nombre} ({tipo})")
            continue
        if nz.clave(ambito) == "jdn" or re.search(r"\b(jdn|escolar)", nz.clave(nombre)):
            descartes.append(f"escolar (JDN): {nombre}")
            continue
        a_pie, mod_nombre = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        enlace = next((a["href"] for a in fila.select("a[href]") if a["href"].startswith("http")), None)
        c = Carrera(
            nombre=nombre,
            fecha=datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date(),
            fuente=Fuente(ID, enlace or URL),
            poblacion=nz.poblacion(re.split(r"\s+o\s+|/", lugar)[0]) if lugar else None,
            provincia="Navarra",
            modalidad=mod_nombre if mod_nombre in ("montaña", "obstáculos", "cross", "trail") else modalidad,
            url_inscripcion=enlace,
            distancias_km=nz.distancias_del_nombre(nombre),
        )
        if "campeonato" in nz.clave(nombre) or re.match(r"cto\b", nz.clave(nombre)):
            c.marcar("Campeonato federado: confirmar que admite corredores populares", PENDIENTE_CARTEL)
        c.marcar("Hora, precio e inscripción en la normativa de la FNAF", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
