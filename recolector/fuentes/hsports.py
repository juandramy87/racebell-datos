"""9hSports (9hsports.cat): inscripciones y cronometraje de trails y carreras de montaña de toda Cataluña
(Osona, Maresme, Terres de l'Ebre, Pirineo de Lleida…). La página de inscripciones lista las próximas
carreras con «POBLACIÓN (código postal), Provincia», fecha y si la inscripción está abierta («Inscriu-te»).
No se abre «Veure inscrits» (lista de inscritos): solo se lee el listado."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, Carrera, Fuente

ID = "9hsports"
URL = "https://www.9hsports.cat/ca/inscripcions"
_LUGAR = re.compile(r"^(.*?)\s*\((\d{5})\)\s*,\s*(.*)$")
_PRUEBA = re.compile(r"\b(prova|proves|packs?)\b")  # carreras de prueba de la plataforma y venta de packs


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for tarjeta in sopa.select("div.marathon-card"):
        enlace = tarjeta.select_one("a[href*='informacio_cursa']")
        titulo = tarjeta.select_one(".marathon-title")
        if not (enlace and titulo):
            continue
        url = urljoin(URL, enlace["href"])
        if url in vistas:  # «Curses destacades» repite carreras de «Properes curses»
            continue
        vistas.add(url)
        nombre = nz.nombre(cat.texto(titulo.get_text(" ", strip=True)))
        detalles = [cat.texto(s.get_text(" ", strip=True)) for s in tarjeta.select(".detail-item span")]
        fecha = next((f for f in map(cat.fecha, detalles) if f), None)
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        if _PRUEBA.search(nz.clave(nombre)):
            descartes.append(f"prueba de la plataforma o venta: {nombre}")
            continue
        if cat.es_infantil(nombre):
            descartes.append(f"infantil: {nombre}")
            continue
        circuito = " ".join(d for d in detalles if not cat.fecha(d))
        a_pie, modalidad = cat.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        lugar = tarjeta.select_one(".location-info span")
        m = _LUGAR.match(cat.texto(lugar.get_text(" ", strip=True)) if lugar else "")
        if not m:
            descartes.append(f"fuera de España o sin lugar: {nombre}")
            continue
        pueblo, cp, prov = m.groups()
        provincia = nz.provincia(prov) or nz.provincia_por_cp(cp)
        if not provincia:
            descartes.append(f"fuera de España o sin provincia: {nombre} ({prov})")
            continue
        oficial = cat.municipio(pueblo)
        poblacion = oficial[0] if oficial and oficial[1] == provincia else nz.poblacion(_articulo_delante(pueblo))
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, url),
            poblacion=poblacion,
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=cat.distancias(nombre),
            url_inscripcion=url,
        )
        if circuito:
            c.previos.append(f"Puntúa en: {circuito}")
        if "inscriu" in nz.clave(enlace.get_text(" ", strip=True)):
            c.estado_fuente = ABIERTA
        cartel = tarjeta.select_one("img.poster-img")
        if cartel and cartel.get("src"):
            c.cartel = urljoin(URL, cartel["src"])
        c.marcar("Cierre de inscripción en la ficha de 9hSports", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes


def _articulo_delante(pueblo: str) -> str:
    """«PINELL DE BRAI, EL» → «EL PINELL DE BRAI»; quita «(MUNICIPIO)»."""
    t = re.sub(r"\s*\(municipio\)", "", pueblo, flags=re.I).strip()
    m = re.match(r"^(.*), ?(EL|LA|ELS|LES|L'|LO)$", t, re.I)
    return f"{m.group(2)} {m.group(1)}" if m else t
