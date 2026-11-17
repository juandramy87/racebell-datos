"""Ayuntamientos de la Comunidad de Madrid (fuera de la capital) y webs oficiales de sus carreras.

Tres vías, todas con datos públicos y sin inscritos:

1. **Agendas municipales con «The Events Calendar»** (WordPress): 19 ayuntamientos de Madrid usan el mismo
   plugin y su API pública `/wp-json/tribe/events/v1/events?start_date=…&end_date=…` (JSON con título, fecha y
   hora, categorías y lugar). Se quedan las que parecen carreras a pie (`_ES_CARRERA` + `nz.clasificar`).
   Lista sacada el 17/11/2026 probando `/wp-json/` en las webs oficiales de los 179 municipios (Wikidata P856).
2. **Agendas con «Modern Events Calendar» (MEC)**: la API `wp/v2/mec-events?search=…` da título y enlace (no la
   fecha); de las que parecen carreras se abre la ficha y se lee su JSON-LD `Event` (`startDate`).
3. **Webs oficiales de carreras municipales** que siguen en la misma dirección cada año (`WEBS`). Muchas son
   microwebs que Deporticket hace a los organizadores (`sansilvestrealcorcon.com`, …) con JSON-LD `SportsEvent`;
   las demás se leen del título y del texto («31 de diciembre de 2026», «Salida 10:00 h»). Si la web aún
   enseña la edición pasada, la fecha queda atrás y no sale.

robots.txt revisado el 17/11/2026: ninguno prohíbe `/wp-json/` ni las agendas (Soto del Real solo cierra
`/calendar/action~…` y bots concretos). Las microwebs de Deporticket no tienen robots.txt (404) ni reto antibots;
la web central `deporticket.com` sí tiene reto de Cloudflare y NO se usa."""
from __future__ import annotations

import html as html_mod
import json
import re
from datetime import date, datetime, timedelta
from typing import Callable, Optional
from urllib.parse import urlencode

from fuentes import jsonld
from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "aytos_madrid"
PROVINCIA = "Madrid"

# Ayuntamientos con The Events Calendar (base de la web → municipio).
TEC = {
    "https://manzanareselreal.es": "Manzanares el Real",
    "https://www.ayto-sotodelreal.es": "Soto del Real",
    "https://www.ayuntamientodebustarviejo.org": "Bustarviejo",
    "https://www.valdeolmos-alalpardo.org": "Valdeolmos-Alalpardo",
    "https://www.robregordo.com": "Robregordo",
    "https://www.grinon.es": "Griñón",
    "https://www.elmolar.org": "El Molar",
    "https://www.pinilladelvalle.org": "Pinilla del Valle",
    "https://www.villanuevadeperales.es": "Villanueva de Perales",
    "https://www.ayto-moraleja.es": "Moraleja de Enmedio",
    "https://www.estremera.es": "Estremera",
    "https://www.talamancadejarama.org": "Talamanca de Jarama",
    "https://www.villarejodesalvanes.es": "Villarejo de Salvanés",
    "https://www.villalbilla.es": "Villalbilla",
    "https://titulcia.es": "Titulcia",
    "https://ayuntamientovaldeavero.es": "Valdeavero",
    "https://valdelaguna.org": "Valdelaguna",
    "https://www.sanmartindevaldeiglesias.es": "San Martín de Valdeiglesias",
    "https://www.ayto-ciempozuelos.org": "Ciempozuelos",
    "https://breadetajo.es": "Brea de Tajo",
}

# Ayuntamientos con Modern Events Calendar.
MEC = {
    "https://coslada.es": "Coslada",
    "https://www.ayto-villacanada.es": "Villanueva de la Cañada",
    "https://www.sanlorenzodeelescorial.org": "San Lorenzo de El Escorial",
    "https://www.moralzarzal.es": "Moralzarzal",
    "https://torrelaguna.es": "Torrelaguna",
    "https://villaviejadellozoya.es": "Villavieja del Lozoya",
    "https://laacebeda.org": "La Acebeda",
    "https://lossantosdelahumosa.eu": "Los Santos de la Humosa",
}
MEC_BUSQUEDAS = ("carrera", "cross", "silvestre", "trail")

# Webs oficiales de carreras municipales (URL → municipio). Revisar cada temporada.
WEBS = {
    "https://www.sansilvestrealcorcon.com/": "Alcorcón",  # Deporticket (JSON-LD); organiza Club Atletismo Alcorcón
    "https://www.sansilvestrecolmenarviejo.com/": "Colmenar Viejo",  # Deporticket (JSON-LD)
    "https://www.sansilvestredelasrozas.es/": "Las Rozas de Madrid",  # Deporticket (texto); Ayuntamiento
    "https://sanselvestre.es/": "San Sebastián de los Reyes",  # Ayuntamiento; inscripción en Pebetero
    "https://www.mediadegetafe.com/": "Getafe",  # Media Maratón; inscripción en RunRun Sports
}

# Lo que parece una carrera a pie en el título de una agenda municipal…
_ES_CARRERA = re.compile(
    r"\b(carrera|cross|san ?silvestre|sanselvestre|trail|legua|marat[oó]n|milla|backyard|running|"
    r"\d+ ?km?\b|kil[oó]metros?)", re.I)
# …y lo que no lo es aunque lo nombre (charlas, cursos, carreras infantiles escolares…).
_NO_CARRERA = re.compile(
    r"\b(charla|taller|curso|conferencia|presentaci[oó]n|entrega de premios|exposici[oó]n|nutrici[oó]n|"
    r"inscripci[oó]n abierta para|escolar|carrera profesional|orientaci[oó]n laboral)", re.I)

_MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
     "noviembre", "diciembre"], 1)}
_FECHA = re.compile(r"\b(\d{1,2})\.?\s+(?:de\s+)?(" + "|".join(_MESES) + r")\.?\s+(?:de\s+|del\s+)?(20\d\d)\b", re.I)
_HORA_SALIDA = re.compile(r"salida[^0-9]{0,40}?(\d{1,2})[:.](\d{2})\s*(?:h|horas)?", re.I)
_PLATAFORMAS = re.compile(
    r'href="(https?://(?:[\w-]+\.)*(?:deporticket\.com/web-evento|pebetero\.com/actividad|runrunsports\.com/eventos|'
    r'rockthesport\.com|youevent\.es|sportmaniacs\.com|timinglap\.com/inscripcion|avaibooksports\.com/inscripcion)'
    r'[^"]*)"', re.I)


def _texto(fragmento: str) -> str:
    return re.sub(r"\s+", " ", html_mod.unescape(re.sub(r"<[^>]+>", " ", fragmento or ""))).strip()


def _es_carrera(*textos: Optional[str]) -> bool:
    t = " ".join(x for x in textos if x)
    return bool(_ES_CARRERA.search(t)) and not _NO_CARRERA.search(t)


# ---------------------------------------------------------------- The Events Calendar

def url_tec(base: str, desde: date, hasta: date) -> str:
    return f"{base}/wp-json/tribe/events/v1/events?" + urlencode(
        {"per_page": 50, "start_date": desde.isoformat(), "end_date": hasta.isoformat()})


def _json(contenido: bytes | str):
    texto = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    return json.loads(texto.lstrip("﻿"))  # alguna web antepone el BOM


def leer_tec(contenido: bytes | str, municipio: str) -> tuple[list[Carrera], list[str], Optional[str]]:
    """Una página de la API de The Events Calendar → (carreras, descartes, URL de la página siguiente)."""
    datos = _json(contenido)
    carreras, descartes = [], []
    for ev in datos.get("events", []):
        nombre = nz.nombre(_texto(ev.get("title", "")))
        categorias = " ".join(c.get("name", "") for c in ev.get("categories") or [])
        if not _es_carrera(nombre):
            continue
        a_pie, modalidad = nz.clasificar(nombre, categorias)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre}")
            continue
        try:
            inicio = datetime.strptime(ev["start_date"][:16], "%Y-%m-%d %H:%M")
        except (KeyError, ValueError):
            descartes.append(f"sin fecha: {nombre}")
            continue
        lugar = ev.get("venue") if isinstance(ev.get("venue"), dict) else {}
        hallado = nz.municipio_espana(lugar.get("city")) if lugar.get("city") else None
        poblacion = hallado[0] if hallado and hallado[1] == PROVINCIA else municipio
        c = Carrera(nombre=nombre, fecha=inicio.date(), fuente=Fuente(ID, ev.get("url") or ""),
                    hora=None if ev.get("all_day") or inicio.strftime("%H:%M") == "00:00" else inicio.strftime("%H:%M"),
                    poblacion=poblacion, provincia=PROVINCIA, modalidad=modalidad,
                    distancias_km=nz.distancias_del_nombre(nombre))
        if isinstance(ev.get("image"), dict) and ev["image"].get("url"):
            c.cartel = ev["image"]["url"]
        try:
            c.coords = (float(lugar["geo_lat"]), float(lugar["geo_lng"]))
        except (KeyError, TypeError, ValueError):
            pass
        c.marcar("Agenda municipal: el cierre de inscripción y las distancias están en el cartel o la normativa",
                 "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes, datos.get("next_rest_url")


# ---------------------------------------------------------------- Modern Events Calendar

def urls_mec(base: str, hoy: date) -> list[str]:
    """Búsquedas en la API de WordPress (solo títulos y enlaces de los eventos tocados en los últimos meses)."""
    desde = hoy - timedelta(days=180)
    return [f"{base}/wp-json/wp/v2/mec-events?" + urlencode(
        {"per_page": 20, "search": q, "modified_after": f"{desde.isoformat()}T00:00:00", "_fields": "title,link"})
        for q in MEC_BUSQUEDAS]


def fichas_mec(contenido: bytes | str) -> list[tuple[str, str]]:
    """(título, enlace) de los eventos MEC que parecen carreras."""
    try:
        datos = _json(contenido)
    except json.JSONDecodeError:
        return []
    salida = []
    for ev in datos if isinstance(datos, list) else []:
        titulo = nz.nombre(_texto((ev.get("title") or {}).get("rendered", "")))
        if ev.get("link") and _es_carrera(titulo):
            salida.append((titulo, ev["link"]))
    return salida


def recortar_mec(datos: bytes) -> bytes:
    """De una ficha MEC solo se guarda el JSON-LD del evento y el og:title, sin organizador (puede ser una
    persona) ni descripción."""
    texto = jsonld.recortar(datos).decode("utf-8", "replace")
    texto = re.sub(r'"organizer":\s*\{.*?\}', '"organizer": {}', texto, flags=re.S)
    texto = re.sub(r'"description":\s*".*?",\s*\n', "", texto, flags=re.S)
    return texto.encode()


def leer_ficha_mec(contenido: bytes | str, url: str, titulo: str, municipio: str
                   ) -> tuple[Optional[Carrera], Optional[str]]:
    """El JSON-LD de MEC no siempre es JSON válido (comas sobrantes): se lee `startDate` con una expresión."""
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    bloques = [b for b in re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', html, re.S) if "startDate" in b]
    m = re.search(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2})(?:T(\d{2}):(\d{2}))?', bloques[0]) if bloques else None
    if not m:
        return None, f"sin fecha en la ficha: {titulo}"
    a_pie, modalidad = nz.clasificar(titulo)
    if not a_pie:
        return None, f"no es a pie: {titulo}"
    hora = f"{m.group(2)}:{m.group(3)}" if m.group(2) and f"{m.group(2)}:{m.group(3)}" != "00:00" else None
    c = Carrera(nombre=titulo, fecha=date.fromisoformat(m.group(1)), fuente=Fuente(ID, url), hora=hora,
                poblacion=municipio, provincia=PROVINCIA, modalidad=modalidad,
                distancias_km=nz.distancias_del_nombre(titulo))
    c.marcar("Agenda municipal: el cierre de inscripción y las distancias están en el cartel o la normativa",
             "pendiente_cartel")
    return c, None


# ---------------------------------------------------------------- Webs oficiales

def recortar_web(datos: bytes) -> bytes:
    """Deja el título, las etiquetas og, el JSON-LD, los enlaces a plataformas de inscripción y el texto visible
    (sin scripts ni estilos). Es lo único que se lee; así la caché y las muestras no guardan nada más."""
    html = datos.decode("utf-8", "replace")
    trozos = re.findall(r"<title[^>]*>.*?</title>", html, re.S | re.I)
    trozos += re.findall(r'<meta[^>]+property="og:[^"]+"[^>]*>', html)
    trozos += re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>.*?</script>', html, re.S)
    trozos += sorted({f'<a href="{u}"></a>' for u in _PLATAFORMAS.findall(html)})
    cuerpo = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    cuerpo = re.sub(r"<head.*?</head>", " ", cuerpo, flags=re.S | re.I)
    lineas = [re.sub(r"\s+", " ", x).strip() for x in html_mod.unescape(re.sub(r"<[^>]+>", "\n", cuerpo)).split("\n")]
    texto = "\n".join(x for x in lineas if x)
    return ("<html><head>\n" + "\n".join(trozos) + "\n</head><body><pre>\n" + html_mod.escape(texto)
            + "\n</pre></body></html>\n").encode()


def _meta(html: str, propiedad: str) -> Optional[str]:
    m = re.search(r'<meta[^>]+property="' + propiedad + r'"[^>]+content="([^"]*)"', html)
    return html_mod.unescape(m.group(1)).strip() if m else None


def _primera_fecha(texto: str, hoy: date) -> Optional[date]:
    """La primera fecha completa del texto («27 de diciembre de 2026», «31 enero 2027»). Solo vale si no ha pasado:
    las fechas de plazos de inscripción suelen venir sin año o antes que la carrera."""
    for d, mes, a in _FECHA.findall(texto):
        try:
            f = date(int(a), _MESES[mes.lower()], int(d))
        except ValueError:
            continue
        if f >= hoy:
            return f
    return None


def leer_web(contenido: bytes | str, url: str, municipio: str, hoy: date) -> tuple[Optional[Carrera], Optional[str]]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    if jsonld.eventos(html):
        c, motivo = jsonld.leer_ficha(html, url, ID, provincia_si_falta=PROVINCIA)
        if c:
            if c.fecha < hoy:
                return None, f"la web aún enseña la edición pasada: {c.nombre} {c.fecha}"
            c.poblacion, c.provincia, c.fuente = municipio, PROVINCIA, Fuente(ID, url)
            if not c.hora and (m := _HORA_SALIDA.search(_texto(html))) and int(m.group(1)) < 24:
                c.hora = f"{int(m.group(1)):02d}:{m.group(2)}"
            enlaces = _PLATAFORMAS.findall(html)
            if enlaces and (not c.url_inscripcion or c.url_inscripcion == url):
                c.url_inscripcion = enlaces[0]
            return c, None
        if motivo and not motivo.startswith("sin datos"):
            return None, motivo
    titulo = _texto((re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I) or [None, ""])[1])
    titulo = re.sub(r"^(Error \d+|Inicio)\s*\|\s*", "", titulo)
    cuerpo = _texto(re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I))
    fecha = _primera_fecha(titulo, hoy) or _primera_fecha(cuerpo, hoy)
    nombre = nz.nombre(re.split(r"\s+[|–]\s+", titulo)[0] if titulo else (_meta(html, "og:site_name") or ""))
    if not nombre or _FECHA.fullmatch(nombre):
        nombre = nz.nombre(_meta(html, "og:site_name") or nombre)
    if not fecha:
        return None, f"sin fecha de la próxima edición: {nombre or url}"
    a_pie, modalidad = nz.clasificar(nombre)
    if not a_pie:
        return None, f"no es a pie: {nombre}"
    m = _HORA_SALIDA.search(cuerpo)
    hora = f"{int(m.group(1)):02d}:{m.group(2)}" if m and int(m.group(1)) < 24 else None
    enlaces = _PLATAFORMAS.findall(html)
    c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, url), hora=hora, poblacion=municipio,
                provincia=PROVINCIA, modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre),
                url_inscripcion=enlaces[0] if enlaces else url, cartel=_meta(html, "og:image"))
    c.marcar("Web oficial leída del texto: comprobar fecha y cierre de inscripción", "pendiente_cartel")
    return c, None


# ---------------------------------------------------------------- Todo junto

def leer(bajar: Callable[[str], bytes], desde: date, hasta: date, hoy: Optional[date] = None,
         bajar_ficha: Optional[Callable[[str], bytes]] = None) -> tuple[list[Carrera], list[str]]:
    """`bajar` descarga una URL (con caché); `bajar_ficha` la de las fichas MEC (con `recortar_mec`) y las webs
    oficiales (con `recortar_web`): si no se da, se usa `bajar`. Un ayuntamiento que falla no para a los demás."""
    hoy = hoy or date.today()
    bajar_ficha = bajar_ficha or (lambda u, recortar=None: bajar(u))
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for base, municipio in TEC.items():
        url, paginas = url_tec(base, desde, hasta), 0
        while url and paginas < 5:
            try:
                cs, ds, url = leer_tec(bajar(url), municipio)
            except Exception as error:  # noqa: BLE001 - una web municipal caída no debe parar el resto
                descartes.append(f"{municipio}: agenda no disponible ({str(error)[:80]})")
                break
            carreras += cs
            descartes += ds
            paginas += 1
    for base, municipio in MEC.items():
        vistas: dict[str, str] = {}
        for u in urls_mec(base, hoy):
            try:
                vistas.update({enlace: titulo for titulo, enlace in fichas_mec(bajar(u))})
            except Exception as error:  # noqa: BLE001
                descartes.append(f"{municipio}: agenda no disponible ({str(error)[:80]})")
                break
        for enlace, titulo in vistas.items():
            try:
                c, motivo = leer_ficha_mec(bajar_ficha(enlace, recortar_mec), enlace, titulo, municipio)
            except Exception as error:  # noqa: BLE001
                c, motivo = None, f"{municipio}: ficha no disponible {enlace} ({str(error)[:60]})"
            if c and desde <= c.fecha <= hasta:
                carreras.append(c)
            elif motivo:
                descartes.append(motivo)
    for url, municipio in WEBS.items():
        try:
            c, motivo = leer_web(bajar_ficha(url, recortar_web), url, municipio, hoy)
        except Exception as error:  # noqa: BLE001
            c, motivo = None, f"web oficial no disponible {url} ({str(error)[:80]})"
        if c:
            carreras.append(c)
        elif motivo:
            descartes.append(motivo)
    return carreras, descartes
