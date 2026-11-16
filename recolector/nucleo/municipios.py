"""Provincia y coordenadas aproximadas (centro del pueblo) a partir del nombre del pueblo.

Se guardan en datos/municipios.json y solo se pregunta a Nominatim (OpenStreetMap) por los pueblos
nuevos: una petición cada 1,5 s, con User-Agent propio (política de uso de Nominatim)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlencode

from nucleo import normalizar as nz

RUTA = Path(__file__).resolve().parents[1] / "datos" / "municipios.json"
URL = "https://nominatim.openstreetmap.org/search?"


def _cargar() -> dict:
    return json.loads(RUTA.read_text()) if RUTA.exists() else {}


def _guardar(tabla: dict) -> None:
    RUTA.write_text(json.dumps(dict(sorted(tabla.items())), ensure_ascii=False, indent=1))


def buscar(poblacion: str, provincia: Optional[str], descargar: Callable[[str], bytes], tabla: dict) -> Optional[dict]:
    """{"provincia": …, "lat": …, "lon": …} o None si no se encuentra en Andalucía."""
    clave = nz.clave(poblacion) + "|" + nz.clave(provincia or "")
    if clave in tabla:
        return tabla[clave]
    consulta = f"{poblacion}, {provincia + ', ' if provincia else ''}Andalucía, España"
    url = URL + urlencode({"q": consulta, "format": "jsonv2", "addressdetails": 1, "limit": 3, "countrycodes": "es"})
    try:
        resultados = json.loads(descargar(url))
    except Exception:
        return None  # sin red o sin respuesta: se vuelve a intentar otro día
    hallado = None
    for r in resultados:
        direccion = r.get("address", {})
        prov = nz.provincia(direccion.get("province") or direccion.get("county") or "")
        if direccion.get("state") != "Andalucía" or not prov or (provincia and prov != provincia):
            continue
        hallado = {"provincia": prov, "lat": round(float(r["lat"]), 4), "lon": round(float(r["lon"]), 4)}
        break
    tabla[clave] = hallado
    return hallado


def completar(carreras: list, descargar: Callable[[str], bytes]) -> int:
    """Rellena provincia y coords que falten. Devuelve cuántas carreras se han completado."""
    tabla = _cargar()
    completadas = 0
    for c in carreras:
        if not c.poblacion or (c.provincia and c.coords):
            continue
        dato = buscar(c.poblacion, c.provincia, descargar, tabla)
        if not dato:
            continue
        if not c.provincia:
            c.provincia = dato["provincia"]
            c.quitar_avisos("provincia")
        if not c.coords:
            c.coords = (dato["lat"], dato["lon"])
        completadas += 1
    _guardar(tabla)
    return completadas
