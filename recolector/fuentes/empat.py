"""Empa-T (Asturias): cronometrador de trails y carreras populares de Asturias (Salas, Aller, Candamo,
Villaviciosa, Colunga, Oviedo, Cudillero…). Inscribe en AvaiBook Sports y su listado de próximas pruebas está en
`avaibooksports.com/listado-empat.php`: fecha y hora, municipio, provincia, coordenadas y plazo de inscripción
exacto. Ver `fuentes/avaibooklistado.py`. Las pruebas con la inscripción ya cerrada dejan de salir."""
from __future__ import annotations

from fuentes import avaibooklistado
from nucleo.modelo import Carrera

ID = "empat"
URL = "https://www.avaibooksports.com/listado-empat.php"


def leer(contenido: bytes | str) -> tuple[list[Carrera], list[str]]:
    return avaibooklistado.leer(contenido, ID, URL)
