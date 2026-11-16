from datetime import date

from fuentes import anunciadas
from nucleo.duplicados import deduplicar
from nucleo.modelo import Carrera, Fuente

DATOS = {"carreras": [
    {"nombre": "Zurich Maratón de Sevilla", "fecha": "2027-02-21", "hora": "08:30", "poblacion": "Sevilla",
     "provincia": "Sevilla", "distancias_km": [42.195], "modalidad": "asfalto", "url_oficial": "https://ejemplo.es/maraton",
     "estado_inscripcion": "abierta", "comprobado": "2026-11-16"},
    {"nombre": "Media Maratón Ciudad de Granada", "fecha": "2027-04-24", "poblacion": "Granada", "provincia": "Granada",
     "url_oficial": "https://ejemplo.es/media", "estado_inscripcion": "no_abierta", "abre": "2027-01-10",
     "fecha_provisional": True},
    {"nombre": "Pasada", "fecha": "2026-01-01", "provincia": "Málaga", "url_oficial": "https://x.es"},
    {"nombre": "De fuera", "fecha": "2027-03-01", "provincia": "Madrid", "url_oficial": "https://x.es"},
]}


def test_lee_anunciadas():
    carreras, descartes = anunciadas.leer(DATOS, date(2026, 11, 16))
    assert [c.nombre for c in carreras] == ["Zurich Maratón de Sevilla", "Media Maratón Ciudad de Granada"]
    sevilla, granada = carreras
    assert sevilla.distancias_km == [42.195] and sevilla.hora == "08:30" and sevilla.estado_fuente == "abierta"
    assert "comprobada el 2026-11-16" in sevilla.previos[0]
    assert granada.estado_fuente == "no_abierta" and granada.inscripcion_desde.date() == date(2027, 1, 10)
    assert granada.distancias_km == [21.097] or granada.distancias_km == []
    assert granada.calidad == "dudoso"
    assert len(descartes) == 2


def test_manda_la_plataforma_al_unir():
    anunciada = anunciadas.leer(DATOS, date(2026, 11, 16))[0][0]
    plataforma = Carrera(nombre="XLII Zurich Maratón de Sevilla", fecha=date(2027, 2, 21),
                         fuente=Fuente("sportmaniacs", "https://sm.es/x"), poblacion="Sevilla")
    unicas, _ = deduplicar([anunciada, plataforma])
    assert len(unicas) == 1 and unicas[0].fuente.id == "sportmaniacs"
    assert unicas[0].distancias_km == [42.195] and unicas[0].hora == "08:30"
