"""Timingsys: cronometraje e inscripciones de Castilla-La Mancha (Cuenca, Albacete, Ciudad Real).
La portada lista los próximos eventos (nombre, tipo «A PIE»/«TRAIL»/«CICLISMO…», fecha). La ficha
`/event/<id>` trae «Cuándo», «Población», «Provincia» y «Fechas de inscripción: Del … al …».
La ficha enlaza el listado de participantes: no se sigue y de la ficha solo se guarda el bloque
«Datos básicos». robots.txt: permite todo."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "timingsys"
URL = "https://timingsys.com/home"
_TIPOS_A_PIE = re.compile(r"a pie|trail|montana|cross|atletismo|running")
_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10,
          "nov": 11, "dic": 12}
_MESES_LARGOS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                 "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def eventos(contenido: bytes | str) -> list[dict]:
    """[{url, nombre, tipo, fecha}] de las tarjetas de la portada."""
    sopa = BeautifulSoup(contenido, "html.parser")
    salida, vistos = [], set()
    for tarjeta in sopa.select("div.card"):
        titulo = tarjeta.select_one("h5.card-title a")
        if not titulo or titulo["href"] in vistos:
            continue
        vistos.add(titulo["href"])
        tipo = tarjeta.select_one("p.card-text")
        fecha = None
        for li in tarjeta.select(".date .event_details"):
            m = re.search(r"(\d{1,2}) (\w+) (\d{4})", nz.clave(li.get_text()))
            if m and m.group(2)[:3] in _MESES:
                fecha = date(int(m.group(3)), _MESES[m.group(2)[:3]], int(m.group(1)))
        salida.append({"url": titulo["href"], "nombre": titulo.get_text(" ", strip=True),
                       "tipo": tipo.get_text(" ", strip=True) if tipo else "", "fecha": fecha})
    return salida


def recortar_ficha(contenido: bytes) -> bytes:
    """Solo el texto del bloque «Datos básicos» (cuándo, lugar, provincia, fechas de inscripción)."""
    sopa = BeautifulSoup(contenido, "html.parser")
    for s in sopa(["script", "style"]):
        s.decompose()
    texto = re.sub(r"\n\s*\n+", "\n", sopa.get_text("\n"))
    inicio = texto.find("Datos básicos")
    if inicio >= 0:
        fin = texto.find("Tarifas", inicio)
        return texto[inicio:fin if fin > inicio else inicio + 1500].encode("utf-8")
    # Ficha de Cronomancha (marca de Timingsys en Ciudad Real): «Fecha del Evento» … «INSCRITOS» y «Fecha de inicio».
    inicio = texto.find("Fecha del Evento")
    if inicio >= 0:
        fin = texto.find("INSCRITOS", inicio)
        trozo = texto[inicio:fin if fin > inicio else inicio + 1200]
        m = re.search(r"Fecha de inicio\s*\n\s*.+", texto)
        # La dirección completa («Plaza …, Manzanares, Ciudad Real») solo está en un comentario HTML.
        lugar = re.search(rb'class="place">([^<>]*?)-->', contenido)
        extra = ("\n" + m.group(0) if m else "") + ("\n" + lugar.group(1).decode("utf-8", "replace") + "-->" if lugar else "")
        return (trozo + extra).encode("utf-8")
    # Ficha nueva (desde finales de 2026): «hasta el …», «Fecha», «Lugar» antes de «Elige tu inscripción».
    fin = texto.find("Elige tu inscripción")
    if fin < 0:
        return b""
    trozo = texto[max(0, fin - 800):fin]
    trozo = trozo[trozo.find("Inscr"):] if "Inscr" in trozo else trozo
    return trozo.encode("utf-8")


def _campo(texto: str, etiqueta: str) -> str:
    m = re.search(re.escape(etiqueta) + r"\s*:\s*\n?\s*(.+)", texto)
    return m.group(1).strip() if m else ""


def _provincia_en(*textos: Optional[str]) -> Optional[str]:
    """Provincia nombrada dentro de un texto («Carrera del Pavo Cuenca 2026» → Cuenca)."""
    for t in textos:
        k = f" {nz.clave(t)} "
        for nombre_clave, prov in nz.PROVINCIAS.items():
            if nombre_clave and f" {nombre_clave} " in k:
                return prov
    return None


def _fin_cronomancha(texto: str, fecha: date) -> Optional[datetime]:
    """«Fin de inscripción: 19 dic 2026 15:00». Se ignora si es de otra edición (más de 4 meses antes)."""
    m = re.search(r"Fin de inscripci.n:?\s*(\d{1,2}) (\w+) (\d{4}) (\d{1,2}):(\d{2})", texto)
    if not m or nz.clave(m.group(2))[:3] not in _MESES:
        return None
    fin = datetime(int(m.group(3)), _MESES[nz.clave(m.group(2))[:3]], int(m.group(1)), int(m.group(4)), int(m.group(5)))
    return fin if 0 <= (fecha - fin.date()).days <= 120 else None


def leer_ficha(contenido: bytes | str, ev: dict) -> tuple[Optional[Carrera], Optional[str]]:
    texto = contenido.decode("utf-8", errors="replace") if isinstance(contenido, bytes) else contenido
    nombre = nz.nombre(ev["nombre"])
    cuando = _campo(texto, "Cuándo")
    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})(?: a las (\d{1,2}):(\d{2}))?", nz.sin_tildes(cuando).lower())
    fecha = date(int(m.group(3)), _MESES_LARGOS[m.group(2)], int(m.group(1))) if m and m.group(2) in _MESES_LARGOS \
        else ev.get("fecha")
    if not fecha:
        return None, f"sin fecha: {nombre}"
    cronomancha = re.search(r"Fecha de inicio\s*\n\s*(\d{1,2}) (\w+) (\d{4})(?: (\d{1,2}):(\d{2}))?", texto)
    nueva = None if cronomancha else re.search(r"Fecha\s*\n\s*(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", texto)
    if cronomancha:  # «Fecha de inicio 20 dic 2026 11:00», «Lugar: MANZANARES», «Plaza …, Manzanares, Ciudad Real-->»
        g = cronomancha.groups()
        mes = _MESES.get(nz.clave(g[1])[:3])
        fecha = date(int(g[2]), mes, int(g[0])) if mes else ev.get("fecha")
        m = None
        hora = f"{int(g[3]):02d}:{g[4]}" if g[3] else None
        poblacion = _campo(texto, "Lugar")
        direccion = re.search(r"^(.+?)-->", texto, re.M)
        partes = [x.strip() for x in direccion.group(1).split(",") if x.strip()] if direccion else []
        provincia = nz.provincia(partes[-1]) if partes else None
        if not poblacion and partes:
            poblacion = partes[-2] if provincia and len(partes) > 1 else partes[-1]
    elif nueva:  # ficha nueva: «Fecha 19/12/2026 16:30», «Lugar Villanueva de la Jara (Cuenca)»
        g = nueva.groups()
        fecha = date(int(g[2]), int(g[1]), int(g[0]))
        m = None
        hora = f"{int(g[3]):02d}:{g[4]}" if g[3] else None
        lugar = re.search(r"Lugar\s*\n\s*(.+?)\s*\(([^()]+)\)\s*$", texto, re.M)
        poblacion, provincia = (lugar.group(1), nz.provincia(lugar.group(2))) if lugar else (None, None)
    else:
        hora = f"{int(m.group(4)):02d}:{m.group(5)}" if m and m.group(4) else None
        provincia = nz.provincia(_campo(texto, "Provincia"))
        poblacion = _campo(texto, "Población")
        # «La Pulgosa, Albacete»: si el último trozo es la provincia o un municipio, se queda ese.
        trozos = [t.strip() for t in poblacion.split(",") if t.strip()]
        poblacion = trozos[-1] if len(trozos) > 1 else (trozos[0] if trozos else None)
    provincia = provincia or _provincia_en(nombre, poblacion)
    a_pie, modalidad = nz.clasificar(nombre, ev.get("tipo"))
    if not a_pie:
        return None, f"no es a pie: {nombre}"
    c = Carrera(
        nombre=nombre,
        fecha=fecha,
        fuente=Fuente(ID, ev["url"]),
        hora=hora,
        poblacion=nz.poblacion(poblacion),
        provincia=provincia,
        modalidad=modalidad or ("trail" if "trail" in nz.clave(ev.get("tipo")) else None),
        distancias_km=nz.distancias_del_nombre(nombre),
        url_inscripcion=ev["url"],
    )
    p = re.search(r"Del (\d{2})/(\d{2})/(\d{4}) a las (\d{1,2}):(\d{2}) al (\d{2})/(\d{2})/(\d{4}) a las (\d{1,2}):(\d{2})",
                  texto)
    cierre = re.search(r"hasta el (\d{2})/(\d{2})/(\d{4}) (\d{1,2}):(\d{2})", texto)
    if not provincia:
        # Todas las de Timingsys/Cronomancha son de Castilla-La Mancha; el pueblo lo dirá al completar municipios.
        c.comunidad = "castilla-la-mancha"
        c.marcar("Provincia sin confirmar (Timingsys no la da): Castilla-La Mancha", "pendiente_cartel")
    if p:
        g = [int(x) for x in p.groups()]
        c.inscripcion_desde = datetime(g[2], g[1], g[0], g[3], g[4])
        c.inscripcion_hasta = datetime(g[7], g[6], g[5], g[8], g[9])
    elif cierre:
        g = [int(x) for x in cierre.groups()]
        c.inscripcion_hasta = datetime(g[2], g[1], g[0], g[3], g[4])
    elif _fin_cronomancha(texto, fecha):
        c.inscripcion_hasta = _fin_cronomancha(texto, fecha)
    elif False:
        g = [int(x) for x in cierre.groups()]
        c.inscripcion_hasta = datetime(g[2], g[1], g[0], g[3], g[4])
    else:
        c.marcar("Cierre de inscripción en la ficha de Timingsys", "pendiente_cartel")
    return c, None


def leer(contenido: bytes | str, descargar_ficha: Callable[[str], bytes]) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for ev in eventos(contenido):
        if (not _TIPOS_A_PIE.search(nz.clave(ev["tipo"])) or not nz.clasificar(ev["nombre"])[0]
                or re.search(r"entrenamiento|escuela", nz.clave(ev["nombre"]))):
            descartes.append(f"no es a pie: {ev['nombre']} ({ev['tipo']})")
            continue
        c, motivo = leer_ficha(descargar_ficha(ev["url"]), ev)
        if c:
            carreras.append(c)
        else:
            descartes.append(motivo)
    return carreras, descartes
