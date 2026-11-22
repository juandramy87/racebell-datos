"""Agenda oficial de Turismo de Islas Canarias (Gobierno de Canarias): `holaislascanarias.com/eventos/`, filtrada por
la categoría «Deportes de Resistencia». Es la única lista común de las siete islas: trae carreras de Gran Canaria,
Lanzarote, Fuerteventura, La Palma, La Gomera y El Hierro que no salen en ningún cronometrador que leamos.

Web nueva (Next.js, noviembre de 2026): el filtro va en `?category=<id>`, la isla y el municipio en la ruta, y cada página trae
dentro, en JSON, cada evento: nombre, isla, municipio, coordenadas, descripción corta, `dateFrom`/`dateTo` (solo si hay
día exacto) o solo `estimatedMonth`/`estimatedYear`. Su servidor a veces devuelve la agenda SIN filtrar: se comprueba que
el filtro venga marcado (`"selected":["<id>"`) y, si no, se repite la petición.
Si la lista no da el día, se mira la ficha (JSON-LD `Event`: `startDate`/`endDate`): solo vale si empieza y acaba el
mismo día. Un mes entero («1 nov – 30 nov») no es un día: se descarta. De la ficha sale también «Ver la web»
(`goToWebsiteButton`), que se usa como `url_inscripcion` salvo que la propia web la corte con «…».

robots.txt: no tiene reglas para todos los robots (solo para algunos concretos). Es una agenda institucional (la
redactan los cabildos y Turismo de Canarias), no un agregador: si la misma carrera sale en una plataforma, se une con
ella y manda la plataforma."""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Callable, Optional

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "holaislascanarias"
BASE = "https://www.holaislascanarias.com"
CATEGORIA = "a9bf3274-9077-48dc-867a-25d92f515004"  # «Deportes de Resistencia»
URL_ISLA = f"{BASE}/eventos/{{}}/?category={CATEGORIA}"
URL_MUNICIPIO = f"{BASE}/eventos/{{}}/{{}}/?category={CATEGORIA}"
ISLAS = ["tenerife", "gran-canaria", "lanzarote", "fuerteventura", "la-palma", "la-gomera", "el-hierro"]
INTENTOS_FILTRO = 6
_PROVINCIA_ISLA = {
    "tenerife": "Santa Cruz de Tenerife", "la palma": "Santa Cruz de Tenerife", "la gomera": "Santa Cruz de Tenerife",
    "el hierro": "Santa Cruz de Tenerife", "gran canaria": "Las Palmas", "lanzarote": "Las Palmas",
    "fuerteventura": "Las Palmas", "la graciosa": "Las Palmas",
}
_MESES = {m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                      "septiembre", "octubre", "noviembre", "diciembre"], 1)}
# «Deportes de Resistencia» incluye bici, natación, crossfit…: lo que `nz.clasificar` no ve en el nombre.
_NO_A_PIE = re.compile(r"\b(bike|bikids|swim|swinrun|swimrun|open water|throwdown|crossfit|criterium|cronoescalada|"
                       r"thlon|travesia a nado|regata|vela)\b|\w+thlon\b")
# Pruebas de natación cuyo nombre no lo dice («The Blue Challenge»): se ve en la descripción.
_NADO = re.compile(r"\b(a nado|natacion|aguas abiertas|nadador)")
_CORRER = re.compile(r"\b(carrera|trail|cross|run|running|maraton|milla|san silvestre|km)\b")
_REDES = re.compile(r"^https?://(www\.|m\.)?(facebook|instagram|twitter|x|tiktok)\.com/")
_FLIGHT = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
_LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _datos_next(contenido: bytes | str) -> str:
    """El texto que Next.js manda troceado en `self.__next_f.push(...)`, ya unido y sin escapar."""
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    return "".join(json.loads(f'"{m}"') for m in _FLIGHT.findall(html))


def pagina(contenido: bytes | str) -> tuple[list[dict], int, bool]:
    """(eventos, total de resultados, ¿viene filtrado por «Deportes de Resistencia»?)."""
    texto = _datos_next(contenido)
    filtrado = f'"selected":["{CATEGORIA}"' in texto
    i = texto.find('"resources":[')
    if i < 0:
        return [], 0, filtrado
    eventos, _ = json.JSONDecoder().raw_decode(texto[i + len('"resources":'):])
    total = re.search(r'"totalResults":(\d+)', texto)
    return [e for e in eventos if e.get("resourceType") == "agenda"], int(total.group(1)) if total else len(eventos), filtrado


def municipios(contenido: bytes | str) -> list[str]:
    """Municipios de la isla elegida que tienen algún evento de la categoría (ids de la ruta: «santiago-del-teide»)."""
    texto = _datos_next(contenido)
    i = texto.find('"id":"municipality"')
    j = texto.find('"availableItems":[', i)
    if i < 0 or j < 0:
        return []
    lista, _ = json.JSONDecoder().raw_decode(texto[j + len('"availableItems":'):])
    return [m["id"] for m in lista if m.get("count")]


def _bajar_filtrado(bajar: Callable[[str], bytes], url: str) -> bytes:
    for _ in range(INTENTOS_FILTRO):
        contenido = bajar(url)
        if pagina(contenido)[2]:
            return contenido
    raise RuntimeError(f"{url} llega siempre sin filtrar")


def bajar_listado(bajar: Callable[[str], bytes]) -> list[dict]:
    """Todos los eventos de la categoría. La web solo pinta 16 por búsqueda (el resto lo pide el navegador a su API,
    que no se usa), así que se pide isla a isla (`/eventos/<isla>/`) y, si una isla pasa de 16, municipio a municipio
    (`/eventos/<isla>/<municipio>/`). `bajar(url)` NO debe usar la caché (el servidor a veces no filtra)."""
    vistos: dict[str, dict] = {}
    for isla in ISLAS:
        contenido = _bajar_filtrado(bajar, URL_ISLA.format(isla))
        lista, total, _ = pagina(contenido)
        trozos = [lista]
        if total > len(lista):
            trozos = [pagina(_bajar_filtrado(bajar, URL_MUNICIPIO.format(isla, m)))[0] for m in municipios(contenido)]
        for trozo in trozos:
            for e in trozo:
                vistos.setdefault(e.get("id") or e.get("url"), e)
    return list(vistos.values())


def recortar_ficha(contenido: bytes) -> bytes:
    """Guarda solo el JSON-LD del evento y el botón «Ver la web»."""
    html = contenido.decode("utf-8", "replace")
    evento = next((ld for ld in _LD.findall(html) if '"Event"' in ld), "{}")
    web = re.search(r'"goToWebsiteButton":\{[^{}]*\}', _datos_next(html))
    return json.dumps({"ld": evento, "web": web.group(0) if web else None}).encode()


def ficha(contenido: bytes | str) -> dict:
    """{inicio, fin, web} de una ficha recortada."""
    datos = json.loads(contenido)
    inicio = fin = None
    try:
        grafo = json.loads(datos.get("ld") or "{}")
        for nodo in grafo.get("@graph", [grafo]):
            if nodo.get("@type") == "Event":
                inicio = date.fromisoformat(nodo["startDate"][:10]) if nodo.get("startDate") else None
                fin = date.fromisoformat(nodo["endDate"][:10]) if nodo.get("endDate") else inicio
    except (ValueError, KeyError, AttributeError):
        pass
    web = None
    if datos.get("web"):
        m = re.search(r'"url":"([^"]+)"', datos["web"])
        web = m.group(1) if m else None
    return {"inicio": inicio, "fin": fin, "web": web}


def _web(url: Optional[str]) -> Optional[str]:
    """Web del evento sin rastreadores (utm_*, fbclid); ni redes sociales ni enlaces que la web corta con «…»."""
    if not url or _REDES.match(url) or url.endswith("…") or not url.startswith("http"):
        return None
    base, _, consulta = url.partition("?")
    quedan = [p for p in consulta.split("&") if p and not re.match(r"(utm_[a-z]+|fbclid|igsh|locale)=", p)]
    return base + ("?" + "&".join(quedan) if quedan else "")


def _mes_en_plazo(e: dict, desde: date, hasta: date) -> bool:
    mes, anio = _MESES.get(nz.clave(e.get("estimatedMonth") or "")), e.get("estimatedYear")
    if not mes or not anio:
        return True  # sin pista: se mira la ficha
    return date(anio, mes, 1) <= hasta and (date(anio + mes // 12, mes % 12 + 1, 1) > desde)


def leer(eventos: list[dict], descargar_ficha: Callable[[str], bytes], desde: date,
         hasta: date) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = [], []
    for e in eventos:
        nombre = nz.nombre(e.get("title") or "")
        url = BASE + e["url"] if e.get("url", "").startswith("/") else e.get("url", "")
        a_pie, modalidad = nz.clasificar(nombre)
        if not a_pie or _NO_A_PIE.search(nz.clave(nombre)):
            descartes.append(f"no es a pie: {nombre}")
            continue
        if _NADO.search(nz.clave(e.get("description") or "")) and not _CORRER.search(nz.clave(nombre)):
            descartes.append(f"no es a pie (natación según la descripción): {nombre}")
            continue
        provincia = _PROVINCIA_ISLA.get(nz.clave(e.get("island") or ""))
        if not provincia:
            descartes.append(f"sin isla: {nombre}")
            continue
        inicio = date.fromisoformat(e["dateFrom"]) if e.get("dateFrom") else None
        fin = date.fromisoformat(e["dateTo"]) if e.get("dateTo") else inicio
        if inicio and not desde <= inicio <= hasta:
            continue
        if not inicio and not _mes_en_plazo(e, desde, hasta):
            continue
        datos = {"inicio": None, "fin": None, "web": None}
        try:
            datos = ficha(descargar_ficha(url))
        except Exception as error:  # noqa: BLE001 - una ficha caída no tumba las demás
            descartes.append(f"ficha sin descargar ({error}): {nombre}")
        if not inicio:
            inicio, fin = datos["inicio"], datos["fin"]
        if not inicio or (fin and fin != inicio):
            descartes.append(f"sin día exacto ({e.get('estimatedMonth') or '?'} {e.get('estimatedYear') or ''}): {nombre}")
            continue
        if not desde <= inicio <= hasta:
            continue
        if not modalidad:
            a_pie_desc, mod_desc = nz.clasificar(e.get("description") or "")
            modalidad = mod_desc if a_pie_desc and mod_desc in {"trail", "montaña", "cross", "obstáculos"} else None
        hallado = nz.municipio_espana(e.get("municipality") or "")
        if hallado and hallado[1] == provincia:
            poblacion = hallado[0]
        else:
            poblacion = nz.poblacion(e["municipality"]) if e.get("municipality") else None
        coords = e.get("coordinates") or {}
        carreras.append(Carrera(
            nombre=nombre, fecha=inicio, fuente=Fuente(ID, url), poblacion=poblacion, provincia=provincia,
            coords=(float(coords["lat"]), float(coords["lng"])) if coords.get("lat") and coords.get("lng") else None,
            modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=_web(datos["web"]),
        ))
    return carreras, descartes
