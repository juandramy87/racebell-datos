"""Elitechip (Illes Balears): cronometrador e inscripciones de casi todas las carreras de las islas.
La web (Next.js) pinta el calendario con su propio JSON: `/api/competitions?fromDate=…&toDate=…` (un mes
como mucho por petición; si no, «Date range too wide»). Trae nombre, fecha, tipo (Running, TrailRunning,
Cursa per Muntanya, Duatlón, Hybrid Race, Marxa Nòrdica, Open BTT…), un texto con el lugar y el municipio,
y la fecha y hora de cierre de inscripción. robots.txt no existe (404): no prohíbe nada.

El JSON trae también recuentos de inscritos por recorrido (números, sin nombres): `recortar` los quita
antes de guardar la caché. Solo se guardan los campos de la carrera."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Optional

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "elitechip"
URL = "https://www.elitechip.net/api/competitions?fromDate={desde}&toDate={hasta}&scope=all&locale=es"
FICHA = "https://www.elitechip.net/es/competiciones/{slug}"
PROVINCIA = "Baleares"

_CAMPOS = ("id", "slug", "nombreCompeticion", "fechaInicio", "fechaFin", "fechaLimInsc", "horaLimInsc",
           "inicioInscripcion", "horaInicioInsc", "inscripcionOnline", "searchText", "idZona", "esEvento",
           "ocultarInternet", "tipoCompeticion")

# Los 67 municipios de Baleares (nombre oficial) y nombres en castellano o núcleos que salen en los textos.
MUNICIPIOS = [
    # Mallorca
    "Alaró", "Alcúdia", "Algaida", "Andratx", "Ariany", "Artà", "Banyalbufar", "Binissalem", "Búger", "Bunyola",
    "Calvià", "Campanet", "Campos", "Capdepera", "Consell", "Costitx", "Deià", "Escorca", "Esporles", "Estellencs",
    "Felanitx", "Fornalutx", "Inca", "Lloret de Vistalegre", "Lloseta", "Llubí", "Llucmajor", "Manacor",
    "Mancor de la Vall", "Maria de la Salut", "Marratxí", "Montuïri", "Muro", "Palma", "Petra", "Pollença",
    "Porreres", "Puigpunyent", "Sa Pobla", "Sant Joan", "Sant Llorenç des Cardassar", "Santa Eugènia",
    "Santa Margalida", "Santa Maria del Camí", "Santanyí", "Selva", "Sencelles", "Ses Salines", "Sineu", "Sóller",
    "Son Servera", "Valldemossa", "Vilafranca de Bonany",
    # Menorca
    "Alaior", "Es Castell", "Ciutadella de Menorca", "Ferreries", "Maó", "Es Mercadal", "Es Migjorn Gran",
    "Sant Lluís",
    # Eivissa y Formentera
    "Eivissa", "Sant Antoni de Portmany", "Sant Joan de Labritja", "Sant Josep de sa Talaia",
    "Santa Eulària des Riu", "Formentera",
]
_OTROS_NOMBRES = {
    "alcudia": "Alcúdia", "arta": "Artà", "pollensa": "Pollença", "soller": "Sóller", "andraitx": "Andratx",
    "santany": "Santanyí", "ciudadela": "Ciutadella de Menorca", "ciutadella": "Ciutadella de Menorca",
    "mahon": "Maó", "mao mahon": "Maó", "llorencina": "Sant Llorenç des Cardassar", "sant llorenc": "Sant Llorenç des Cardassar",
    "san antonio": "Sant Antoni de Portmany", "sant antoni": "Sant Antoni de Portmany", "santa eulalia": "Santa Eulària des Riu",
    "santa eularia": "Santa Eulària des Riu", "sant josep": "Sant Josep de sa Talaia", "san jose": "Sant Josep de sa Talaia",
    "sant francesc xavier": "Formentera", "sant francesc": "Formentera", "es pujols": "Formentera",
    "magaluf": "Calvià", "santa ponsa": "Calvià", "santa ponca": "Calvià", "peguera": "Calvià", "paguera": "Calvià",
    "portol": "Marratxí", "pont d inca": "Marratxí", "port de pollenca": "Pollença", "port d alcudia": "Alcúdia",
    "can picafort": "Santa Margalida", "colonia de sant jordi": "Ses Salines", "portocristo": "Manacor",
    "porto cristo": "Manacor", "cala d or": "Santanyí", "son fusteret": "Palma", "son ferriol": "Palma",
    "platja de palma": "Palma", "s arenal": "Llucmajor", "cala ratjada": "Capdepera", "portocolom": "Felanitx",
    "mercadal": "Es Mercadal", "calvianera": "Calvià", "migjorn": "Es Migjorn Gran", "es migjorn": "Es Migjorn Gran", "pobla": "Sa Pobla",
}
_NOMBRES = {nz.clave(m): m for m in MUNICIPIOS} | _OTROS_NOMBRES


def _c(texto: str) -> str:
    """clave() con apóstrofos y guiones como espacios: «s’Hostal» → «s hostal»."""
    return re.sub(r"\s+", " ", re.sub(r"[’'`´·\-–.,()/]", " ", nz.clave(texto))).strip()


_PATRON = re.compile(r"\b(" + "|".join(sorted((re.escape(_c(k)) for k in _NOMBRES), key=len, reverse=True)) + r")\b")
_NO_PUEBLO = re.compile(r"\bconsell (de|insular)\b")  # «Consell de Mallorca» no es el pueblo de Consell


def municipio(*textos: Optional[str]) -> Optional[str]:
    """Municipio balear que aparece en los textos (el primero que tenga uno; el nombre más largo gana)."""
    for texto in textos:
        if not texto:
            continue
        t = _NO_PUEBLO.sub(" ", _c(texto))
        hallados = _PATRON.findall(t)
        if hallados:
            mejor = max(hallados, key=len)
            return _NOMBRES.get(mejor) or next(v for k, v in _NOMBRES.items() if _c(k) == mejor)
    return None


def solo_infantil(nombre: str) -> bool:
    """«Veolia Sant Silvestre Kids» sí; «Cursa Sant Juniper & Sant Juniper Kids» no (hay prueba de adultos)."""
    t = _c(nombre)
    return bool(re.search(r"\b(kids|infantil|infantils|menuts)\b", t)) and not re.search(r"[&+]| i | y | e ", f" {nombre} ")


def urls(desde: date, hasta: date) -> list[str]:
    """Una URL por mes natural entre `desde` y `hasta` (la API no acepta rangos de más de un mes)."""
    salida, inicio = [], date(desde.year, desde.month, 1)
    while inicio <= hasta:
        siguiente = date(inicio.year + inicio.month // 12, inicio.month % 12 + 1, 1)
        salida.append(URL.format(desde=inicio.isoformat(), hasta=(siguiente - timedelta(days=1)).isoformat()))
        inicio = siguiente
    return salida


def recortar(datos: bytes) -> bytes:
    """Deja solo los campos de la carrera (fuera recuentos de inscritos, estado de clasificaciones…)."""
    try:
        lista = json.loads(datos)
    except ValueError:
        return datos
    if not isinstance(lista, list):
        return datos
    return json.dumps([{k: e.get(k) for k in _CAMPOS if k in e} for e in lista], ensure_ascii=False).encode()


def _cuando(dia: Optional[str], hora: Optional[str]) -> Optional[datetime]:
    if not dia:
        return None
    d = datetime.fromisoformat(dia[:19])
    if hora:
        h = datetime.fromisoformat(hora[:19])
        return d.replace(hour=h.hour, minute=h.minute)
    return d.replace(hour=23, minute=59)


def leer(paginas: list[bytes | str]) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set = set()
    for pagina in paginas:
        for e in json.loads(pagina):
            if e.get("id") in vistas or e.get("ocultarInternet"):
                continue
            vistas.add(e.get("id"))
            nombre = nz.nombre(e.get("nombreCompeticion") or "")
            tipo = (e.get("tipoCompeticion") or {}).get("tipo") or ""
            if e.get("esEvento"):
                descartes.append(f"evento con varias pruebas (se leen sus pruebas): {nombre}")
                continue
            # El tipo manda: «Running», «TrailRunning», «Cursa per Muntanya», «Cros»… Lo demás (BTT, natación,
            # duatlón, marcha nórdica, carreras híbridas…) se descarta aunque el nombre diga «cursa».
            if not re.search(r"running|trail|muntanya|montana|cros|atletisme|atletismo|ocr|obstacul", nz.clave(tipo)):
                descartes.append(f"no es a pie: {nombre} ({tipo})")
                continue
            if solo_infantil(nombre):
                descartes.append(f"solo infantil: {nombre}")
                continue
            a_pie, modalidad = nz.clasificar(nombre, tipo.replace("TrailRunning", "trail"))
            if not a_pie or re.search(r"\bcamina(da|ta)?\b|nordic|walking", _c(nombre)):
                descartes.append(f"no es a pie: {nombre} ({tipo})")
                continue
            if "trailrunning" in nz.clave(tipo) and modalidad in (None, "asfalto"):
                modalidad = "trail"
            elif "muntanya" in nz.clave(tipo) and modalidad in (None, "asfalto", "trail"):
                modalidad = "montaña"
            texto = e.get("searchText") or ""
            sitio = texto[len(nz.clave(nombre)):] if nz.clave(texto).startswith(nz.clave(nombre)) else texto
            url = FICHA.format(slug=e["slug"])
            c = Carrera(
                nombre=nombre,
                fecha=date.fromisoformat(e["fechaInicio"][:10]),
                fuente=Fuente(ID, url),
                poblacion=municipio(sitio, nombre),
                provincia=PROVINCIA,
                modalidad=modalidad,
                distancias_km=nz.distancias_del_nombre(nombre),
                url_inscripcion=url if e.get("inscripcionOnline") else None,
            )
            c.inscripcion_hasta = _cuando(e.get("fechaLimInsc"), e.get("horaLimInsc"))
            c.inscripcion_desde = _cuando(e.get("inicioInscripcion"), e.get("horaInicioInsc"))
            if c.inscripcion_desde and c.inscripcion_desde.year < 2000:
                c.inscripcion_desde = None
            if not c.inscripcion_hasta:
                c.marcar("Cierre de inscripción no indicado en Elitechip", "pendiente_cartel")
            if not c.poblacion:
                c.marcar("Municipio no indicado en Elitechip", "pendiente_cartel")
            carreras.append(c)
    return carreras, descartes
