"""Cronofinisher (Extremadura, y algunas en Cádiz, Jaén y Huelva). Calendario HTML con fecha,
«LOCALIDAD (PROVINCIA)», tipo de prueba (icono), estado y «Hasta: dd-mm-aaaa» (fin de inscripción).
Son dos o tres páginas enlazadas como `/calendario//pg=N/` (GET). Solo se guardan las andaluzas."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, NO_ABIERTA, Carrera, Fuente

ID = "cronofinisher"
URL = "https://www.cronofinisher.com/calendario/"
MAX_PAGINAS = 5
_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
          "sep": 9, "oct": 10, "nov": 11, "dic": 12}
_ESTADOS = {"abiertas": ABIERTA, "cerradas": CERRADA, "agotadas": CERRADA, "proximamente": NO_ABIERTA}
_NO_ES_TIPO = ("logo", "kit digital", "abiertas", "cerradas", "agotadas", "proximamente")


def otras_paginas(contenido: bytes | str) -> list[str]:
    html = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    numeros = sorted({int(n) for n in re.findall(r'href="/calendario//pg=(\d+)/"', html)} - {1})
    return [f"https://www.cronofinisher.com/calendario//pg={n}/" for n in numeros[:MAX_PAGINAS - 1]]


def leer(paginas: list[bytes | str]) -> tuple[list[Carrera], list[str]]:
    carreras, descartes, vistas = [], [], set()
    for pagina in paginas:
        sopa = BeautifulSoup(pagina, "html.parser")
        for bloque in sopa.select("div.container_padre_actividad"):
            titulo = bloque.select_one(".titulo_evento_ficha")
            lugar = bloque.select_one(".localidad_evento_ficha")
            dia, mes, anyo = (bloque.select_one(f".{k}_evento") for k in ("dia", "mes", "ano"))
            if not (titulo and lugar and dia and mes and anyo):
                continue
            url = titulo.find_parent("a")["href"]
            if url in vistas:
                continue
            vistas.add(url)
            m = re.match(r"\s*(.*?)\s*\(([^)]+)\)", lugar.get_text(" ", strip=True))
            poblacion, provincia = (m.group(1), nz.provincia(m.group(2))) if m else (None, None)
            if provincia and nz.clave(poblacion) == nz.clave(provincia):
                poblacion = provincia  # «CADIZ (CÁDIZ)» → Cádiz, con su tilde
            if not provincia:
                continue  # Extremadura y resto: fuera de nuestra zona (sin anotarlo, son la mayoría)
            nombre = nz.nombre(titulo.get_text(" ", strip=True))
            iconos = [i.get("alt", "") for i in bloque.select("img[alt]")]
            tipo = next((a for a in iconos if not nz.clave(a).startswith(_NO_ES_TIPO)), "")
            a_pie, modalidad = nz.clasificar(nombre, tipo)
            if not a_pie or "hibrida" in nz.clave(tipo):
                descartes.append(f"no es a pie: {nombre} ({tipo})")
                continue
            mes_n = _MESES.get(nz.clave(mes.get_text())[:3])
            if not mes_n:
                descartes.append(f"fecha ilegible: {nombre}")
                continue
            estado = next((_ESTADOS[nz.clave(a)] for a in iconos if nz.clave(a) in _ESTADOS), None)
            c = Carrera(nombre=nombre, fecha=date(int(anyo.get_text()), mes_n, int(dia.get_text())),
                        fuente=Fuente(ID, url), poblacion=nz.poblacion(poblacion), provincia=provincia,
                        modalidad=modalidad, distancias_km=nz.distancias_del_nombre(nombre), url_inscripcion=url,
                        estado_fuente=estado)
            hasta = re.search(r"Hasta:\s*(\d{2})-(\d{2})-(\d{4})", bloque.get_text(" ", strip=True))
            if hasta:
                d, mm, a = map(int, hasta.groups())
                c.inscripcion_hasta = datetime(a, mm, d, 23, 59)
                c.marcar("Cierre de inscripción sin hora en la fuente (se supone 23:59)", "pendiente_cartel")
            else:
                c.marcar("Cierre de inscripción no indicado en el calendario", "pendiente_cartel")
            fondo = bloque.select_one(".container_actividad[style]")
            if fondo and (img := re.search(r"url\('([^']+)'\)", fondo["style"])) and "no_cartel" not in img.group(1):
                c.cartel = urljoin("https://www.cronofinisher.com/", img.group(1))
            carreras.append(c)
    return carreras, descartes
