"""Mide la cobertura de un fin de semana frente a running.life.

running.life es competencia: aquí SOLO se usa para contar qué carreras nos faltan.
Nada de lo que se lee de running.life se guarda en carreras.json.

Uso:
    .venv/bin/python cobertura.py 2026-11-21     # sábado del finde
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from nucleo import red
from nucleo.duplicados import misma_carrera
from nucleo.modelo import Carrera, Fuente
from nucleo.normalizar import clave, nombre as limpiar_nombre

URL = "https://running.life/calendario-carreras/espana/andalucia?page={}"
DATOS = Path(__file__).resolve().parent / "datos"


def leer_pagina(html: str) -> list[dict]:
    eventos = []
    for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            datos = json.loads(bloque)
        except json.JSONDecodeError:
            continue
        if datos.get("@type") != "ItemList":
            continue
        for elemento in datos.get("itemListElement", []):
            ev = elemento.get("item", {})
            lugar = ev.get("location", {})
            eventos.append({
                "nombre": ev.get("name", ""),
                "fecha": date.fromisoformat(ev["startDate"][:10]),
                "poblacion": lugar.get("address", {}).get("addressLocality") or lugar.get("name"),
            })
    return eventos


def eventos_finde(sabado: date, max_paginas: int = 15) -> list[dict]:
    return eventos_rango(sabado, sabado + timedelta(days=1), max_paginas)


def eventos_rango(desde: date, hasta: date, max_paginas: int = 15) -> list[dict]:
    sabado, domingo = desde, hasta
    encontrados = []
    for pagina in range(1, max_paginas + 1):
        try:
            eventos = leer_pagina(red.descargar(URL.format(pagina)).decode("utf-8", "replace"))
        except RuntimeError as error:  # pasada la última página, running.life da 404
            if "404" in str(error):
                break
            raise
        if not eventos:
            break
        for e in eventos:  # las páginas se solapan: no contar dos veces la misma
            if sabado <= e["fecha"] <= domingo and (e["nombre"], e["fecha"]) not in {(x["nombre"], x["fecha"]) for x in encontrados}:
                encontrados.append(e)
        if min(e["fecha"] for e in eventos) > domingo:
            break
    return encontrados


def medir(sabado: date, hasta: date | None = None) -> str:
    domingo = hasta or sabado + timedelta(days=1)
    nuestras_json = json.loads((DATOS / "carreras.json").read_text())["carreras"]
    nuestras = [c for c in nuestras_json if sabado.isoformat() <= c["fecha"] <= domingo.isoformat()]
    suyas = eventos_rango(sabado, domingo, 15 if hasta is None else 120)

    def como_carrera(d: dict, fuente: str) -> Carrera:
        return Carrera(nombre=limpiar_nombre(d["nombre"]), fecha=date.fromisoformat(str(d["fecha"])),
                       fuente=Fuente(fuente, ""), poblacion=d.get("poblacion"))

    ours = [(c, como_carrera(c, "nuestra")) for c in nuestras]
    coinciden, solo_suyas = [], []
    usadas = set()
    for s in suyas:
        cs = como_carrera(s, "running.life")
        hit = next((i for i, (_, o) in enumerate(ours) if i not in usadas and misma_carrera(o, cs)), None)
        if hit is None:
            # Respaldo: mismo día y mismo pueblo (los nombres a veces no se parecen nada).
            hit = next((i for i, (_, o) in enumerate(ours) if i not in usadas and o.fecha == cs.fecha
                        and o.poblacion and clave(o.poblacion) == clave(cs.poblacion)), None)
        if hit is None:
            solo_suyas.append(s)
        else:
            usadas.add(hit)
            coinciden.append((ours[hit][0], s))
    solo_nuestras = [c for i, (c, _) in enumerate(ours) if i not in usadas]
    union = len(coinciden) + len(solo_suyas) + len(solo_nuestras)
    cobertura = (len(coinciden) + len(solo_nuestras)) / union if union else 0

    meses = sorted({str(c["fecha"])[:7] for c, _ in coinciden} | {s["fecha"].isoformat()[:7] for s in solo_suyas}
                   | {c["fecha"][:7] for c in solo_nuestras})
    por_mes = []
    for m in meses:
        a = sum(1 for c, _ in coinciden if c["fecha"][:7] == m) + sum(1 for c in solo_nuestras if c["fecha"][:7] == m)
        f = sum(1 for x in solo_suyas if x["fecha"].isoformat()[:7] == m)
        por_mes.append(f"| {m} | {a} | {f} | {a / (a + f):.0%} |")
    largas = re.compile(r"marat|media|medio|\b21|ultra|42", re.I)
    lineas = [
        f"# Cobertura del {sabado:%d/%m/%Y} al {domingo:%d/%m/%Y}" if hasta else f"# Cobertura del finde {sabado:%d/%m} – {domingo:%d/%m/%Y}",
        "",
        f"- Nuestras: **{len(nuestras)}** · running.life: **{len(suyas)}** · en común: **{len(coinciden)}**",
        f"- Solo nuestras: **{len(solo_nuestras)}** · nos faltan: **{len(solo_suyas)}** · total entre las dos: **{union}**",
        f"- **Cobertura: {cobertura:.0%}** (objetivo: 80 % dos findes seguidos)",
        "",
        *(["## Por mes", "", "| Mes | Tenemos | Nos faltan | Cobertura |", "|---|---|---|---|", *por_mes, "",
            "## Medias, maratones y ultras que nos faltan",
            *[f"- {s['fecha']} · {s['nombre']} · {s['poblacion']}" for s in solo_suyas if largas.search(s["nombre"])], ""]
          if hasta else []),
        "## Nos faltan (pista de qué fuentes buscar)",
        *[f"- {s['fecha']:%a %d} · {s['nombre']} · {s['poblacion']}" for s in solo_suyas],
        "",
        "## Solo las tenemos nosotros",
        *[f"- {c['fecha']} · {c['nombre']} · {c.get('poblacion') or '¿?'} [{c['fuentes'][0]['id']}]" for c in solo_nuestras],
        "",
        "## En común",
        *[f"- {c['nombre']} = {s['nombre']}" for c, s in coinciden],
    ]
    texto = "\n".join(lineas) + "\n"
    nombre = f"cobertura-{sabado.isoformat()}" + (f"-a-{domingo.isoformat()}" if hasta else "")
    (DATOS / f"{nombre}.md").write_text(texto)
    return texto


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sabado", type=date.fromisoformat, help="sábado del finde, o inicio del periodo con --hasta")
    p.add_argument("--hasta", type=date.fromisoformat, help="mide todo el periodo, mes a mes")
    args = p.parse_args()
    if args.hasta is None and args.sabado.weekday() != 5:
        sys.exit("La fecha tiene que ser un sábado (o usa --hasta).")
    print(medir(args.sabado, args.hasta))
