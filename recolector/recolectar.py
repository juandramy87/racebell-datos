"""Recolector de Racebell: lee las fuentes, une duplicados y escribe datos/carreras.json.

Uso:
    .venv/bin/python recolectar.py              # próximos 60 días
    .venv/bin/python recolectar.py --dias 90
    .venv/bin/python recolectar.py --sin-cache  # vuelve a descargar aunque haya copia de hoy
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fuentes import (anunciadas, rockthesport, alcanzatumeta, cruzandolameta, montur, corredorespopulares, cronius, cronofinisher, deportime, dorsalchip, faa,
                     gesconchip, globaltempo, inscrik, jsonld, olarivers, ruta091, runnink, sesca, sportmaniacs,
                     tecnocrono, time2run, todofondo, tucarrera)
from nucleo import municipios, red
from nucleo.duplicados import deduplicar
from nucleo.modelo import Carrera

MADRID = ZoneInfo("Europe/Madrid")
DATOS = Path(__file__).resolve().parent / "datos"


def recolectar(dias: int, usar_cache: bool) -> dict:
    ahora = datetime.now(MADRID).replace(tzinfo=None)
    desde, hasta = ahora.date(), (ahora + timedelta(days=dias)).date()
    bajar = lambda url: red.descargar(url, usar_cache=usar_cache)  # noqa: E731
    # Fichas con JSON-LD: se guarda solo el JSON-LD (nada de inscritos ni del resto de la página).
    bajar_ficha_jsonld = lambda url: red.descargar(url, usar_cache=usar_cache, recortar=jsonld.recortar)  # noqa: E731
    ruta_recuerdo = DATOS / "sportmaniacs-provincias.json"
    recuerdo_sm = json.loads(ruta_recuerdo.read_text()) if ruta_recuerdo.exists() else {}

    todas: list[Carrera] = []
    informe = {"fuentes": {}, "descartes": {}, "avisos": []}
    lectores = [
        (dorsalchip.ID, lambda: dorsalchip.leer(bajar(dorsalchip.URL))),
        (tecnocrono.ID, lambda: tecnocrono.leer(bajar(tecnocrono.URL))),
        (sesca.ID, lambda: sesca.leer(bajar(sesca.URL))),
        (globaltempo.ID, lambda: globaltempo.leer(bajar(globaltempo.URL), descargar_ficha=lambda u: red.descargar(
                                                      u, usar_cache=usar_cache, recortar=globaltempo.recortar_ficha),
                                                  desde=desde, hasta=hasta)),
        (faa.ID, lambda: faa.leer(bajar(faa.URL))),
        (gesconchip.ID, lambda: gesconchip.leer(bajar(gesconchip.URL))),
        (corredorespopulares.ID, lambda: corredorespopulares.leer(bajar(corredorespopulares.URL))),
        (cronius.ID, lambda: cronius.leer(bajar(cronius.URL), descargar_ficha=bajar)),
        (inscrik.ID, lambda: inscrik.leer(bajar(inscrik.URL), descargar_ficha=bajar)),
        (deportime.ID, lambda: deportime.leer(bajar(deportime.URL), descargar_ficha=bajar)),
        (todofondo.ID, lambda: todofondo.leer(bajar(todofondo.URL))),
        (runnink.ID, lambda: runnink.leer(bajar(runnink.URL))),
        (alcanzatumeta.ID, lambda: alcanzatumeta.leer(bajar(alcanzatumeta.URL))),
        (rockthesport.ID, lambda: rockthesport.leer(bajar(rockthesport.URL), desde=desde, hasta=hasta,
                                                  descargar_ficha=lambda u: red.descargar(u, usar_cache=usar_cache, recortar=jsonld.recortar))),
        (olarivers.ID, lambda: olarivers.leer(bajar(olarivers.URL))),
        (montur.ID, lambda: montur.leer(bajar(montur.URL))),
        (cruzandolameta.ID, lambda: cruzandolameta.leer(bajar(cruzandolameta.URL))),
        (tucarrera.ID, lambda: tucarrera.leer(bajar(tucarrera.URL))),
        (ruta091.ID, lambda: ruta091.leer(bajar(ruta091.URL))),
        (cronofinisher.ID, lambda: _cronofinisher(bajar)),
        (time2run.ID, lambda: time2run.leer(bajar(time2run.URL), descargar_ficha=bajar,
                                            descargar_rockthesport=bajar_ficha_jsonld)),
        (sportmaniacs.ID, lambda: sportmaniacs.leer(sportmaniacs.bajar_paginas(bajar, hasta),
                                                    descargar_ficha=bajar_ficha_jsonld, desde=desde, hasta=hasta,
                                                    recuerdo=recuerdo_sm)),
        # Siempre la última: solo rellena lo que ninguna plataforma tiene todavía.
        (anunciadas.ID, lambda: anunciadas.leer(json.loads((Path(__file__).resolve().parent / "anunciadas.json").read_text()),
                                                hoy=desde)),
    ]
    for ident, leer in lectores:
        try:
            carreras, descartes = leer()
        except Exception as error:  # una fuente rota no tumba las demás
            informe["avisos"].append(f"{ident}: ERROR {error}")
            print(f"  {ident}: ERROR {error}", file=sys.stderr)
            continue
        en_plazo = [c for c in carreras if desde <= c.fecha <= hasta]
        informe["fuentes"][ident] = {"leidas": len(carreras), "en_plazo": len(en_plazo)}
        informe["descartes"][ident] = descartes
        if not carreras:
            informe["avisos"].append(f"{ident}: 0 carreras. ¿Ha cambiado la web?")
        print(f"  {ident}: {len(carreras)} leídas, {len(en_plazo)} entre {desde} y {hasta}")
        todas.extend(en_plazo)

    DATOS.mkdir(exist_ok=True)
    ruta_recuerdo.write_text(json.dumps(dict(sorted(recuerdo_sm.items())), ensure_ascii=False, indent=1))

    todas = aplicar_correcciones(todas, informe)
    informe["carteles_aplicados"] = aplicar_carteles(todas)
    informe["municipios_completados"] = municipios.completar(todas, bajar)
    for c in todas:
        revisar(c)
    unicas, uniones = deduplicar(todas)
    informe["uniones"] = uniones
    salida = {
        "version": 1,
        "generado": ahora.isoformat(timespec="minutes"),
        "zona": "Europe/Madrid",
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "carreras": [_con_id(c.a_dict(ahora)) for c in unicas],
    }
    DATOS.mkdir(exist_ok=True)
    (DATOS / "carreras.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    (DATOS / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1))
    print(f"  {len(todas)} carreras → {len(unicas)} tras unir {len(uniones)} duplicados")
    return salida


def _cronofinisher(bajar) -> tuple[list[Carrera], list[str]]:
    primera = bajar(cronofinisher.URL)
    return cronofinisher.leer([primera] + [bajar(u) for u in cronofinisher.otras_paginas(primera)])


def aplicar_correcciones(carreras: list[Carrera], informe: dict) -> list[Carrera]:
    """Quita las carreras canceladas que las fuentes aún muestran (ver correcciones.json)."""
    correcciones = json.loads((Path(__file__).resolve().parent / "correcciones.json").read_text())
    canceladas = correcciones.get("canceladas", {})
    quedan = []
    for c in carreras:
        if c.fuente.url in canceladas:
            informe["descartes"].setdefault("correcciones", []).append(f"{c.nombre}: {canceladas[c.fuente.url]}")
        else:
            quedan.append(c)
    return quedan


def aplicar_carteles(carreras: list[Carrera]) -> int:
    """Completa las carreras con lo leído en su cartel (carteles.json, clave = URL del cartel)."""
    from datetime import datetime as _dt
    carteles = json.loads((Path(__file__).resolve().parent / "carteles.json").read_text())
    aplicados = 0
    for c in carreras:
        dato = carteles.get(c.cartel or "")
        if not dato:
            continue
        for campo in ("nombre", "poblacion", "provincia", "hora", "modalidad", "url_inscripcion", "estado_fuente"):
            if dato.get(campo):
                setattr(c, campo, dato[campo])
        if dato.get("distancias_km"):
            c.distancias_km = [float(x) for x in dato["distancias_km"]]
        if dato.get("precios"):
            c.precios = dato["precios"]
        if dato.get("inscripcion_hasta"):
            c.inscripcion_hasta = _dt.fromisoformat(dato["inscripcion_hasta"])
        c.previos = list(dict.fromkeys(c.previos + dato.get("previos", [])))
        c.quitar_avisos("solo en el cartel")
        if dato.get("dudoso"):
            c.marcar(dato["dudoso"])
        if not c.inscripcion_hasta and c.estado_fuente != "no_abierta":
            c.marcar("Cierre de inscripción no indicado en el cartel", "pendiente_cartel")
        aplicados += 1
    return aplicados


def revisar(c: Carrera) -> None:
    """Comprobaciones de sentido común: lo raro se marca como dudoso para revisarlo."""
    if c.inscripcion_hasta and c.inscripcion_hasta.date() > c.fecha:
        c.marcar("El cierre de inscripción es posterior a la carrera")
    if c.inscripcion_hasta and (c.fecha - c.inscripcion_hasta.date()).days > 120:
        c.marcar("El cierre de inscripción es más de 4 meses antes de la carrera: ¿fecha equivocada?")
    if c.inscripcion_desde and c.inscripcion_hasta and c.inscripcion_desde > c.inscripcion_hasta:
        c.marcar("La inscripción abre después de cerrar")


def _con_id(d: dict) -> dict:
    from nucleo.normalizar import clave
    base = "-".join(x for x in (d["fecha"], clave(d.get("poblacion")), clave(d["nombre"])) if x)
    d["id"] = base.replace(" ", "-")[:90]
    return {"id": d.pop("id"), **d}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dias", type=int, default=60)
    p.add_argument("--sin-cache", action="store_true")
    args = p.parse_args()
    recolectar(args.dias, usar_cache=not args.sin_cache)
