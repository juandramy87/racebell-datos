"""RockTheSport: carreras de Madrid que el lector general (`fuentes/rockthesport.py`) descarta.

Muchas fichas de la capital (y algunas de la Comunidad) no traen provincia en su JSON-LD: el lugar es el barrio
(«Hortaleza», «La Elipa») o va vacío y solo lo dicen el nombre y las coordenadas («10K / 5K Sanchinarro 2027»).
`rockthesport.leer` solo adivina el pueblo con la tabla de municipios ANDALUCES, así que las guarda en
`datos/rockthesport-vistos.json` como «fuera de España o sin provincia» o «coordenadas fuera del municipio del
nombre» (cuando el slug nombra un pueblo andaluz homónimo: «…salvar-el-pinar-de-la-elipa»).

Este lector solo LEE ese archivo de vistos (lo escribe `rockthesport.leer`, que se ejecuta antes), escoge las
fichas descartadas que apuntan a Madrid (barrio o distrito de la capital, o municipio de la provincia en el
nombre, comprobado con las coordenadas) y las vuelve a leer con el lector común de JSON-LD.
Son pocas fichas por pasada (una veintena) y se descargan con `red.descargar` (caché del día).

Si algún día `rockthesport.py` usa `nz.municipio_espana` y `fuentes/madridcapital.py`, este lector sobra.
robots.txt de RockTheSport: prohíbe `/api/`; las fichas `/es/event/<slug>` se pueden leer."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from fuentes import jsonld, madridcapital
from nucleo import normalizar as nz
from nucleo.modelo import Carrera

ID = "rtsmadrid"
FICHA = "https://web.rockthesport.com/es/event/"
VISTOS = Path(__file__).resolve().parents[1] / "datos" / "rockthesport-vistos.json"
_MOTIVOS = ("fuera de España o sin provincia", "coordenadas fuera del municipio del nombre")


def municipio_madrid(texto: Optional[str]) -> Optional[str]:
    """Municipio de la provincia de Madrid (distinto de la capital) nombrado en el texto, o None.
    «vi-carrera-y-marcha-conquista-del-castillo-mejorada» no basta (falta «del Campo»); «Mejorada del Campo» sí."""
    palabras = nz.clave((texto or "").replace("-", " ")).split()
    for n in range(5, 0, -1):
        for i in range(len(palabras) - n + 1):
            trozo = " ".join(palabras[i:i + n])
            if len(trozo) < 4:
                continue
            hallado = nz.municipio_espana(trozo)
            if hallado and hallado[1] == "Madrid" and hallado[0] != "Madrid":
                return hallado[0]
    return None


def _en_provincia(coords: tuple[float, float]) -> bool:
    """Provincia de Madrid, en grueso."""
    return 39.88 <= coords[0] <= 41.17 and -4.58 <= coords[1] <= -3.05


def _pista(slug: str) -> bool:
    texto = madridcapital.palabras_slug(slug)
    return bool(madridcapital.barrio(texto) or municipio_madrid(texto) or " madrid " in f" {nz.clave(texto)} ")


def candidatas(vistos: dict) -> list[str]:
    """Fichas descartadas por el lector general que pueden ser de Madrid."""
    salida = []
    for slug, recuerdo in vistos.items():
        motivo = str(recuerdo.get("motivo", ""))
        if recuerdo.get("espana") is False and motivo.startswith(_MOTIVOS) and _pista(slug):
            if nz.clasificar(slug.replace("-", " "))[0]:
                salida.append(slug)
    return sorted(salida)


def _lugar_ficha(contenido: bytes | str) -> tuple[list[str], Optional[tuple[float, float]]]:
    """Textos de lugar (localidad, nombre del sitio, nombre de la prueba) y coordenadas de la ficha."""
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    evs = jsonld.eventos(html)
    if not evs:
        return [], None
    ev = evs[0]
    sitio = ev.get("location") or {}
    sitio = sitio[0] if isinstance(sitio, list) and sitio else sitio
    sitio = sitio if isinstance(sitio, dict) else {}
    direccion = sitio.get("address") or {}
    if isinstance(direccion, str):
        direccion = {"addressLocality": direccion}
    coords = None
    if geo := sitio.get("geo"):
        try:
            coords = (float(geo["latitude"]), float(geo["longitude"]))
        except (KeyError, TypeError, ValueError):
            coords = None
    textos = [direccion.get("addressLocality") or "", sitio.get("name") or "", ev.get("name") or ""]
    return textos, coords


def leer(vistos: dict, *, descargar_ficha: Callable[[str], bytes], desde: date, hasta: date
         ) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = [], []
    for slug in candidatas(vistos):
        url = FICHA + slug
        ficha = descargar_ficha(url)
        textos, coords = _lugar_ficha(ficha)
        if not textos:
            descartes.append(f"sin datos de evento: {url}")
            continue
        # 1) Un municipio de la provincia en la localidad o en el nombre (Mejorada del Campo, Pezuela…).
        pueblo = None
        for t in textos + [madridcapital.palabras_slug(slug)]:
            pueblo = municipio_madrid(t)
            if pueblo:
                break
        # 2) Un barrio o distrito de la capital (o «Madrid» a secas) con las coordenadas en el término.
        if pueblo and coords and not _en_provincia(coords):
            descartes.append(f"coordenadas fuera de la provincia de Madrid: {slug}")
            continue
        if not pueblo and (madridcapital.lugar(*textos, madridcapital.palabras_slug(slug), coords=coords)
                           or (coords and madridcapital.en_termino(coords)
                               and any(" madrid " in f" {nz.clave(t)} " for t in textos))):
            pueblo = "Madrid"
        if not pueblo:
            descartes.append(f"no es de Madrid o no se ubica: {slug}")
            continue
        c, motivo = jsonld.leer_ficha(ficha, url, ID, provincia_si_falta="Madrid")
        if not c:
            descartes.append(motivo or f"sin datos: {slug}")
            continue
        if c.provincia != "Madrid":
            descartes.append(f"la ficha dice otra provincia ({c.provincia}): {slug}")
            continue
        barrio = madridcapital.barrio(textos[0]) or madridcapital.barrio(textos[1])
        c.poblacion = pueblo
        # RockTheSport pone «SoldOut» en TODAS sus fichas (también en las abiertas): no se hace caso.
        c.previos = [p for p in c.previos if p != "Inscripciones agotadas"]
        if pueblo == "Madrid" and barrio and nz.clave(barrio) != "madrid":
            c.previos.append(f"Barrio o distrito: {barrio}")
        if desde <= c.fecha <= hasta:
            carreras.append(c)
    return carreras, descartes


def leer_vistos(ruta: Path = VISTOS) -> dict:
    return json.loads(ruta.read_text()) if ruta.exists() else {}
