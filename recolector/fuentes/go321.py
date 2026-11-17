"""321Go (Asturias, y algo de Pontevedra): plataforma de inscripción. La página «todas las modalidades»
(`/Carrera/Modalidad/TODOS`) lista las próximas con nombre, modalidad (Atletismo, Trail, Andaina…),
dirección (con provincia y a veces código postal), fecha y si la inscripción está abierta. La ficha
(`/Carrera/Detail/<id>`) da la hora de cada prueba y el «Cierre de inscripciones: … (dd mes, aaaa - hh:mm».
Sin robots.txt. De la ficha solo se lee la hora y el cierre (ni inscritos ni cupos)."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, PENDIENTE_CARTEL, Carrera, Fuente

ID = "321go"
BASE = "https://www.321go.es"
URL = BASE + "/Carrera/Modalidad/TODOS?lang=es"

_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_FECHA = re.compile(r"(\d{1,2})\s+([a-záéíóú]+),?\s+(\d{4})(?:\s*-\s*(\d{1,2}:\d{2}))?", re.I)
# Modalidades de la tarjeta que no son carreras a pie.
_NO_A_PIE = {"andaina", "ciclismo", "natacion", "otro"}
_CP = re.compile(r"\b(\d{5})\b")


def _fecha(texto: str) -> Optional[tuple[date, Optional[str]]]:
    m = _FECHA.search(texto)
    if not m or nz.clave(m.group(2)) not in _MESES:
        return None
    return date(int(m.group(3)), _MESES[nz.clave(m.group(2))], int(m.group(1))), m.group(4)


def _lugar(texto: str) -> tuple[Optional[str], Optional[str]]:
    """«Noreña, Asturias, 33180, España» → («Noreña», «Asturias»). «Plaza…, Sabugo, Avilés, Asturias, 33402,
    España» → («Avilés», «Asturias»): el pueblo es lo que va justo antes de la provincia (o de la comunidad)."""
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    partes = [re.sub(r"\s*\d{5}\s*", " ", p).strip() for p in partes if nz.clave(p) not in ("espana", "")]
    partes = [p for p in partes if p and not p.isdigit()]
    provincia = None
    for i, p in enumerate(partes):
        nombre = re.sub(r"^principado de ", "", nz.clave(p))
        if prov := nz.provincia(nombre):
            provincia = prov
            # Antes de la provincia puede ir la comarca («Morrazo») o la comunidad («Galicia») detrás.
            antes = [x for x in partes[:i] if nz.clave(x) not in ("galicia", "morrazo")]
            # «Pontevedra, Galicia, España»: sin nada delante, el pueblo es la capital.
            return nz.poblacion(antes[-1] if antes else p), provincia
    if m := _CP.search(texto):
        provincia = nz.provincia_por_cp(m.group(1))
    return (nz.poblacion(partes[0]) if partes else None), provincia


def leer(contenido: bytes | str, *, descargar_ficha: Optional[Callable[[str], bytes]] = None
         ) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for tarjeta in sopa.select("div.card.box-shadow"):
        titulo = tarjeta.select_one("h5.card-title a[href]")
        if not titulo:
            continue
        url = BASE + titulo["href"].split("?")[0]
        if url in vistas:
            continue
        vistas.add(url)
        nombre = nz.nombre(titulo.get_text(" ", strip=True))
        modalidades = [m.get_text(" ", strip=True) for m in tarjeta.select(".race-card-modalities .badge")]
        if modalidades and all(nz.clave(m) in _NO_A_PIE for m in modalidades):
            descartes.append(f"no es a pie: {nombre} ({', '.join(modalidades)})")
            continue
        if re.search(r"\bescolar", nz.clave(nombre)):
            descartes.append(f"competición escolar: {nombre}")
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        if not modalidad:
            claves = " ".join(nz.clave(m) for m in modalidades)
            modalidad = ("trail" if "trail" in claves else "obstáculos" if "obstaculos" in claves
                         else "asfalto" if "atletismo" in claves else None)
        fecha = None
        for li in tarjeta.select("li.list-group-item"):
            if "fecha" in nz.clave(li.get_text()):
                fecha = _fecha(li.get_text(" ", strip=True))
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        texto_lugar = tarjeta.select_one("p.card-text")
        poblacion, provincia = _lugar(texto_lugar.get_text(" ", strip=True)) if texto_lugar else (None, None)
        if not provincia:
            descartes.append(f"sin provincia: {nombre} ({texto_lugar.get_text(' ', strip=True) if texto_lugar else ''})")
            continue
        estado = tarjeta.select_one(".card-footer small")
        estado_txt = nz.clave(estado.get_text()) if estado else ""
        c = Carrera(
            nombre=nombre,
            fecha=fecha[0],
            fuente=Fuente(ID, url),
            poblacion=poblacion,
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=nz.distancias_del_nombre(nombre),
            estado_fuente=ABIERTA if "abiertas" in estado_txt else CERRADA if "cerradas" in estado_txt else None,
            url_inscripcion=url,
        )
        img = tarjeta.select_one("img.card-img-top-same-height")
        if img and img.get("src"):
            c.cartel = BASE + img["src"] if img["src"].startswith("/") else img["src"]
        if descargar_ficha:
            leer_ficha(descargar_ficha(url), c)
        if not c.inscripcion_hasta and c.estado_fuente != CERRADA:
            c.marcar("Cierre de inscripción no indicado en 321Go", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes


def leer_ficha(contenido: bytes | str, c: Carrera) -> None:
    """Hora de la primera salida del día de la carrera y la fecha de cierre más tardía."""
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    texto = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    horas = []
    for m in re.finditer(r"Fecha de inicio:\s*(\d{1,2}\s+[a-záéíóú]+,?\s+\d{4}\s*-\s*\d{1,2}:\d{2})", texto, re.I):
        if (f := _fecha(m.group(1))) and f[0] == c.fecha and f[1]:
            horas.append(f[1].zfill(5))
    if horas:
        c.hora = min(horas)
    cierres = []
    for m in re.finditer(r"Cierre de inscripciones:[^()]*\((\d{1,2}\s+[a-záéíóú]+,?\s+\d{4}\s*-\s*\d{1,2}:\d{2})", texto, re.I):
        if (f := _fecha(m.group(1))) and f[1]:
            h, mi = map(int, f[1].split(":"))
            cierres.append(datetime(f[0].year, f[0].month, f[0].day, h, mi))
    if cierres:
        c.inscripcion_hasta = max(cierres)


def recortar_ficha(datos: bytes) -> bytes:
    """Deja de la ficha solo las líneas de «Fecha de inicio» y «Cierre de inscripciones» (para la caché):
    nada de cupos ni del buscador de inscritos."""
    texto = BeautifulSoup(datos.decode("utf-8", "replace"), "html.parser").get_text(" ", strip=True)
    trozos = re.findall(r"Fecha de inicio:\s*\d{1,2}\s+[a-záéíóú]+,?\s+\d{4}\s*-\s*\d{1,2}:\d{2}", texto, re.I)
    trozos += re.findall(r"Cierre de inscripciones:[^()]*\([^)]*\)", texto, re.I)
    return ("<html><body>\n" + "\n".join(f"<p>{t}</p>" for t in trozos) + "\n</body></html>\n").encode()
