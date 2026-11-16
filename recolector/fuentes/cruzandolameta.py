"""Cruzando la Meta (organiza y cronometra en Almería, Granada, Jaén…): «Próximas pruebas» con tarjetas por mes.
Inscribe en Inscrik (que ya leemos), pero publica las pruebas antes de abrir la inscripción. Cada tarjeta da
nombre, día (mes abreviado y día; el año sale del separador «Diciembre 2026»), disciplina, lugar («… (Granada)»)
y estado («Cierra el 19 nov 2026», «Inscripciones abiertas»). La provincia sale del paréntesis o del municipio."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fuentes.rockthesport import _indice_municipios
from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, NO_ABIERTA, Carrera, Fuente

ID = "cruzandolameta"
URL = "https://www.cruzandolameta.es/pruebas/"
_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10,
          "nov": 11, "dic": 12}
_CIERRA = re.compile(r"Cierra el (\d{1,2}) (\w{3})\w* (\d{4})", re.I)


def _lugar(texto: str, nombre: str, indice: dict) -> tuple[str | None, str | None]:
    """(municipio, provincia): el municipio andaluz más largo que aparezca en el lugar (sin la provincia del
    paréntesis final, que si no se tomaría por la capital) o en el nombre de la prueba."""
    sin_provincia = re.sub(r"\([^)]*\)\s*$", "", texto)
    clave = f" {nz.clave(sin_provincia)} {nz.clave(nombre)} "
    mejor = None
    for k, valor in indice.items():
        if f" {k} " in clave and (mejor is None or len(k) > len(mejor[0])):
            mejor = (k, valor)
    m = re.search(r"\(([^)]+)\)\s*$", texto)
    provincia = nz.provincia(m.group(1)) if m else None
    if mejor and provincia and mejor[1][1] != provincia:
        return None, provincia  # «Guájar Fondón (Granada)» no es Fondón de Almería
    if mejor:
        return mejor[1][0], mejor[1][1]
    return None, provincia


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    indice = _indice_municipios()
    carreras, descartes = [], []
    for separador in sopa.select(".separador-mes"):
        anyo = re.search(r"(\d{4})", separador.get_text())
        rejilla = separador.find_next_sibling(class_="rejilla")
        if not (anyo and rejilla):
            continue
        for t in rejilla.select("a.tarjeta"):
            nombre = nz.nombre(t.select_one("h3").get_text(" ", strip=True))
            mes, dia = t.select_one(".calendario .mes"), t.select_one(".calendario b")
            lugar = t.select_one(".meta.lugar")
            if not (mes and dia and lugar and nz.clave(mes.get_text())[:3] in _MESES):
                continue
            poblacion, provincia = _lugar(lugar.get_text(" ", strip=True), nombre, indice)
            if not provincia:
                descartes.append(f"sin provincia andaluza: {nombre}")
                continue
            disciplina = (t.select_one(".disc") or lugar).get_text(" ", strip=True)
            a_pie, modalidad = nz.clasificar(nombre, disciplina)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre}")
                continue
            url = urljoin(URL, t["href"])
            c = Carrera(nombre=nombre, fecha=date(int(anyo.group(1)), _MESES[nz.clave(mes.get_text())[:3]],
                                                  int(dia.get_text())),
                        hora=None, fuente=Fuente(ID, url), poblacion=poblacion, provincia=provincia,
                        modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=url)
            estado = (t.select_one(".estado") or lugar).get_text(" ", strip=True)
            if m := _CIERRA.search(estado):
                if nz.clave(m.group(2)) in _MESES:
                    # Solo da el día: hasta el final de ese día, como en Corredores Populares.
                    c.inscripcion_hasta = datetime(int(m.group(3)), _MESES[nz.clave(m.group(2))], int(m.group(1)), 23, 59)
                c.estado_fuente = ABIERTA
            elif re.search(r"abiertas", estado, re.I):
                c.estado_fuente = ABIERTA
            elif re.search(r"cerrad|agotad", estado, re.I):
                c.estado_fuente = CERRADA
            elif re.search(r"próxima|pronto|abre", estado, re.I):
                c.estado_fuente = NO_ABIERTA
            img = t.select_one("img[src]")
            c.cartel = urljoin(URL, img["src"]) if img else None
            carreras.append(c)
    return carreras, descartes
