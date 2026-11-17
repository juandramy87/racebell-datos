"""Carrera de las Ciudades contra el Cáncer de Páncreas (`carreracancerpancreas.es`): carrera solidaria que se
celebra cada año en varias ciudades de España (2026: Elche, Vigo, Vilamartín de Valdeorras, Alicante, Madrid,
Santiago de Compostela y Barcelona). La portada trae el calendario de la edición:
`<span>2026</span>` y un `<h3><span class="strong">22 NOVIEMBRE</span> / MADRID</h3>` por ciudad.
Cada ciudad tiene su página (`/carrera-madrid/`, `/cursa-barcelona/carrera-barcelona/`), que se enlaza como
inscripción. La «Carrera virtual» (con la app, sin lugar) no se recoge.
Sirve para varias comunidades: Madrid, C. Valenciana, Galicia y Cataluña.
robots.txt: `Allow: /` para todos."""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "cancerpancreas"
URL = "https://carreracancerpancreas.es/"
_MESES = {m: i for i, m in enumerate(
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(), 1)}
# Grafías de la web que no son la oficial del INE.
_CIUDADES = {"villamartin de valdeorras": ("Vilamartín de Valdeorras", "Ourense")}


def _ciudad(texto: str) -> tuple[str | None, str | None]:
    """«VILLAMARTÍN DE VALDEORRAS - ORENSE» → («Vilamartín de Valdeorras», «Ourense»)."""
    partes = [p.strip() for p in re.split(r"\s+[-–]\s+", texto) if p.strip()]
    if not partes:
        return None, None
    if hallado := _CIUDADES.get(nz.clave(partes[0])):
        return hallado
    hallado = nz.municipio_espana(partes[0])
    if hallado:
        return hallado
    provincia = nz.provincia(partes[-1]) if len(partes) > 1 else nz.provincia(partes[0])
    return (nz.poblacion(partes[0]), provincia) if provincia else (None, None)


def _enlaces(sopa: BeautifulSoup) -> dict[str, str]:
    """clave de la ciudad (sin tildes, con guiones) → página de la carrera en esa ciudad."""
    enlaces = {}
    for a in sopa.find_all("a", href=re.compile(r"carreracancerpancreas\.es/.*(carrera|cursa)-")):
        href = a["href"].strip()
        if re.search(r"virtual|_no/?$|%20", href):
            continue
        ultimo = href.rstrip("/").rsplit("/", 1)[-1]
        enlaces.setdefault(re.sub(r"^(carrera|cursa)-(de-)?", "", ultimo), href)
    return enlaces


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    anio = None
    for t in sopa.find_all(class_="elementor-heading-title"):
        if re.fullmatch(r"\s*20\d\d\s*", t.get_text()):
            anio = int(t.get_text().strip())
            break
    if not anio:
        return [], ["sin año de la edición en la portada"]
    enlaces = _enlaces(sopa)
    carreras, descartes = [], []
    for h in sopa.find_all("h3"):
        texto = " ".join(h.get_text(" ", strip=True).split())
        m = re.fullmatch(r"(\d{1,2}) (\w+) / (.+)", texto)
        if not m or nz.clave(m.group(2)) not in _MESES:
            continue
        try:
            fecha = date(anio, _MESES[nz.clave(m.group(2))], int(m.group(1)))
        except ValueError:
            descartes.append(f"fecha imposible: {texto}")
            continue
        poblacion, provincia = _ciudad(m.group(3))
        if not provincia:
            descartes.append(f"sin provincia: {texto}")
            continue
        clave_ciudad = nz.clave(poblacion).replace(" ", "-")
        url = next((u for k, u in enlaces.items()
                    if k == clave_ciudad or k.split("-")[0] == clave_ciudad.split("-")[0]), URL)
        c = Carrera(nombre=f"Carrera de las Ciudades contra el Cáncer de Páncreas - {poblacion}", fecha=fecha,
                    fuente=Fuente(ID, url), poblacion=poblacion, provincia=provincia, modalidad="asfalto",
                    url_inscripcion=url)
        c.previos.append("Carrera solidaria: lo recaudado va a becas de investigación del cáncer de páncreas")
        c.marcar("Hora, distancias y cierre de inscripción en la página de la ciudad", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
