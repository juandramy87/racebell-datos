"""Carreras grandes con fecha ya anunciada (medias, maratones, ultras) que aún no están en ninguna
plataforma de inscripción: las plataformas solo las publican al abrir la inscripción, 1–3 meses antes.

Los datos los lee Claude en la web OFICIAL de cada carrera y los apunta en `anunciadas.json`
(con la URL y la fecha de comprobación). Cuando una plataforma la publica, se une con ella y manda
la plataforma (ver `nucleo/duplicados.py`)."""
from __future__ import annotations

from datetime import date, datetime

from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, NO_ABIERTA, Carrera, Fuente

ID = "anunciadas"
ESTADOS = {"abierta": ABIERTA, "cerrada": CERRADA, "no_abierta": NO_ABIERTA}


def leer(datos: dict, hoy: date) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = [], []
    for ev in datos.get("carreras", []):
        nombre = nz.nombre(ev.get("nombre") or "")
        try:
            fecha = date.fromisoformat(ev["fecha"])
        except (KeyError, TypeError, ValueError):
            descartes.append(f"sin fecha: {nombre}")
            continue
        if fecha < hoy:
            descartes.append(f"ya pasada (actualizar anunciadas.json): {nombre} {fecha}")
            continue
        provincia = nz.provincia(ev.get("provincia"))
        if not provincia:
            descartes.append(f"fuera de España o sin provincia: {nombre}")
            continue
        url = ev.get("url_oficial") or ev.get("url_inscripcion")
        if not url:
            descartes.append(f"sin web oficial: {nombre}")
            continue
        c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, url), hora=ev.get("hora") or None,
                    poblacion=ev.get("poblacion") or None, provincia=provincia, modalidad=ev.get("modalidad") or None,
                    distancias_km=[float(x) for x in ev.get("distancias_km") or []] or nz.distancias_del_nombre(nombre),
                    url_inscripcion=ev.get("url_inscripcion") or None,
                    estado_fuente=ESTADOS.get((ev.get("estado_inscripcion") or "").strip().lower()))
        if ev.get("abre"):
            try:
                c.inscripcion_desde = datetime.fromisoformat(ev["abre"])
            except ValueError:
                pass
        comprobado = ev.get("comprobado")
        c.previos.append(f"Fecha anunciada en la web oficial{f' (comprobada el {comprobado})' if comprobado else ''}")
        if ev.get("fecha_provisional"):
            c.marcar("Fecha provisional: aún sin confirmar en la web oficial")
        carreras.append(c)
    return carreras, descartes
