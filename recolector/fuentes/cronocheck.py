"""CronoCheck (cronocheck.com): plataforma de inscripciones de toda España, con muchos organizadores catalanes
(Bages, Baix Llobregat, Terres de l'Ebre) y alguno gallego, vasco, andaluz y canario. El calendario público
(`/es/calendar`) lista los próximos eventos con fecha («13 de Diciembre de 2026»), nombre, un resumen y el enlace
de inscripción. El lugar no va en el listado: se saca del nombre («… Sant Boi», «Sant Silvestre Manresana») y,
si no, del JSON-LD de la ficha (`location.address`, a veces «No disponible»). robots.txt no prohíbe nada.
De la ficha solo se lee el JSON-LD (no hay datos de inscritos en ella)."""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Callable, Optional

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "cronocheck"
URL = "https://cronocheck.com/es/calendar"
_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_FECHA = re.compile(r"(\d{1,2}) de (\w+) de (\d{4})")
# Gentilicios y formas cortas en los nombres de las carreras.
_ALIAS = {"manresana": "Manresa", "manresa": "Manresa"}
_SOLO_SOCIOS = re.compile(r"\b(nomes per a socis|solo para socios|exclusiva para socios)\b")
_NO_A_PIE = re.compile(r"\b(canicross|muixing|mushing|triatlon|aguas abiertas|concentracion invernal|etapa camino)\b")


def _fecha(texto: str) -> Optional[date]:
    m = _FECHA.search(nz.clave(texto))
    if m and _MESES.get(m.group(2)):
        return date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
    return None


def eventos(contenido: bytes | str) -> list[dict]:
    """[{nombre, fecha, url, resumen}] del calendario."""
    sopa = BeautifulSoup(contenido, "html.parser")
    lista: list[dict] = []
    vistas: set[str] = set()
    for fila in sopa.select(".cal-ck-row"):
        titulo, cuando = fila.select_one("h1"), fila.select_one("p.fw-bold")
        enlace = fila.select_one("a.btn[href^='https://cronocheck.com/']")
        if not (titulo and cuando and enlace) or enlace["href"] in vistas:
            continue
        vistas.add(enlace["href"])
        resumen = fila.select_one("p.lead")
        lista.append({"nombre": nz.nombre(cat.texto(titulo.get_text(" ", strip=True))),
                      "fecha": _fecha(cuando.get_text(" ", strip=True)), "url": enlace["href"],
                      "resumen": cat.texto(resumen.get_text(" ", strip=True)) if resumen else ""})
    return lista


def lugar_de_ficha(contenido: bytes | str) -> Optional[tuple[str, str]]:
    """(municipio, provincia) del JSON-LD de la ficha, o None si dice «No disponible» o no se reconoce."""
    texto = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', texto, re.S):
        try:
            datos = json.loads(bloque)
        except ValueError:
            continue
        lugar = datos.get("location") or {}
        for t in (lugar.get("address"), lugar.get("name")):
            if isinstance(t, dict):
                t = " ".join(str(v) for v in t.values())
            if t and "no disponible" not in nz.clave(t):
                hallado = cat.municipio(t) or nz.municipio_espana(t)
                if hallado:
                    return hallado
    return None


def _municipio(nombre: str) -> Optional[tuple[str, str]]:
    k = nz.clave(nombre)
    for corto, oficial in _ALIAS.items():
        if re.search(rf"\b{corto}\b", k):
            return cat.municipio(oficial)
    return cat.municipio_en(nombre)


def leer(contenido: bytes | str, *, descargar_ficha: Callable[[str], bytes],
         hoy: Optional[date] = None) -> tuple[list[Carrera], list[str]]:
    hoy = hoy or date.today()
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for e in eventos(contenido):
        nombre, fecha = e["nombre"], e["fecha"]
        if not fecha or fecha < hoy:
            continue
        clave = nz.clave(f"{nombre} {e['resumen']}")
        if _NO_A_PIE.search(nz.clave(nombre)):
            descartes.append(f"no es a pie: {nombre}")
            continue
        if _SOLO_SOCIOS.search(clave):
            descartes.append(f"solo para socios: {nombre}")
            continue
        a_pie, modalidad = cat.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        if cat.es_infantil(nombre):
            descartes.append(f"infantil: {nombre}")
            continue
        oficial = _municipio(nombre) or lugar_de_ficha(descargar_ficha(e["url"]))
        if not oficial:
            descartes.append(f"sin municipio: {nombre}")
            continue
        c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, e["url"]), poblacion=oficial[0],
                    provincia=oficial[1], modalidad=modalidad, distancias_km=cat.distancias(nombre),
                    url_inscripcion=e["url"])
        c.marcar("Cierre de inscripción en la ficha de CronoCheck", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
