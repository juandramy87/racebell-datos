"""Orycronsport: cronometraje e inscripciones de Salamanca (también Ávila y Zamora).
Listado `competiciones?proximas=1` (nombre, fecha, estado) y ficha `/competiciones/<id>` con día, hora,
lugar, recorrido y plazo de cada modalidad («Inscripción 15/10/2026 a las 0:00 - 19/11/2026 a las 23:59»).
La ficha enlaza listados de inscritos: no se siguen y de la ficha solo se guarda el bloque de datos.
robots.txt: solo prohíbe /diplomas/."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, Carrera, Fuente

ID = "orycronsport"
BASE = "https://www.orycronsport.com"
URL = BASE + "/competiciones?proximas=1"
# Si la ficha no nombra otra provincia, se toma la de la empresa (todas las de 2026 son de Salamanca o lo dicen).
PROVINCIA_POR_DEFECTO = "Salamanca"

_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def _fecha_larga(texto: str) -> Optional[date]:
    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", nz.sin_tildes(texto).lower())
    if not m or m.group(2) not in _MESES:
        return None
    return date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))


def enlaces(contenido: bytes | str) -> list[tuple[str, str, Optional[date], str]]:
    """(url, nombre, fecha, estado) de cada competición próxima."""
    sopa = BeautifulSoup(contenido, "html.parser")
    vistos, salida = set(), []
    for a in sopa.select("div.divCuadriculaCompeticiones a.btnCompeticion"):
        url = BASE + a["href"] if a["href"].startswith("/") else a["href"]
        if url in vistos:
            continue
        vistos.add(url)
        nombre = a.find("strong").get_text(" ", strip=True) if a.find("strong") else ""
        fecha = a.select_one(".spanFecha")
        estado = a.select_one(".spanEstado")
        salida.append((url, nombre, _fecha_larga(fecha.get_text()) if fecha else None,
                       estado.get_text(" ", strip=True) if estado else ""))
    return salida


def recortar_ficha(contenido: bytes) -> bytes:
    """Solo el texto de la ficha, desde el título hasta antes del bloque de contacto."""
    sopa = BeautifulSoup(contenido, "html.parser")
    for s in sopa(["script", "style", "noscript"]):
        s.decompose()
    texto = re.sub(r"\n\s*\n+", "\n", sopa.get_text("\n"))
    inicio, fin = texto.find("Día:"), texto.find("CONTACTO")
    if inicio < 0:
        return b""
    trozo = texto[inicio:fin if fin > inicio else inicio + 3000]
    trozo = "\n".join(l for l in trozo.splitlines() if "listado de inscri" not in l.lower())
    return trozo.encode("utf-8")


def _campo(texto: str, etiqueta: str) -> str:
    m = re.search(re.escape(etiqueta) + r"\s*\n\s*(.+)", texto)
    return m.group(1).strip() if m else ""


def _provincia(*textos: str) -> str:
    for t in textos:
        if nz.provincia(t):
            return nz.provincia(t)
        for trozo in re.split(r"[\s,()\-]+de\s+|[,()\-]", t or ""):
            if nz.provincia(trozo.strip()):
                return nz.provincia(trozo.strip())
    return PROVINCIA_POR_DEFECTO


def _distancias(texto: str) -> list[float]:
    """Distancias del bloque «Recorrido» («300m - 650m - 3,2km - 6,2km» → [3.2, 6.2]; sin marcha ni infantiles)."""
    m = re.search(r"Recorrido:\s*\n(.*?)(?:\n\*|\nWeb del organizador|\Z)", texto, re.S)
    kms = set()
    for linea in (m.group(1).splitlines() if m else []):
        if re.search(r"marcha|infantil|menores|andarin", nz.clave(linea)):
            continue
        for numero, unidad in re.findall(r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,3})?)\s*(km|m)\b", linea, re.I):
            valor = float(numero.replace(".", "").replace(",", "."))
            km = valor if unidad.lower() == "km" else valor / 1000
            if km >= 1:
                kms.add(round(km, 3))
    return sorted(kms)


def leer_ficha(contenido: bytes | str, url: str, nombre: str, estado: str = "") -> tuple[Optional[Carrera], Optional[str]]:
    texto = contenido.decode("utf-8", errors="replace") if isinstance(contenido, bytes) else contenido
    fecha = _fecha_larga(_campo(texto, "Día:"))
    if not fecha:
        return None, f"ficha sin fecha: {nombre}"
    lugar = re.sub(r"\s*\([^()]*\)", "", _campo(texto, "Lugar:")).strip()  # «Salamanca (El Corte Inglés)»
    m_ciudad = re.search(r"\bciudad de ([^,]+)$", lugar, re.I)  # «Parque del Soto de la ciudad de Ávila»
    lugar = m_ciudad.group(1).strip() if m_ciudad else lugar
    recorrido = _campo(texto, "Recorrido:")
    a_pie, modalidad = nz.clasificar(nombre)
    if not a_pie:
        return None, f"no es a pie: {nombre}"
    c = Carrera(
        nombre=nz.nombre(nombre),
        fecha=fecha,
        fuente=Fuente(ID, url),
        poblacion=nz.poblacion(lugar) or None,
        provincia=_provincia(lugar, nombre),
        modalidad=modalidad,
        distancias_km=sorted(set(nz.distancias_del_nombre(nombre)) | set(_distancias(texto))),
        url_inscripcion=url,
        estado_fuente=ABIERTA if "abierta" in nz.clave(estado) else None,
    )
    horas = re.findall(r"\b(\d{1,2})[:.](\d{2})\s*h", _campo(texto, "Hora:"))
    if horas:
        # Si hay varias salidas, la de la absoluta suele ser la última; si no lo dice, la primera.
        linea = _campo(texto, "Hora:")
        absoluta = re.search(r"(\d{1,2})[:.](\d{2})\s*h\s*\((?:[^)]*absolut)", linea, re.I)
        h, mi = absoluta.groups() if absoluta else horas[0]
        c.hora = f"{int(h):02d}:{mi}"
    # Plazos de cada modalidad: la carrera cierra con el plazo más tardío.
    plazos = re.findall(r"(\d{2})/(\d{2})/(\d{4}) a las (\d{1,2}):(\d{2})\s*-\s*(\d{2})/(\d{2})/(\d{4}) a las (\d{1,2}):(\d{2})",
                        texto)
    if plazos:
        inicios = [datetime(int(p[2]), int(p[1]), int(p[0]), int(p[3]), int(p[4])) for p in plazos]
        finales = [datetime(int(p[7]), int(p[6]), int(p[5]), int(p[8]), int(p[9])) for p in plazos]
        c.inscripcion_desde, c.inscripcion_hasta = min(inicios), max(finales)
    else:
        c.marcar("Cierre de inscripción en la ficha de Orycronsport", "pendiente_cartel")
    return c, None


def leer(contenido: bytes | str, descargar_ficha: Callable[[str], bytes]) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for url, nombre, _fecha, estado in enlaces(contenido):
        if not nz.clasificar(nombre)[0]:
            descartes.append(f"no es a pie: {nombre}")
            continue
        c, motivo = leer_ficha(descargar_ficha(url), url, nombre, estado)
        if c:
            carreras.append(c)
        else:
            descartes.append(motivo)
    return carreras, descartes
