"""Corredores Populares: listado de las carreras con inscripción propia (Sevilla y Córdoba).
OJO: solo `inscripciones.php`. Su `/calendario/` mezcla carreras de otros (es un agregador).
No se abre nunca la página de inscritos."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "corredorespopulares"
URL = "https://www.corredorespopulares.es/inscripciones.php"

_MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
_LUGAR = re.compile(r"📍\s*(.+?),\s*([^\n📅]+)")
_FECHA = re.compile(r"📅\s*(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})", re.I)
_CIERRE = re.compile(r"Cierre inscripciones:\s*(\d{2}/\d{2}/\d{4})", re.I)


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for caja in sopa.select("div.box"):
        h2 = caja.find("h2")
        if not h2:
            continue
        # «XXIX CARRERA POPULAR SANTIPONCE<br>XXIV CARRERA ESCOLAR…»: la primera línea es la principal.
        nombre = nz.nombre(h2.get_text("\n", strip=True).split("\n")[0])
        texto = caja.get_text("\n", strip=True)
        texto_plano = re.sub(r"\s+", " ", texto)
        mf = _FECHA.search(texto_plano)
        if not mf or nz.clave(mf.group(2)) not in _MESES:
            descartes.append(f"sin fecha: {nombre}")
            continue
        fecha = date(int(mf.group(3)), _MESES[nz.clave(mf.group(2))], int(mf.group(1)))
        ml = _LUGAR.search(texto_plano)
        poblacion, provincia = (ml.group(1), nz.provincia(ml.group(2))) if ml else (None, None)
        if not provincia:
            descartes.append(f"fuera de Andalucía: {nombre} ({ml.group(2).strip() if ml else '¿?'})")
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        enlace = caja.find("a", href=re.compile(r"inscripcion/.+/index\.php"))
        url = urljoin(URL, enlace["href"]) if enlace else URL
        img = caja.find("img")
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, url),
            poblacion=nz.poblacion(poblacion),
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=nz.distancias_del_nombre(nombre),
            url_inscripcion=url,
            cartel=urljoin(URL, img["src"].split("?")[0]) if img and img.get("src") else None,
        )
        if mc := _CIERRE.search(texto_plano):
            # Solo da el día: se toma hasta el final de ese día.
            c.inscripcion_hasta = datetime.strptime(mc.group(1), "%d/%m/%Y").replace(hour=23, minute=59)
        else:
            c.marcar("Cierre de inscripción en el reglamento (PDF)", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
