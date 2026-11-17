"""Conchip Canarias (Tenerife): cronometrador del norte y el área metropolitana de Tenerife (La Laguna,
El Rosario, Los Realejos, Fasnia, Arico…). Inscribe en AvaiBook Sports (`inscripciones.conchipcanarias.com`) y
su listado de próximas pruebas está en `avaibooksports.com/listado-conchipcanarias.php`: fecha y hora, municipio,
provincia, coordenadas y plazo de inscripción exacto. Ver `fuentes/avaibooklistado.py`. Las pruebas con la
inscripción ya cerrada dejan de salir en el listado."""
from __future__ import annotations

from fuentes import avaibooklistado
from nucleo.modelo import Carrera

ID = "conchip"
URL = "https://www.avaibooksports.com/listado-conchipcanarias.php"


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    return avaibooklistado.leer(contenido, ID, URL)
