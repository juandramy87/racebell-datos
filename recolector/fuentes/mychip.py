"""Mychip (cronometrador de la Safor, la Ribera, la Marina y l'Alcoià): lleva la Lliga de Muntanya València Sud, el
Circuit Trail Marina, la Lliga de Carreras por Montaña y la Copa de Marcha Nórdica de la FEMECV, y medias de pueblo.
Su web (`www.mychip.es`, una app Vue) pide la lista a su API, `…/prod/events` (POST con los estados de inscripción
que pinta la portada: sin abrir, abierta, completa o cerrada). Sin robots.txt. Leída con permiso del usuario
(17/11/2026), igual que Cronorunner.

La API devuelve, además de lo público, campos internos (claves de inscripción en directo, hashes de importación…).
`recortar` se queda SOLO con lo público ANTES de guardar nada en la caché: nombre, fechas, plazo, estado, localidad,
coordenadas, slug y, de cada modalidad, nombre, distancia, precio y deporte. Nunca inscritos ni clasificaciones.
La inscripción está en `inscripciones.mychip.es/es/evento/<slug>` (marca blanca de RockTheSport): si la misma carrera
sale en RockTheSport, se une con ella."""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, datetime
from typing import Optional

from nucleo import normalizar as nz
from nucleo.modelo import ABIERTA, CERRADA, NO_ABIERTA, Carrera, Fuente
from nucleo.red import USER_AGENT

ID = "mychip"
API = "https://sfztfth1r1.execute-api.eu-central-1.amazonaws.com/prod/events"
CONSULTA = {"limit": 999, "status": ["registrations_not_opened", "registrations_opened", "registrations_full",
                                     "registrations_closed"]}
_INSCRIPCION = "https://inscripciones.mychip.es/es/evento/"
_ESTADOS = {"registrations_not_opened": NO_ABIERTA, "registrations_opened": ABIERTA, "registrations_full": CERRADA,
            "registrations_closed": CERRADA}
# Marcha nórdica y senderista: no se corren. «Marcha» a secas sí puede ser una carrera popular (lo decide clasificar).
_NO_CORRER = re.compile(r"\b(marxa|marcha) (nordica|senderista)\b|\bnordic walking\b|\bsenderisme\b")
_DEPORTES_A_PIE = {"running", "trail_running", "trail", "walking", None, ""}


def descargar() -> bytes:
    peticion = urllib.request.Request(API, data=json.dumps(CONSULTA).encode(), method="POST", headers={
        "User-Agent": USER_AGENT, "Content-Type": "application/json", "Origin": "https://www.mychip.es"})
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        return recortar(respuesta.read())


def _fecha(valor) -> Optional[datetime]:
    texto = valor.get("$date") if isinstance(valor, dict) else valor
    if not texto:
        return None
    return datetime.fromisoformat(texto.replace("Z", "+00:00")).replace(tzinfo=None)


def recortar(contenido: bytes | str) -> bytes:
    """Solo los campos públicos de cada evento visible (lista de dicts planos)."""
    eventos = []
    for e in json.loads(contenido):
        if not e.get("visible", True):
            continue
        loc = e.get("location") or {}
        coords = ((loc.get("coordinates") or {}).get("coordinates") or None)
        eventos.append({
            "nombre": e.get("name") or "",
            "slug": e.get("slug") or "",
            "estado": e.get("status"),
            "inicio": (_fecha(e.get("date_start")) or datetime.min).isoformat() if e.get("date_start") else None,
            "fin": _fecha(e.get("date_end")).isoformat() if e.get("date_end") else None,
            "inscripcion_desde": _fecha(e.get("registration_start")).isoformat() if e.get("registration_start") else None,
            "inscripcion_hasta": _fecha(e.get("registration_end")).isoformat() if e.get("registration_end") else None,
            "ciudad": loc.get("city"),
            "provincia": loc.get("county"),
            "pais": loc.get("country_iso"),
            "coords": coords,
            "cartel": e.get("poster"),
            "modalidades": [{"nombre": m.get("name"), "metros": m.get("distance"), "euros": m.get("price"),
                             "deporte": m.get("sport")}
                            for m in e.get("modalities") or [] if m.get("visible", True)],
        })
    return json.dumps(eventos, ensure_ascii=False).encode()


def _poblacion(ciudad: str) -> tuple[Optional[str], Optional[str]]:
    """«Monòver / Monóvar», «Alcoy/alcoi»: se prueba cada forma contra la tabla del INE."""
    for forma in [ciudad, *re.split(r"\s*/\s*", ciudad)]:
        if forma and (hallado := nz.municipio_espana(forma)):
            return hallado
    return None, None


def leer(contenido: bytes | str, desde: date, hasta: date) -> tuple[list[Carrera], list[str]]:
    carreras, descartes = [], []
    for e in json.loads(contenido):
        nombre = nz.nombre(e["nombre"])
        if not e.get("inicio"):
            descartes.append(f"sin fecha: {nombre}")
            continue
        inicio = datetime.fromisoformat(e["inicio"])
        if not desde <= inicio.date() <= hasta:
            continue
        if e.get("pais") and e["pais"] != "ES":
            descartes.append(f"fuera de España: {nombre}")
            continue
        mods = e.get("modalidades") or []
        textos = [nombre, *(m.get("nombre") for m in mods)]
        if _NO_CORRER.search(nz.clave(nombre)):
            descartes.append(f"no se corre (marcha): {nombre}")
            continue
        if mods and not any(m.get("deporte") in _DEPORTES_A_PIE for m in mods):
            descartes.append(f"no es a pie ({', '.join(sorted({str(m.get('deporte')) for m in mods}))}): {nombre}")
            continue
        a_pie, modalidad = nz.clasificar(*textos)
        if not a_pie and not any(m.get("deporte") in {"running", "trail_running", "trail"} for m in mods):
            descartes.append(f"no es a pie: {nombre}")
            continue
        if not modalidad and mods and all(m.get("deporte") == "trail_running" for m in mods):
            modalidad = "trail"
        poblacion, provincia = _poblacion(e.get("ciudad") or "")
        if not poblacion or nz.clave(poblacion) == "valencia":  # «València» suele ser la provincia, no el pueblo
            for trozo in re.split(r"[,.\-–‐]", nombre)[1:]:
                if (hallado := nz.municipio_espana(trozo.strip())) and nz.clave(hallado[0]) != "valencia":
                    poblacion, provincia = hallado
                    break
        if not provincia:
            provincia = nz.provincia(e.get("provincia") or "")
            poblacion = nz.poblacion(e["ciudad"]) if e.get("ciudad") and nz.clave(e["ciudad"]) != "valencia" else None
        if not provincia:
            descartes.append(f"sin provincia: {nombre} ({e.get('ciudad')})")
            continue
        coords = e.get("coords")
        # La API da [latitud, longitud] (39.19, -0.42 en Algemesí); se comprueba que cae en España.
        if coords and len(coords) == 2 and 27 <= coords[0] <= 44 and -19 <= coords[1] <= 5:
            coords = (float(coords[0]), float(coords[1]))
        else:
            coords = None
        distancias = sorted({round(m["metros"] / 1000, 3) for m in mods if m.get("metros")}) or \
            nz.distancias_del_nombre(nombre)
        url = _INSCRIPCION + e["slug"]
        c = Carrera(
            nombre=nombre, fecha=inicio.date(), fuente=Fuente(ID, url),
            poblacion=poblacion, provincia=provincia, coords=coords, modalidad=modalidad,
            distancias_km=distancias,
            inscripcion_desde=datetime.fromisoformat(e["inscripcion_desde"]) if e.get("inscripcion_desde") else None,
            inscripcion_hasta=datetime.fromisoformat(e["inscripcion_hasta"]) if e.get("inscripcion_hasta") else None,
            estado_fuente=_ESTADOS.get(e.get("estado") or ""),
            url_inscripcion=url, cartel=e.get("cartel"),
            precios=[{"nombre": m["nombre"], "euros": float(m["euros"])} for m in mods
                     if m.get("nombre") and isinstance(m.get("euros"), (int, float)) and m["euros"] > 0],
        )
        if e.get("estado") == "registrations_full":
            c.previos.append("Inscripciones agotadas")
        if not poblacion:
            c.marcar("Población no indicada en Mychip", "pendiente_cartel")
        c.marcar("Hora en el reglamento de Mychip (la API la da en UTC)", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
