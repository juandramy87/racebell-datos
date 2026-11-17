"""Federación Cántabra de Atletismo (fcatle.com): su calendario (All-in-One Event Calendar) se puede
exportar en iCalendar, el enlace «Suscríbete» de su web. Cada evento trae fecha y hora, nombre,
«Pueblo, Cantabria @ sitio» y la ficha (`/evento/DDMMAAAA/`). robots.txt solo prohíbe las vistas
`/calendar/action~…`. Se quedan las carreras de Cantabria; fuera pista, marcha y tecnificación, y las
competiciones de fuera de Cantabria que la federación también anuncia."""
from __future__ import annotations

import re
from datetime import datetime

from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "fcatle"
URL = ("https://www.fcatle.com/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller"
       "&action=export_events&no_html=true")

_NO_POPULAR = re.compile(r"\b(tecnificacion|pntd|lanzamiento|lanzamientos|pista|pruebas combinadas|control|"
                         r"jornada de menores|juegos escolares|escolar|reunion|asamblea|gala|curso|clinic)")


# Pista: reuniones en estadio/complejo deportivo que no se anuncian como carrera (campeonatos por edades,
# ligas de clubes, trofeos y grandes premios de pista). Se quedan los cross, millas, ruta y populares.
_INSTALACION = re.compile(r"\b(complejo deportivo|complejo deporitvo|complejos deportivos|estadio)\b")
_CARRERA = re.compile(r"\b(cross|campo a traves|carrera|milla|legua|san silvestre|kilometros|km|ruta|popular|subida)\b")
_DE_PUEBLO = re.compile(r"\b(?:de|del)\s+((?:el|la|los|las)\s+)?([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+(?:\s+(?:de\s+)?[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)*)\s*$")


def _campos(bloque: str) -> dict[str, str]:
    campos = {}
    for linea in bloque.split("\n"):
        nombre, _, valor = linea.partition(":")
        clave = nombre.split(";")[0].strip().upper()
        if clave and clave not in campos:
            campos[clave] = valor.strip()
    return campos


def _texto(valor: str) -> str:
    return re.sub(r"\s+", " ", valor.replace("\\,", ",").replace("\\;", ";").replace("\\n", " ")).strip()


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    ics = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    ics = re.sub(r"\r?\n[ \t]", "", ics.replace("\r\n", "\n"))  # líneas partidas (RFC 5545)
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for bloque in re.findall(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", ics, re.S):
        e = _campos(bloque)
        if not e.get("DTSTART") or not e.get("SUMMARY"):
            continue
        nombre = nz.nombre(_texto(e["SUMMARY"]))
        m = re.match(r"(\d{8})(?:T(\d{4}))?", e["DTSTART"])
        if not m:
            continue
        inicio = datetime.strptime(m.group(1) + (m.group(2) or "0000"), "%Y%m%d%H%M")
        if _NO_POPULAR.search(nz.clave(nombre)):
            descartes.append(f"no es carrera popular: {nombre}")
            continue
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        sitio = _texto(e.get("LOCATION", "")).partition("@")[2]
        if _INSTALACION.search(nz.clave(sitio)) and not _CARRERA.search(nz.clave(nombre)):
            descartes.append(f"pista (en {sitio.strip()}): {nombre}")
            continue
        lugar = _texto(e.get("LOCATION", "")).split("@")[0]
        partes = [p.strip() for p in re.split(r"[,()]", lugar) if p.strip()]
        provincias = {nz.provincia(p) for p in partes} - {None}
        if provincias and "Cantabria" not in provincias:
            descartes.append(f"fuera de Cantabria: {nombre} ({lugar.strip()})")
            continue
        if len(provincias) > 1:  # «Panes (Asturias) - Potes (Cantabria)»: llega a Cantabria; el pueblo es el cántabro
            i = next(i for i, p in enumerate(partes) if nz.provincia(p) == "Cantabria")
            poblacion = partes[i - 1].lstrip("- ").strip() if i else None
        else:
            poblacion = next((p for p in partes if nz.provincia(p) != "Cantabria"), None)
        if not poblacion and (m_pueblo := _DE_PUEBLO.search(nombre)):  # sin LOCATION: «… de El Astillero»
            candidato = "".join(g for g in m_pueblo.groups() if g)
            if (mun := nz.municipio_espana(candidato)) and mun[1] == "Cantabria":
                poblacion = mun[0]
        c = Carrera(
            nombre=nombre,
            fecha=inicio.date(),
            hora=inicio.strftime("%H:%M") if inicio.strftime("%H:%M") != "00:00" else None,
            fuente=Fuente(ID, e.get("URL") or "https://www.fcatle.com/calendario/"),
            poblacion=nz.poblacion(poblacion),
            provincia="Cantabria",
            modalidad=modalidad,
            distancias_km=nz.distancias_del_nombre(nombre),
        )
        c.marcar("Precio, cierre de inscripción y distancias en la ficha o el reglamento de la FCA", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
