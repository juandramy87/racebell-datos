import json
from datetime import date

from nucleo import municipios
from nucleo.modelo import Carrera, Fuente


def respuesta(*resultados):
    return json.dumps(list(resultados)).encode()


def test_rellena_provincia_y_coords_solo_en_andalucia():
    tabla = {}
    pedidas = []

    def descargar(url):
        pedidas.append(url)
        return respuesta(
            {"lat": "39.4", "lon": "-3.0", "address": {"state": "Castilla-La Mancha", "province": "Ciudad Real"}},
            {"lat": "37.8512", "lon": "-4.8890", "address": {"state": "Andalucía", "province": "Córdoba"}},
        )

    dato = municipios.buscar("Villarrubia", None, descargar, tabla)
    assert dato == {"provincia": "Córdoba", "lat": 37.8512, "lon": -4.889}
    municipios.buscar("Villarrubia", None, descargar, tabla)
    assert len(pedidas) == 1  # la segunda vez sale de la tabla


def test_no_cambia_una_provincia_conocida_por_otra():
    def descargar(url):
        return respuesta({"lat": "37.0", "lon": "-4.0", "address": {"state": "Andalucía", "province": "Málaga"}})

    assert municipios.buscar("Algarrobo", "Granada", descargar, {}) is None


def test_completar_quita_el_aviso_de_provincia(tmp_path, monkeypatch):
    monkeypatch.setattr(municipios, "RUTA", tmp_path / "municipios.json")
    c = Carrera(nombre="XIII CxM Prueba", fecha=date(2026, 11, 21), fuente=Fuente("time2run", "u"), poblacion="Priego de Córdoba")
    c.marcar("Provincia sin indicar en Time2Run: confirmarla", "pendiente_cartel")

    def descargar(url):
        return respuesta({"lat": "37.4380", "lon": "-4.1950", "address": {"state": "Andalucía", "province": "Córdoba"}})

    assert municipios.completar([c], descargar) == 1
    assert c.provincia == "Córdoba" and c.coords == (37.438, -4.195) and not c.avisos_calidad
