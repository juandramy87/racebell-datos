from datetime import date, datetime

from fuentes import faa
from recolectar import aplicar_carteles
from tests.test_lectores import buscar, muestra


def test_carteles_completan_las_carreras_de_la_faa():
    carreras, _ = faa.leer(muestra("faa.html"))
    assert aplicar_carteles(carreras) >= 5
    c = buscar(carreras, "Cartaya")
    assert (c.poblacion, c.provincia, c.hora) == ("Cartaya", "Huelva", "10:00")
    assert c.inscripcion_hasta == datetime(2026, 11, 19, 14, 0) and c.calidad == "fuente"
    velez = buscar(carreras, "Vélez-Málaga")
    assert velez.fecha == date(2026, 11, 22) and velez.calidad == "dudoso"
    assert {"nombre": "10K", "euros": 10} in velez.precios
