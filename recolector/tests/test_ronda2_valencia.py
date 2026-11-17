"""Tests de la segunda ronda de la Comunitat Valenciana (Championchip Levante, Runática, Som Esport),
con copias recortadas del 17/11/2026."""
from datetime import date, datetime

from fuentes import chiplevante, runatica, somesport
from nucleo.modelo import ABIERTA, CERRADA, PENDIENTE_CARTEL
from tests.test_lectores import buscar, muestra


def test_chiplevante_portada_y_listado_sin_repetir():
    carreras, descartes = chiplevante.leer(muestra("chiplevante-portada.html"), muestra("chiplevante.html"))
    albatera = buscar(carreras, "Cabezo Negro")
    assert (albatera.fecha, albatera.poblacion, albatera.provincia, albatera.modalidad) == (
        date(2026, 11, 22), "Albatera", "Alicante", "montaña")
    assert albatera.fuente.url == ("https://www.chiplevante.com/es/prueba/"
                                   "cross-de-montana-subida-al-cabezo-negro-albatera-1101-2026")
    assert sum("Cabezo Negro" in c.nombre for c in carreras) == 1  # sale en las dos páginas
    aspe = buscar(carreras, "Villa de Aspe")
    assert (aspe.fecha, aspe.distancias_km) == (date(2026, 12, 20), [5.0, 11.0, 21.097])
    assert buscar(carreras, "Alcaraz").provincia == "Albacete"
    assert buscar(carreras, "Cáncer de Mama").poblacion == "Elche"
    assert buscar(carreras, "Guardamar").modalidad == "cross"
    assert not any(x in c.nombre for c in carreras for x in ("BTT", "Hyrace", "Uci", "Ruta"))
    assert any("Hyrace" in d for d in descartes) and any("Ermites" in d for d in descartes)
    assert albatera.calidad == PENDIENTE_CARTEL


def test_runatica_fecha_hora_cierre_y_solo_inscripciones():
    carreras, descartes = runatica.leer(muestra("runatica.html"))
    alzira = buscar(carreras, "San Silvestre Solidaria Alzira")
    assert (alzira.fecha, alzira.hora, alzira.poblacion, alzira.provincia, alzira.distancias_km) == (
        date(2026, 12, 20), "10:30", "Alzira", "Valencia", [5.0])
    assert (alzira.inscripcion_desde, alzira.inscripcion_hasta) == (datetime(2026, 11, 1, 10), datetime(2026, 12, 17, 23, 59, 59))
    assert alzira.url_inscripcion == "https://www.runatica.com/event/vii-san-silvestre-alzira-2026"
    assert buscar(carreras, "Dements").poblacion == "Eslida"  # «Eslida / Aín (Castellón)»
    media = buscar(carreras, "Mitja Marató Ciutat d'Alzira")
    assert media.distancias_km == [21.097]
    assert media.inscripcion_hasta is None  # el cierre (27/01/2026) es del año anterior
    daurada = buscar(carreras, "Costa Daurada")
    assert (daurada.poblacion, daurada.provincia, daurada.hora) == (None, "Tarragona", None)  # «a las 00:00»
    assert not any("Pasada" in c.nombre for c in carreras)  # lo de «Resultados» no se lee
    for quitada in ("Montsant Bike", "Cross Escolar", "Esquí", "Circuito Gudar"):
        assert any(quitada in d for d in descartes), quitada
    assert runatica.recortar(b"a<span lang=\"es\">Resultados</span>b") == b"a"


def test_somesport_calendario_de_las_marinas():
    carreras, descartes = somesport.leer(muestra("somesport.html"))
    benidoleig = buscar(carreras, "Benidoleig")
    assert (benidoleig.fecha, benidoleig.poblacion, benidoleig.provincia, benidoleig.distancias_km) == (
        date(2026, 11, 22), "Benidoleig", "Alicante", [7.0])
    assert benidoleig.url_inscripcion == "https://www.somesport.com/solidariabenidoleig/correr-26.php"
    assert buscar(carreras, "Raval").provincia == "Valencia"  # Gandia
    assert buscar(carreras, "Raval").estado_fuente == ABIERTA
    montgo = buscar(carreras, "Baix Montgó")
    assert (montgo.distancias_km, montgo.estado_fuente, montgo.modalidad) == ([8.5, 13.3], CERRADA, "cross")
    assert "llistat" not in (montgo.fuente.url + (montgo.url_inscripcion or ""))  # nunca la lista de inscritos
    assert buscar(carreras, "Alfàs del Pi").poblacion == "L'Alfàs del Pi"
    assert not any("Circuit" in c.nombre or "Caminada" in c.nombre for c in carreras)
    assert sum("Circuit" in d for d in descartes) == 2
