"""Segunda ronda: Canarias, La Rioja, Cantabria y Asturias (copias recortadas de las webs del 17/11/2026)."""
from datetime import date, datetime

from fuentes import conchip, cronoline, empat, logronodeporte
from nucleo.modelo import PENDIENTE_CARTEL
from tests.test_lectores import buscar, muestra

HOY = date(2026, 11, 17)


def test_conchip():
    carreras, descartes = conchip.leer(muestra("conchip.html"))
    assert [c.nombre for c in carreras] == ["I Milla Azul Ciudad de la Laguna 2026", "San Silvestre Realejera 2026"]
    c = buscar(carreras, "Realejera")
    assert (c.fecha, c.hora) == (date(2026, 12, 27), "11:00")
    assert (c.poblacion, c.provincia) == ("Los Realejos", "Santa Cruz de Tenerife")
    assert c.inscripcion_hasta == datetime(2026, 12, 20, 23, 59)
    assert c.fuente.id == "conchip"
    assert c.url_inscripcion == "https://www.avaibooksports.com/inscripcion/san-silvestre-realejera-2026/"
    assert c.coords and 28 < c.coords[0] < 29.5 and -17 < c.coords[1] < -16
    assert any("Medallón" in d for d in descartes)  # producto, no carrera
    assert any("Donación" in d for d in descartes)  # especialidad «Otro»


def test_empat():
    carreras, _ = empat.leer(muestra("empat.html"))
    assert len(carreras) == 4 and {c.provincia for c in carreras} == {"Asturias"}
    salas = buscar(carreras, "Trail Salas")
    assert (salas.fecha, salas.poblacion, salas.modalidad) == (date(2026, 11, 22), "Salas", "trail")
    assert salas.inscripcion_hasta == datetime(2026, 11, 18, 23, 59)
    # Sin enlace a AvaiBook: se usa la web del organizador.
    assert buscar(carreras, "Minero").fuente.url == "https://trailsantabarbara.com"
    assert buscar(carreras, "Triásica").modalidad == "asfalto"


def test_logronodeporte():
    carreras, descartes = logronodeporte.leer(muestra("logronodeporte.html"), hoy=HOY)
    assert len(carreras) == 3  # el maratón de octubre ya se corrió
    sarrio = buscar(carreras, "Desafío Sarrio")
    assert (sarrio.fecha, sarrio.hora, sarrio.distancias_km) == (date(2026, 11, 29), "11:00", [10.0, 24.0])
    assert (sarrio.poblacion, sarrio.provincia) == ("Logroño", "La Rioja")
    assert sarrio.fuente.url == "https://circuito.logronodeporte.es/carrera/II-Desafio-Sarrio"
    ss = buscar(carreras, "San Silvestre")
    assert (ss.fecha, ss.hora) == (date(2026, 12, 31), "18:45")  # «jueves, 31 de diciembre» → 2026
    assert all(c.calidad == PENDIENTE_CARTEL for c in carreras)


def test_logronodeporte_anyo_por_dia_de_semana():
    assert logronodeporte._fecha("domingo, 08 de febrero a las 11:00:00", HOY) == (date(2026, 2, 8), "11:00")
    assert logronodeporte._fecha("domingo, 07 de febrero a las 10:00:00", HOY) == (date(2027, 2, 7), "10:00")


def test_cronoline():
    carreras, descartes = cronoline.leer(muestra("cronoline.html"), hoy=HOY)
    assert len(carreras) == 2
    m = buscar(carreras, "Maratón Dany Sport")
    assert (m.fecha, m.poblacion, m.provincia) == (date(2026, 12, 12), "Corralejo", "Las Palmas")
    assert m.modalidad == "asfalto"
    assert any("Marcha" in d for d in descartes) and any("Copa" in d for d in descartes)
    assert not any("Titan" in c.nombre for c in carreras)  # ya celebrada
    assert cronoline._lugar("Cross San Bartolomé Globara") == ("San Bartolomé", "Las Palmas")
    assert cronoline._lugar("Milla de Santa Marta") is None  # Santa Marta es de Badajoz, no de las islas
