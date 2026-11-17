"""Ronda 4, Cantabria: el lector `fcatle` (Federación Cántabra de Atletismo, iCal) con una muestra recortada
de su calendario de 2026 (`muestras/fcatle_ronda4.ics`, solo DTSTART, SUMMARY, LOCATION y URL).

Los tests marcados `xfail` describen el cambio propuesto en el informe de la ronda 4 (no aplicado aquí porque
`fuentes/fcatle.py` es compartido): quitar reuniones de pista en estadio, aceptar la Subida a La Hermida
(sale en Asturias y llega a Potes) y sacar el pueblo del nombre cuando el evento no trae LOCATION."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from fuentes import fcatle

MUESTRAS = Path(__file__).parent / "muestras"


def _leer():
    carreras, descartes = fcatle.leer((MUESTRAS / "fcatle_ronda4.ics").read_bytes())
    return {c.nombre: c for c in carreras}, descartes


def test_carreras_populares_de_invierno():
    carreras, _ = _leer()
    piélagos = carreras["XXXI Carrera de Navidad de Piélagos"]
    assert piélagos.fecha == date(2026, 12, 20)
    assert piélagos.poblacion == "Renedo de Piélagos"
    assert piélagos.provincia == "Cantabria"
    assert piélagos.fuente.url.startswith("https://www.fcatle.com/evento/")
    polanco = next(c for n, c in carreras.items() if n.startswith("VIII Carrera Popular de Nochebuena"))
    assert polanco.fecha == date(2026, 12, 24) and polanco.poblacion == "Polanco"


def test_cross_en_estadio_se_queda():
    carreras, _ = _leer()
    cross = next(c for n, c in carreras.items() if n.startswith("LI Cross Costa Esmeralda"))
    assert cross.poblacion == "Laredo" and cross.modalidad == "cross"


def test_ruta_en_complejo_deportivo_se_queda():
    carreras, _ = _leer()
    assert any(n.startswith("XLVI 100 y 50 Kilómetros") for n in carreras)


def test_pista_en_estadio_fuera():
    carreras, _ = _leer()
    assert "Campeonato de Cantabria Sub18" not in carreras
    assert not any(n.startswith("XLIV Trofeo Olimpia") for n in carreras)


def test_subida_a_la_hermida_llega_a_potes():
    carreras, _ = _leer()
    hermida = carreras["XXXIX Subida Pedestre al Desfiladero de La Hermida"]
    assert hermida.poblacion == "Potes" and hermida.provincia == "Cantabria"


def test_san_silvestre_sin_lugar_saca_el_pueblo_del_nombre():
    carreras, _ = _leer()
    assert carreras["IX San Silvestre Solidaria de El Astillero"].poblacion == "El Astillero"
