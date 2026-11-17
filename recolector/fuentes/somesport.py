"""Som Esport (`somesport.com`): cronometrador de la Marina Alta y la Marina Baixa (Alicante) y la Safor.
Su portada es el calendario (WordPress con Divi): cada columna trae el cartel, la fecha en valenciano o en
castellano («22 de novembre 2026»), el municipio (h4), el nombre, botones de inscripción (`…/correr-26.php`) y
las distancias («Córrer 7 Km»). Se quitan los circuitos (columnas con un periodo «27 setembre al 29
novembre») y lo que solo es caminar. robots.txt: Yoast, `Disallow:` vacío (todo permitido)."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from fuentes import levante
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "somesport"
URL = "https://www.somesport.com/"

_MESES = {"gener": 1, "enero": 1, "febrer": 2, "febrero": 2, "marc": 3, "marzo": 3, "abril": 4, "maig": 5,
          "mayo": 5, "juny": 6, "junio": 6, "juliol": 7, "julio": 7, "agost": 8, "agosto": 8, "setembre": 9,
          "septiembre": 9, "octubre": 10, "novembre": 11, "noviembre": 11, "desembre": 12, "diciembre": 12}
_FECHA = re.compile(r"^(\d{1,2})\s+(?:de\s+)?(\w+)\s+(?:de\s+)?(\d{4})$")
_CORRER = re.compile(r"\bc[oó]rrer\s+([\d.,]+)\s*km(?:\s+o\s+([\d.,]+)\s*km)?", re.I)


def columnas(contenido: bytes | str) -> list[dict]:
    sopa = BeautifulSoup(contenido, "html.parser")
    salida = []
    for col in sopa.select("div.et_pb_column"):
        municipio = col.select_one("h4.et_pb_module_header")
        textos = [t.get_text(" ", strip=True) for t in col.select("div.et_pb_text_inner")]
        if not municipio or len(textos) < 2:
            continue
        botones = [(a.get_text(" ", strip=True), a.get("href", "")) for a in col.select("a.et_pb_button")]
        salida.append({"fecha": textos[0], "municipio": municipio.get_text(" ", strip=True),
                       "nombre": textos[1], "detalle": " ".join(textos[2:]), "botones": botones})
    return salida


def _municipio(texto: str) -> Optional[tuple[str, str]]:
    """El INE escribe «Alfàs del Pi, l'»; la web, «l'Alfàs del Pi»."""
    hallado = nz.municipio_espana(texto)
    m = re.match(r"(?i)(l'|el |la |els |les )(.+)", texto.strip())
    if not hallado and m:
        hallado = nz.municipio_espana(f"{m.group(2)}, {m.group(1).strip().lower()}")
        if hallado:
            hallado = (texto.strip()[:1].upper() + texto.strip()[1:], hallado[1])
    return hallado


def _fecha(texto: str) -> Optional[date]:
    m = _FECHA.match(re.sub(r"\s+", " ", nz.clave(texto)).strip())
    if not m or m.group(2) not in _MESES:
        return None
    return date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for col in columnas(contenido):
        nombre = nz.nombre(col["nombre"].rstrip(". "))
        fecha = _fecha(col["fecha"])
        if not fecha:  # circuitos («27 setembre al 29 novembre 2026») o pruebas sin día («2026», aplazadas)
            descartes.append(f"sin fecha de un día: {nombre} ({col['fecha']})")
            continue
        detalle = col["detalle"] + " " + " ".join(t for t, _ in col["botones"])
        if not _CORRER.search(detalle):
            descartes.append(f"no es a pie (solo caminar): {nombre}")
            continue
        a_pie, modalidad = levante.clasificar(nombre)
        if not a_pie:
            a_pie, modalidad = levante.clasificar(nombre + " cursa")  # «Cross», «Cursa solidària»…
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        hallado = _municipio(col["municipio"])
        poblacion, provincia = hallado if hallado else (nz.poblacion(col["municipio"]), "Alicante")
        kms = sorted({float(k.replace(",", ".")) for par in _CORRER.findall(detalle) for k in par if k}
                     | set(levante.distancias(nombre)))
        enlaces = [(t, h) for t, h in col["botones"] if h.startswith("http") and "llistat" not in h.lower()]
        enlace = next((h for t, h in enlaces if "correr" in nz.clave(t + h)), enlaces[0][1] if enlaces else None)
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, enlace or URL),
            poblacion=poblacion,
            provincia=provincia,
            modalidad=modalidad,
            distancias_km=kms,
            url_inscripcion=enlace,
        )
        estado = nz.clave(col["detalle"] + " " + " ".join(t for t, _ in col["botones"]))
        if "tancades" in estado or "cerradas" in estado:
            c.estado_fuente = "cerrada"
        elif "obertes" in estado or "abiertas" in estado:
            c.estado_fuente = "abierta"
        if not hallado:  # pedanías como Jesús Pobre (Dénia): la web es de las Marinas
            c.marcar(f"Municipio «{col['municipio']}» no está en el INE: provincia Alicante supuesta", "pendiente_cartel")
        c.marcar("Hora y cierre de inscripción en el reglamento de Som Esport", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
