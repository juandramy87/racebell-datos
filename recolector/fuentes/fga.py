"""Federación Galega de Atletismo (atletismo.gal/competicions/): calendario de toda Galicia, un mes por
página (`?cp_date=01/MM/AAAA`). Cada competición trae fecha, tipo (Ruta, Campo a Través, Trail Running,
Pista…), nombre, lugar y la delegación (que dice la provincia). Textos en gallego.
Las inscripciones van por Carreiras Galegas (la plataforma de la propia FGA), enlazada desde cada ficha.
Sin robots.txt. Se quitan pista, marcha, escolares (XOGADE, JJDD), tecnificación y reuniones."""
from __future__ import annotations

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import PENDIENTE_CARTEL, Carrera, Fuente

ID = "fga"
URL = "https://atletismo.gal/competicions/"
URL_MES = "https://atletismo.gal/competicions/?cp_date=01/{mes:02d}/{anyo}"

# Delegación de la FGA → provincia.
_DELEGACION = {
    "a-coruna": "A Coruña", "santiago": "A Coruña", "ferrol": "A Coruña",
    "lugo": "Lugo",
    "ourense": "Ourense", "valdeorras": "Ourense",
    "pontevedra": "Pontevedra", "vigo": "Pontevedra",
}
_TIPO_MODALIDAD = {"ruta": "asfalto", "campo a traves": "cross", "trail running": "trail", "montana": "montaña"}
# Lo que no es una carrera popular a pie: escolares, tecnificación, asambleas, controles…
_NO_POPULAR = re.compile(r"\b(xogade|jjdd|escolar|pgta|pntd|tecnificacion|sesion tecnica|asemblea|asamblea|"
                         r"control|charla|curso|xornada de|plan galego)")


def urls(hoy: date, meses: int = 3) -> list[str]:
    """Páginas del mes actual y de los siguientes."""
    salida = []
    anyo, mes = hoy.year, hoy.month
    for _ in range(meses):
        salida.append(URL_MES.format(mes=mes, anyo=anyo))
        anyo, mes = (anyo + 1, 1) if mes == 12 else (anyo, mes + 1)
    return salida


def _poblacion(texto: str) -> str | None:
    """«Coruña, A» → «A Coruña»; «Pereiro de Aguiar, O» → «O Pereiro de Aguiar»; «Varias sedes» → None."""
    t = re.sub(r"\s+", " ", texto).strip()
    if not t or "varias sedes" in nz.clave(t):
        return None
    t = re.sub(r"\s*\(.*?\)\s*", " ", t).strip()  # «Aldea Novas (Ames)» → «Aldea Novas»
    if m := re.match(r"^(.+?),\s*(A|O|As|Os)$", t):
        t = f"{m.group(2)} {m.group(1)}"
    return nz.poblacion(t)


def _distancias(nombre: str) -> list[float]:
    """Como nz.distancias_del_nombre, pero entiende el gallego «Medio Maratón» (si no, daría 42,195)."""
    if "medio maraton" in nz.clave(nombre):
        return sorted(set([k for k in nz.distancias_del_nombre(nombre) if k != 42.195] + [21.097]))
    return nz.distancias_del_nombre(nombre)


def leer(paginas: list[bytes | str]) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for contenido in paginas:
        sopa = BeautifulSoup(contenido, "html.parser")
        for art in sopa.select("article.competition"):
            enlace = art.select_one("h2 a[href]")
            fecha_el = art.select_one("div.bg-red span")
            if not enlace or not fecha_el:
                continue
            url = enlace["href"]
            if url in vistas:  # una competición de varios días sale en dos meses
                continue
            vistas.add(url)
            nombre = nz.nombre(enlace.get_text(" ", strip=True))
            tipo_el = art.select_one("div.space-x-2 > span.text-sm")
            tipo = tipo_el.get_text(" ", strip=True) if tipo_el else ""
            modalidad = _TIPO_MODALIDAD.get(nz.clave(tipo))
            if nz.clave(tipo).startswith("pista") and re.search(r"\bmilla\b", nz.clave(nombre)):
                modalidad = "pista"  # las millas populares van como «Pista»; el resto de pista es federado
            if not modalidad and not tipo:
                # Sin tipo: solo si el nombre dice claramente que es una carrera (el resto son charlas, galas…).
                modalidad = nz.clasificar(nombre)[1] if re.search(
                    r"\b(trail|cros|cross|carreira|carrera|san silvestre|maraton)\b", nz.clave(nombre)) else None
            if not modalidad:
                descartes.append(f"no es carrera popular a pie: {nombre} ({tipo or 'sin tipo'})")
                continue
            if _NO_POPULAR.search(nz.clave(nombre)):
                descartes.append(f"no es carrera popular: {nombre}")
                continue
            a_pie, mod_nombre = nz.clasificar(nombre, tipo if modalidad != "asfalto" else "")
            if not a_pie:
                descartes.append(f"no es a pie: {nombre} ({tipo})")
                continue
            delegaciones = [c.removeprefix("delegation-") for c in art.get("class", []) if c.startswith("delegation-")]
            provincia = next((_DELEGACION[d] for d in delegaciones if d in _DELEGACION), None)
            if not provincia:
                descartes.append(f"sin provincia: {nombre} ({', '.join(delegaciones)})")
                continue
            lugar = art.select_one("div.text-base")
            c = Carrera(
                nombre=nombre,
                fecha=datetime.strptime(fecha_el.get_text(strip=True), "%d/%m/%Y").date(),
                fuente=Fuente(ID, url),
                poblacion=_poblacion(lugar.get_text(" ", strip=True)) if lugar else None,
                provincia=provincia,
                modalidad=mod_nombre if mod_nombre in ("montaña", "obstáculos") else modalidad or "asfalto",
                distancias_km=_distancias(nombre),
            )
            c.marcar("Hora, precio y cierre de inscripción en Carreiras Galegas (enlazada en la ficha de la FGA)",
                     PENDIENTE_CARTEL)
            carreras.append(c)
    return carreras, descartes
