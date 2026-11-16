"""Global-Tempo (Granada, Almería y alrededores). HTML en latin1.
La portada da nombre y fecha; provincia y localidad están en la ficha `carreras.php?id=N`.
OJO: la ficha publica la lista de inscritos con nombres. Solo se leen las líneas
«Fecha», «Provincia» y «Localidad»; nada más de la página se guarda."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "globaltempo"
URL = "https://www.global-tempo.com/"

_FECHA = re.compile(r"(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})")


def _texto(contenido: bytes | str) -> str:
    return contenido.decode("latin-1") if isinstance(contenido, bytes) else contenido


def leer_portada(contenido: bytes | str) -> list[tuple[str, str, datetime, Optional[str]]]:
    """Devuelve (id, nombre, fecha y hora, cartel) de cada prueba de la portada."""
    sopa = BeautifulSoup(_texto(contenido), "html.parser")
    vistos, pruebas = set(), []
    for a in sopa.find_all("a", href=re.compile(r"carreras\.php\?id=\d+")):
        caja = a.find("div", class_="cuadro_inscripcion")
        if not caja or not caja.find("h1") or not caja.find("h2"):
            continue
        ident = re.search(r"id=(\d+)", a["href"]).group(1)
        if ident in vistos:
            continue
        vistos.add(ident)
        m = _FECHA.search(caja.find("h2").get_text())
        if not m:
            continue
        d, mes, a_, h, mi = map(int, m.groups())
        img = caja.find("img")
        cartel = urljoin(URL, img["src"]) if img and img.get("src") else None
        pruebas.append((ident, nz.nombre(caja.find("h1").get_text(" ", strip=True)), datetime(a_, mes, d, h, mi), cartel))
    return pruebas


_INSCRITOS = re.compile(rb"Inscritos en la Carrera", re.I)


def recortar_ficha(contenido: bytes) -> bytes:
    """Corta la ficha donde empieza la lista de inscritos (nombres, apellidos y categoría):
    esos datos personales no se guardan nunca, ni en la caché."""
    m = _INSCRITOS.search(contenido)
    return contenido[: m.start()] if m else contenido


def leer_ficha(contenido: bytes | str) -> dict[str, str]:
    """Solo el título y las líneas «Fecha», «Provincia» y «Localidad». Ignora todo lo demás
    (la ficha publica también la lista de inscritos con nombres)."""
    if isinstance(contenido, bytes):
        contenido = recortar_ficha(contenido)
    texto = BeautifulSoup(_texto(contenido), "html.parser").get_text("\n", strip=True)
    datos = {}
    for campo in ("Fecha", "Provincia", "Localidad"):
        m = re.search(rf"^{campo}\s*:\s*(.+)$", texto, re.M)
        if m:
            datos[campo.lower()] = m.group(1).strip()
    lineas = texto.split("\n")
    for i, linea in enumerate(lineas):
        if linea.startswith("Fecha") and i and lineas[i - 1] not in ("Contraseña", "Acceso"):
            datos["nombre"] = lineas[i - 1]
            break
    return datos


# La portada no enseña todas las pruebas: algunas (sobre todo de Córdoba) solo tienen ficha.
# Sus id son correlativos, así que se sondean los huecos cercanos al id más alto de la portada.
MARGEN_IDS_OCULTOS = 40


def _ficha_a_prueba(ident: str, ficha: dict) -> Optional[tuple[str, str, datetime, Optional[str]]]:
    m = _FECHA.search(ficha.get("fecha", ""))
    if not m or not ficha.get("nombre"):
        return None  # id vacío: «01-01-1970» sin hora ni título
    d, mes, a_, h, mi = map(int, m.groups())
    return ident, nz.nombre(ficha["nombre"]), datetime(a_, mes, d, h, mi), None


def leer(contenido: bytes | str, *, descargar_ficha: Callable[[str], bytes], desde: date, hasta: date,
         buscar_ocultas: bool = True) -> tuple[list[Carrera], list[str]]:
    """Lee la portada, sondea las fichas ocultas y, solo para las pruebas entre `desde` y `hasta`,
    abre su ficha."""
    carreras: list[Carrera] = []
    descartes: list[str] = []
    pruebas = leer_portada(contenido)
    fichas: dict[str, dict] = {}
    if buscar_ocultas and pruebas:
        conocidos = {p[0] for p in pruebas}
        mayor = max(int(p[0]) for p in pruebas)
        vacios_seguidos = 0
        for n in range(mayor - MARGEN_IDS_OCULTOS, mayor + MARGEN_IDS_OCULTOS):
            if str(n) in conocidos:
                continue
            ficha = leer_ficha(descargar_ficha(urljoin(URL, f"carreras.php?id={n}")))
            prueba = _ficha_a_prueba(str(n), ficha)
            if prueba is None:
                vacios_seguidos += 1
                if n > mayor and vacios_seguidos >= 3:
                    break
                continue
            vacios_seguidos = 0
            fichas[str(n)] = ficha
            pruebas.append(prueba)
    for ident, nombre, cuando, cartel in pruebas:
        if cuando.month == 1 and cuando.day == 1:
            descartes.append(f"fecha por defecto 01-01 (circuito o sin fecha real): {nombre}")
            continue
        if not desde <= cuando.date() <= hasta:
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        url = urljoin(URL, f"carreras.php?id={ident}")
        ficha = fichas.get(ident) or leer_ficha(descargar_ficha(url))
        provincia = nz.provincia(ficha.get("provincia"))
        if not provincia:
            descartes.append(f"fuera de España o sin provincia: {nombre} ({ficha.get('provincia')})")
            continue
        c = Carrera(
            nombre=nombre,
            fecha=cuando.date(),
            hora=cuando.strftime("%H:%M") if cuando.strftime("%H:%M") != "00:00" else None,
            fuente=Fuente(ID, url),
            poblacion=nz.poblacion(ficha.get("localidad")),
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=nz.distancias_del_nombre(nombre),
            url_inscripcion=url,
            cartel=cartel,
        )
        c.marcar("Cierre de inscripción en la normativa (PDF) de la ficha", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
