"""Runvasport (Valladolid, Palencia, Zamora): cronometrador de carreras populares de Castilla y León.
Inscribe en AvaiBook Sports y su listado de próximas pruebas está en
`avaibooksports.com/listado-runvasport.php`: fecha y hora, municipio, provincia, coordenadas y plazo de inscripción
exacto. Ver `fuentes/avaibooklistado.py`. Las pruebas con la inscripción ya cerrada dejan de salir."""
from __future__ import annotations

from fuentes import avaibooklistado
from nucleo.modelo import Carrera

ID = "runvasport"
URL = "https://www.avaibooksports.com/listado-runvasport.php"


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    return avaibooklistado.leer(contenido, ID, URL)
