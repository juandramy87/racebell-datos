"""Federació d'Atletisme de la Comunitat Valenciana: calendario de la temporada
(`facv.es/calendario/es`, HTML). Por GET salen los meses en curso (noviembre y diciembre); los
siguientes se piden con un formulario POST que `red.descargar` no hace.
Cada prueba: «Nombre / Población - Provincia/Província», «Fecha: dd/mm/aa», a veces «Hora», tipo
(Ruta, Cross, Aire Libre, Pista Cubierta, Marcha…), ámbito (Internacional, Nacional, Autonómico, Juegos
Deportivos…) y organizador. Solo se guardan Ruta, Cross y Montaña/Trail; fuera las de juegos escolares y
municipales, que no son populares. robots.txt no existe (404)."""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from fuentes import levante
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "facv"
URL = "https://www.facv.es/calendario/es"

_TIPOS = {"ruta": "asfalto", "cross": "cross", "montana": "montaña", "trail": "trail"}
_NO_POPULAR = re.compile(r"\b(juegos deportivos|juegos municipales|jecv|jjmm|escolar)\b")


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for bloque in sopa.select("div.bloque_resultado .resultado_titulo_competicion"):
        negritas = [b.get_text(" ", strip=True) for b in bloque.find_all("b")]
        texto = re.sub(r"\s+", " ", bloque.get_text(" ", strip=True))
        titulo = bloque.select_one("a.titulo_competicion")
        nombre = nz.nombre(titulo.get_text(" ", strip=True) if titulo else (negritas[0] if negritas else ""))
        tipo = next((_TIPOS[nz.clave(b)] for b in negritas if nz.clave(b) in _TIPOS), None)
        if not tipo:
            continue  # pista, marcha atlética, etc.: no se anota, son muchas
        if _NO_POPULAR.search(nz.clave(texto)):
            descartes.append(f"competición escolar o municipal: {nombre}")
            continue
        a_pie, modalidad = levante.clasificar(nombre)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        lugar = re.search(r"/\s*([^/]+?)\s+-\s+([^/\s][^/]*(?:/[^/]*?)?)\s+Fecha:", texto)
        poblacion = lugar.group(1).strip() if lugar else None
        provincia = nz.provincia(lugar.group(2).split("/")[0].strip()) if lugar and lugar.group(2) else None
        if nz.comunidad(provincia) != "valenciana":
            descartes.append(f"fuera de la Comunitat Valenciana: {nombre} ({lugar.group(2) if lugar else '?'})")
            continue
        if re.search(r"\bcampeonato (de espana|de europa|autonomico)\b", nz.clave(nombre)):
            descartes.append(f"campeonato federado (la carrera popular va aparte): {nombre}")
            continue
        fecha_m = re.search(r"Fecha:\s*(\d{2})/(\d{2})/(\d{2,4})", texto)
        if not fecha_m:
            descartes.append(f"sin fecha: {nombre}")
            continue
        anyo = int(fecha_m.group(3))
        hora_m = re.search(r"Hora:\s*(\d{1,2}):(\d{2})", texto)
        enlace = titulo.get("href") if titulo and titulo.get("href", "").startswith("http") else None
        c = Carrera(
            nombre=nombre,
            fecha=date(anyo + 2000 if anyo < 100 else anyo, int(fecha_m.group(2)), int(fecha_m.group(1))),
            fuente=Fuente(ID, enlace or URL),
            hora=f"{int(hora_m.group(1)):02d}:{hora_m.group(2)}" if hora_m else None,
            poblacion=nz.poblacion(re.sub(r"\s*\(.*?\)", "", poblacion or "")) or None,
            provincia=provincia,
            modalidad=modalidad if modalidad and tipo == "asfalto" else tipo,
            distancias_km=levante.distancias(re.sub(r"circuito.*$", "", nombre, flags=re.I)),  # «Circuito … 42k» no es la distancia
        )
        c.marcar("Inscripción y plazos en la web de la carrera (calendario FACV)", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
