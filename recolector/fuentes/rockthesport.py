"""RockTheSport (plataforma nacional). Su listado se carga por /api/, que robots.txt prohíbe, así que:
1. se lee el sitemap público de eventos (`/sitemap/events-es.xml`, ~3.300 fichas sin fecha ni región);
2. se abren las fichas que parecen carreras a pie (las marchas, bici o senderismo ni se abren), como mucho
   NUEVAS_POR_PASADA fichas nunca vistas por ejecución;
3. de cada ficha se guarda solo el JSON-LD (jsonld.recortar). La provincia sale de su región o código postal; si no
   los trae, del municipio andaluz del nombre (datos/municipios-andalucia.json), comprobado con las coordenadas.
   Lo que no es de España o ya pasó se recuerda en datos/rockthesport-vistos.json para no volver a abrirlo."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from fuentes import jsonld
from nucleo import normalizar as nz
from nucleo.modelo import Carrera

ID = "rockthesport"
URL = "https://web.rockthesport.com/sitemap/events-es.xml"
_FICHA = "https://web.rockthesport.com/es/event/"
NUEVAS_POR_PASADA = 500  # fichas nunca vistas que se abren por ejecución; las demás quedan para los días siguientes
DATOS = Path(__file__).resolve().parents[1] / "datos"


def _indice_municipios() -> dict[str, tuple[str, str]]:
    """clave del municipio → (nombre, provincia)."""
    tabla = json.loads((DATOS / "municipios-andalucia.json").read_text())
    indice = {}
    for provincia, nombres in tabla.items():
        for n in nombres:
            k = nz.clave(n)
            if len(k) >= 5:
                indice[k] = (n, provincia)
    return indice


def municipio_del_slug(slug: str, indice: dict) -> Optional[tuple[str, str]]:
    trozos = slug.strip("-").split("-")
    mejor = None
    for i in range(len(trozos)):
        for j in range(i + 1, min(len(trozos), i + 5) + 1):
            k = " ".join(trozos[i:j])
            if k in indice and (mejor is None or len(k) > len(nz.clave(mejor[0]))):
                mejor = indice[k]
    return mejor


def _en_andalucia(coords) -> bool:
    return bool(coords) and 35.9 <= coords[0] <= 38.8 and -7.6 <= coords[1] <= -1.6


def leer(sitemap: bytes | str, *, descargar_ficha: Callable[[str], bytes], desde: date, hasta: date,
         ruta_vistos: Path | None = None, nuevas_por_pasada: int = NUEVAS_POR_PASADA) -> tuple[list[Carrera], list[str]]:
    texto = sitemap.decode("utf-8", "replace") if isinstance(sitemap, bytes) else sitemap
    slugs = re.findall(r"<loc>https://web\.rockthesport\.com/es/event/([^<]+)</loc>", texto)
    ruta_vistos = ruta_vistos or DATOS / "rockthesport-vistos.json"
    vistos: dict = json.loads(ruta_vistos.read_text()) if ruta_vistos.exists() else {}
    indice = _indice_municipios()
    carreras, descartes = [], []
    nuevas = 0
    for slug in slugs:
        if not nz.clasificar(slug.replace("-", " "))[0]:
            continue  # marchas, bici, senderismo…: ni se abre
        recuerdo = vistos.get(slug)
        # «espana» = False: no es de España (o no se pudo ubicar). Las fichas recordadas con el formato antiguo
        # («andaluza»: False, de cuando solo se buscaba Andalucía) se vuelven a abrir una vez.
        if recuerdo and ("espana" in recuerdo or recuerdo.get("andaluza")):
            if recuerdo.get("espana") is False or recuerdo.get("fecha", "9999") < desde.isoformat():
                continue
        else:
            if nuevas >= nuevas_por_pasada:
                continue  # se abrirá en otra pasada
            nuevas += 1
        lugar = municipio_del_slug(slug, indice)
        url = _FICHA + slug
        ficha = descargar_ficha(url)
        c, motivo = jsonld.leer_ficha(ficha, url, ID)
        adivinada = False
        if not c and lugar:
            c, motivo = jsonld.leer_ficha(ficha, url, ID, provincia_si_falta=lugar[1])
            adivinada = c is not None
        if not c or (adivinada and c.coords and not _en_andalucia(c.coords)):
            vistos[slug] = {"espana": False, "motivo": motivo or "coordenadas fuera del municipio del nombre"}
            descartes.append(motivo or f"sin provincia: {slug}")
            continue
        vistos[slug] = {"espana": True, "provincia": c.provincia, "fecha": c.fecha.isoformat()}
        if adivinada:
            c.poblacion = lugar[0]  # el nombre oficial del municipio (la ficha trae «Pl. de España, Fonelas»…)
        if desde <= c.fecha <= hasta:
            carreras.append(c)
    ruta_vistos.write_text(json.dumps(dict(sorted(vistos.items())), ensure_ascii=False, indent=1))
    return carreras, descartes
