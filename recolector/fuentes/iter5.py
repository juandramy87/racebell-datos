"""Iter5 (iter5.cat, Chronos Iter5 de Lleida): cronometra la Lliga Ponent (asfalto y trail), las Mitges
Maratons de Ponent y marchas de Lleida. La portada lista las inscripciones abiertas con nombre, fecha
(«22-Novembre-2026»), web oficial, enlace al formulario y el tipo en las clases (`ls-10k`, `ls-5k`, `ls-mm`,
`ls-trail`, `ls-marxa`, `ls-duatlo`, `ls-btt`, `ls-infantil`…). No da el pueblo: se saca del nombre; si no
sale, se supone Lleida (es un cronometrador de Ponent) y se avisa. Nunca se abre «Llistat inscrits»."""
from __future__ import annotations

from bs4 import BeautifulSoup

from fuentes import cataluna as cat
from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, PENDIENTE_CARTEL, Carrera, Fuente

ID = "iter5"
URL = "https://www.iter5.cat/"
_KM = {"ls-5k": 5.0, "ls-10k": 10.0, "ls-mm": 21.097}
_A_PIE = {"ls-5k", "ls-10k", "ls-mm", "ls-trail"}
_FUERA = {"ls-duatlo": "duatlón", "ls-btt": "BTT", "ls-infantil": "infantil", "ls-altres": "no es una carrera"}


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    sopa = BeautifulSoup(contenido, "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for bloque in sopa.select("div.mix"):
        titulo = bloque.find("span")
        cuando = bloque.select_one("small.font-lato")
        form = bloque.select_one("a[href*='formCursa.php']")
        if not (titulo and cuando and form) or form["href"] in vistas:
            continue
        vistas.add(form["href"])
        nombre = nz.nombre(cat.texto(titulo.get_text(" ", strip=True)))
        tipos = set(bloque.get("class", []))
        fuera = next((motivo for clase, motivo in _FUERA.items() if clase in tipos), None)
        if fuera or not tipos & _A_PIE:
            descartes.append(f"no es a pie ({fuera or 'marcha'}): {nombre}")
            continue
        fecha = cat.fecha(cuando.get_text(" ", strip=True))
        if not fecha:
            descartes.append(f"sin fecha: {nombre}")
            continue
        a_pie, modalidad = cat.clasificar(nombre, *(["trail"] if "ls-trail" in tipos else []))
        if not a_pie or cat.es_infantil(nombre):
            descartes.append(f"no es a pie o infantil: {nombre}")
            continue
        lugar = cat.municipio_en(nombre)
        oficial = bloque.select_one("a.thumbnail")
        c = Carrera(
            nombre=nombre,
            fecha=fecha,
            fuente=Fuente(ID, form["href"]),
            poblacion=lugar[0] if lugar else None,
            provincia=lugar[1] if lugar else "Lleida",
            modalidad=modalidad or ("asfalto" if tipos & {"ls-5k", "ls-10k", "ls-mm"} else None),
            distancias_km=sorted(set(cat.distancias(nombre)) | {km for clase, km in _KM.items() if clase in tipos}),
            estado_fuente=ABIERTA,  # la portada solo enseña las de inscripción abierta
            url_inscripcion=form["href"],
        )
        if oficial and oficial.get("href"):
            c.previos.append(f"Web oficial: {oficial['href']}")
        if not lugar:
            c.marcar("Población no indicada en Iter5: se supone provincia de Lleida", PENDIENTE_CARTEL)
        c.marcar("Cierre de inscripción en el formulario de Iter5", PENDIENTE_CARTEL)
        carreras.append(c)
    return carreras, descartes
