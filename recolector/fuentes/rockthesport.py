"""RockTheSport (plataforma nacional). Su listado se carga por /api/, que robots.txt prohíbe, así que:
1. se lee el sitemap público de eventos (`/sitemap/events-es.xml`, ~3.300 fichas sin fecha ni región);
2. solo se abren las fichas cuyo nombre contiene un municipio andaluz (datos/municipios-andalucia.json)
   y que parecen carreras a pie;
3. de cada ficha se guarda solo el JSON-LD (jsonld.recortar). Las que no son andaluzas o ya pasaron se
   recuerdan en datos/rockthesport-vistos.json para no volver a abrirlas.
La provincia sale del municipio del nombre (las fichas no la dan) y se comprueba con las coordenadas.
4. Las fichas cuyo nombre no lleva municipio («xviii-calamorro-skyrace») también se abren, una sola vez cada una y
   como mucho NUEVAS_POR_PASADA por ejecución: si su JSON-LD da una provincia andaluza (región o código postal),
   entran; si no, se recuerdan como no andaluzas."""
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
NUEVAS_POR_PASADA = 300  # fichas sin municipio en el nombre que se abren por primera vez en cada ejecución
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
        lugar = municipio_del_slug(slug, indice)
        if not nz.clasificar(slug.replace("-", " "))[0]:
            continue  # marchas, bici, senderismo…: ni se abre
        recuerdo = vistos.get(slug)
        if recuerdo and (not recuerdo.get("andaluza") or recuerdo.get("fecha", "9999") < desde.isoformat()):
            continue
        if not lugar and not recuerdo:
            if nuevas >= nuevas_por_pasada:
                continue  # se abrirá en otra pasada
            nuevas += 1
        url = _FICHA + slug
        c, motivo = jsonld.leer_ficha(descargar_ficha(url), url, ID, provincia_si_falta=lugar[1] if lugar else None)
        if not c:
            vistos[slug] = {"andaluza": False, "motivo": motivo}
            descartes.append(motivo)
            continue
        andaluza = _en_andalucia(c.coords) if c.coords else True
        vistos[slug] = {"andaluza": andaluza, "fecha": c.fecha.isoformat()}
        if not andaluza:
            descartes.append(f"fuera de Andalucía (coordenadas): {c.nombre}")
            continue
        if lugar:
            c.poblacion = lugar[0]  # el nombre oficial del municipio (la ficha trae «Pl. de España, Fonelas»…)
            c.provincia = lugar[1]
        if desde <= c.fecha <= hasta:
            carreras.append(c)
    ruta_vistos.write_text(json.dumps(dict(sorted(vistos.items())), ensure_ascii=False, indent=1))
    return carreras, descartes
