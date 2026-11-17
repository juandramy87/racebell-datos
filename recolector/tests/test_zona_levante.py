"""Tests de los lectores de Levante (Comunitat Valenciana y Región de Murcia), con copias del 17/11/2026."""
from datetime import date, datetime

from fuentes import crono4sports, dorsal21, facv, fdmvalencia, levante, lineadesalida
from nucleo.modelo import NO_ABIERTA, PENDIENTE_CARTEL
from tests.test_lectores import buscar, muestra


def test_levante_valenciano_y_provincia_murciana():
    assert levante.clasificar("XI Volta a peu Beniflà") == (True, "asfalto")
    assert levante.clasificar("XIV Cursa popular solidaria Beniarjó")[0]
    assert levante.clasificar("7ª Carrera Cuatro Santos y Marcha Solidaria") == (True, "asfalto")
    assert not levante.clasificar("Ruta senderista Estación de Calasparra")[0]
    assert levante.distancias("XXII Mitja Marató de Xàtiva") == [21.097]
    assert levante.distancias("Media Maratón de Cieza y XVII 11.3K Solidarios") == [11.3, 21.097]
    assert levante.provincia_murciana("Campoamor") == "Alicante"
    assert levante.provincia_murciana("El Palmar") == "Murcia"


def test_crono4sports_listado_y_portada():
    carreras, descartes = crono4sports.leer(muestra("crono4sports.html"), muestra("crono4sports-portada.html"),
                                            hoy=date(2026, 11, 17))
    assert {c.provincia for c in carreras} == {"Valencia", "Alicante", "Castellón"}
    xeraco = buscar(carreras, "Xeraco")
    assert xeraco.fecha == date(2027, 1, 6)  # «6 ENE» visto en noviembre: año siguiente
    # Xàtiva solo sale en el carrusel de la portada, sin provincia: sin ficha no se puede guardar.
    assert any("Xàtiva" in d and "sin provincia" in d for d in descartes)
    tarjeta = next(t for t in crono4sports.tarjetas(muestra("crono4sports-portada.html")) if "Xàtiva" in t["nombre"])
    assert (tarjeta["dia_mes"], tarjeta["lugar"]) == ("28 feb 2027", "Xàtiva")
    assert buscar(carreras, "Medieval Xtrem").modalidad == "obstáculos"
    assert not any("Travess" in c.nombre or "Bany" in c.nombre or "Hybrid" in c.nombre for c in carreras)
    assert any("Natación" in d for d in descartes) and any("Híbrido" in d for d in descartes)


def test_crono4sports_ficha_da_hora_distancia_y_cierre():
    carreras, _ = crono4sports.leer(muestra("crono4sports.html"), hoy=date(2026, 11, 17),
                                    descargar_ficha=lambda url: muestra("crono4sports-ficha.html"))
    c = buscar(carreras, "Beniflà")
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 22), "09:30", "Beniflà", "Valencia")
    assert c.distancias_km == [8.5]  # la de menores no cuenta
    assert (c.inscripcion_desde, c.inscripcion_hasta) == (datetime(2026, 10, 17, 0, 0), datetime(2026, 11, 21, 14, 0))
    assert c.url_inscripcion == "https://crono4sports.com/evento/xi-volta-a-peu-benifla"


def test_fdmvalencia():
    carreras, descartes = fdmvalencia.leer(muestra("fdmvalencia.html"))
    assert len(carreras) == 5
    m = buscar(carreras, "Maratón València")
    assert (m.fecha, m.hora, m.provincia, m.distancias_km) == (date(2026, 12, 6), "08:15", "Valencia", [42.195])
    assert m.fuente.url == "https://www.valenciaciudaddelrunning.com/maraton"  # «Más información»
    assert buscar(carreras, "Pas Ras").distancias_km == [10.0]
    assert any("Mini Maratón" in d for d in descartes)
    assert m.calidad == PENDIENTE_CARTEL


def test_facv_solo_ruta_y_cross_populares_de_la_comunitat():
    carreras, descartes = facv.leer(muestra("facv.html"))
    assert {c.provincia for c in carreras} == {"Alicante", "Valencia"}
    utiel = buscar(carreras, "Cross Ciudad de Utiel")
    assert (utiel.fecha, utiel.poblacion, utiel.modalidad, utiel.distancias_km) == (date(2026, 11, 29), "Utiel", "cross", [])
    crev = buscar(carreras, "Crevillentina")
    assert (crev.fecha, crev.hora, crev.poblacion) == (date(2026, 12, 31), "09:30", "Crevillent")
    assert buscar(carreras, "Benidorm Half").provincia == "Alicante"
    assert not any("Escolar" in c.nombre or "Campeonato" in c.nombre for c in carreras)
    assert any("Burgos" in d for d in descartes)


def test_lineadesalida():
    carreras, descartes = lineadesalida.leer(muestra("lineadesalida.html"))
    c = buscar(carreras, "Puerto de Cartagena")
    assert (c.fecha, c.poblacion, c.provincia) == (date(2026, 11, 21), "Cartagena", "Murcia")
    assert buscar(carreras, "Campoamor").provincia == "Alicante"
    assert buscar(carreras, "Vista Alegre").modalidad == "montaña"
    assert any("Baño de Navidad" in d for d in descartes)


def test_dorsal21():
    carreras, descartes = dorsal21.leer(muestra("dorsal21.html"))
    c = buscar(carreras, "Los Rosales")
    assert (c.fecha, c.poblacion, c.provincia) == (date(2026, 11, 21), "El Palmar", "Murcia")
    assert c.url_inscripcion == "https://www.babelsport.com/evento/rosales-2026/"
    assert buscar(carreras, "Quiero Crecer").nombre == "II Carrera y Marcha Solidaria Quiero Crecer"
    assert buscar(carreras, "Novelda").provincia == "Alicante"
    assert buscar(carreras, "Cieza").distancias_km == [11.3, 21.097]
    assert buscar(carreras, "Cuatro Santos")  # carrera y marcha: la carrera cuenta
    assert any("Benjamin" in d for d in descartes) and any("senderista" in d for d in descartes)
    assert all(c.estado_fuente in (None, NO_ABIERTA) for c in carreras)


def test_cronorunner_api_publica():
    from fuentes import cronorunner
    carreras, descartes = cronorunner.leer(muestra("cronorunner.json"))
    assert len(carreras) == 16 and not descartes
    c = next(c for c in carreras if "Dinosauris" in c.nombre)
    assert (c.fecha, c.poblacion, c.provincia, c.distancias_km) == (date(2026, 11, 22), "Moncada", "Valencia", [5.0, 10.0])
    assert next(c for c in carreras if "Bali" in c.nombre).provincia == "Alicante"  # Benidorm
