"""Lectores de Cataluña (17/11/2026): 9hSports, Championchip (xipgroc), FCA, Iter5, Curses.cat y CronoSports,
y las ayudas comunes de fuentes/cataluna.py. Muestras recortadas en tests/muestras/ (sin datos personales)."""
from datetime import date, datetime

from fuentes import cataluna as cat
from fuentes import cronosports, cursescat, fca, hsports, iter5, xipgroc
from nucleo.modelo import ABIERTA, PENDIENTE_CARTEL
from tests.test_lectores import buscar, muestra


def test_municipios_catalanes():
    assert cat.municipio("PINELL DE BRAI, EL") == ("El Pinell de Brai", "Tarragona")
    assert cat.municipio("SANT GREGORI (MUNICIPIO)") == ("Sant Gregori", "Girona")
    assert cat.municipio("SANT LLORENÇ (MATADEPERA)") == ("Matadepera", "Barcelona")
    assert cat.municipio("GIRONA-ELS ANGELS") == ("Girona", "Girona")
    assert cat.municipio("ST. LLORENÇ DE LA MUGA") == ("Sant Llorenç de la Muga", "Girona")
    assert cat.municipio("BELLCAIRE D&#039;EMPORDÀ") == ("Bellcaire d'Empordà", "Girona")
    assert cat.municipio("Vila-seca") == ("Vila-seca", "Tarragona")
    assert cat.municipio("Atapuerca (Burgos)") is None
    assert len(cat._tabla()) > 947  # los 947 municipios más las formas sin artículo y los alias


def test_municipio_en_el_nombre():
    assert cat.municipio_en("Cursa de Parets del Vallès") == ("Parets del Vallès", "Barcelona")
    assert cat.municipio_en("1a Cursa Antiracista Santa Perpetua de Mogoda 2026") == ("Santa Perpètua de Mogoda", "Barcelona")
    assert cat.municipio_en("Cursa de Sant Andreu - Barcelona") == ("Barcelona", "Barcelona")
    assert cat.municipio_en("Pujada a la Seu Vella") == ("Lleida", "Lleida")  # la catedral de Lleida, no La Seu d'Urgell
    assert cat.municipio_en("Cursa de les Fonts") is None  # «Les» es un municipio, pero aquí es un artículo
    assert cat.municipio_en("Cursa per la Pau") is None


def test_catalan_a_castellano():
    assert cat.clasificar("Cursa i caminada Entrecabanes") == (True, "asfalto")
    assert cat.clasificar("Caminada d'Artesa de Lleida")[0] is False
    assert cat.clasificar("X Marxa solidària anARIanant")[0] is False
    assert cat.clasificar("Duatló Cross Hivernal")[0] is False
    assert cat.clasificar("Canitrail d'Ordal")[0] is False
    assert cat.clasificar("IX Cros de Cardedeu") == (True, "cross")
    assert cat.clasificar("Cursa de Muntanya de Llagostera") == (True, "montaña")
    assert cat.clasificar("Crono Escalada Boí - Taüll") == (True, "montaña")
    assert cat.distancias("37a MITJA MARATÓ i 10K Ciutat de Vilanova") == [10.0, 21.097]
    assert cat.distancias("20a Cursa de Parets (5 i 10 Km)") == [5.0, 10.0]
    assert cat.es_infantil("Mitja Marató de Sitges (Infantils)")
    assert cat.es_infantil("Sant Silvestre de Bellver KIDS")
    assert not cat.es_infantil("34è Cros escolar i 31è Cros popular de les Franqueses del Vallès")
    assert not cat.es_infantil("5K de Nadal i Minicurses 2026")
    assert cat.fecha("21 novembre 2026") == date(2026, 11, 21)
    assert cat.fecha("07-Març-2027") == date(2027, 3, 7)
    assert cat.fecha("Dijous 03/12/2026") == date(2026, 12, 3)


def test_9hsports():
    carreras, descartes = hsports.leer(muestra("9hsports.html"))
    assert len(carreras) == 59  # la tarjeta repetida no cuenta dos veces
    c = buscar(carreras, "Roc de la Clusa")
    assert (c.fecha, c.poblacion, c.provincia) == (date(2026, 11, 21), "Castell de l'Areny", "Barcelona")
    assert c.estado_fuente == ABIERTA and c.fuente.url == "https://www.9hsports.cat/ca/informacio_cursa/1115"
    assert buscar(carreras, "Biberons").poblacion == "El Pinell de Brai"
    assert buscar(carreras, "Monroyo").provincia == "Teruel"  # también publica alguna de fuera
    assert buscar(carreras, "Vilaverd Skyrace").estado_fuente is None  # «Veure inscrits»: no se sabe si abierta
    assert buscar(carreras, "Crono Escalada").modalidad == "montaña"
    assert not any("Prova" in c.nombre or "KIDS" in c.nombre or "Canillo" in c.nombre for c in carreras)
    assert any("Canitrail" in d for d in descartes) and any("Caminada" in d for d in descartes)


def test_xipgroc():
    assert len(xipgroc.otras_paginas(muestra("xipgroc-1.html"), date(2026, 11, 17), date(2027, 1, 31))) == 2
    carreras, descartes = xipgroc.leer([muestra("xipgroc-1.html"), muestra("xipgroc-2.html")])
    c = buscar(carreras, "Cursa de Parets")
    assert (c.fecha, c.poblacion, c.provincia, c.distancias_km) == (date(2026, 11, 22), "Parets del Vallès", "Barcelona", [5.0, 10.0])
    assert c.url_inscripcion.startswith("https://xipgroc.cat/ca/curses/Parets2026/") and c.estado_fuente == ABIERTA
    assert buscar(carreras, "Pujada i Baixada a Guanta").distancias_km == [6.0, 12.3]
    assert buscar(carreras, "Sagrera").poblacion == "Barcelona"  # barrio de Barcelona
    sin_pueblo = buscar(carreras, "Les Ciutats Contra el Càncer")
    assert sin_pueblo.provincia is None and sin_pueblo.comunidad == "cataluna"
    assert any(t == PENDIENTE_CARTEL and "Población" in x for t, x in sin_pueblo.avisos_calidad)
    assert not any("Infantils" in c.nombre or "SwimSilvestre" in c.nombre or "Marxa" in c.nombre for c in carreras)
    assert any("icono «n»" in d for d in descartes)


def test_fca():
    carreras, descartes = fca.leer([muestra("fca-1.json"), muestra("fca-4.json")])
    c = buscar(carreras, "Cros de Vidreres")
    assert (c.fecha, c.poblacion, c.provincia, c.modalidad) == (date(2026, 11, 29), "Vidreres", "Girona", "cross")
    assert buscar(carreras, "Mitja Marató Espirall").url_inscripcion == "https://mitja.vilafranca.cat/"
    assert buscar(carreras, "Maratón Valencia").provincia == "Valencia"
    assert buscar(carreras, "Lo Port Vertical").modalidad == "montaña"
    assert not any("Campionat d’Espanya" in c.nombre or "Europa" in c.nombre for c in carreras)
    assert any("Campionat d’Espanya de Cros per Clubs" in d for d in descartes)


def test_iter5():
    carreras, descartes = iter5.leer(muestra("iter5.html"))
    c = buscar(carreras, "Indiot de Mollerussa")
    assert (c.fecha, c.poblacion, c.provincia, c.distancias_km) == (date(2026, 12, 26), "Mollerussa", "Lleida", [5.0, 10.0])
    assert c.url_inscripcion == "https://iter5.cat/inscripcions/formCursa.php?id=2150"
    sin_pueblo = buscar(carreras, "Espardenya - Trail")
    assert (sin_pueblo.poblacion, sin_pueblo.provincia, sin_pueblo.modalidad) == (None, "Lleida", "trail")
    assert not any("Duatl" in c.nombre or "Caminada d'Artesa" in c.nombre or "Impermeable" in c.nombre.title()
                   or "Infantils" in c.nombre for c in carreras)
    assert any("duatlón" in d for d in descartes)


def test_cursescat():
    carreras, descartes = cursescat.leer(muestra("cursescat.html"))
    c = buscar(carreras, "Trail la Vall")
    assert (c.fecha, c.poblacion, c.provincia, c.modalidad) == (date(2026, 12, 13), "Bellcaire d'Empordà", "Girona", "trail")
    assert c.distancias_km == [6.0, 13.0, 22.0, 46.0]
    assert buscar(carreras, "Fox Trail").poblacion == "Sant Llorenç de la Muga"
    assert buscar(carreras, "Cims de Girona Rocacorba").poblacion == "Girona"
    assert not any("BTT" in c.nombre or "Caminada" in c.nombre or "Virtual" in c.nombre for c in carreras)
    assert any("virtual" in d for d in descartes)


def test_cronosports_con_cierre_de_la_ficha():
    carreras, _ = cronosports.leer(muestra("cronosports.html"), descargar_ficha=lambda url: muestra("cronosports-ficha.html"))
    assert len(carreras) == 8
    c = buscar(carreras, "Enric Race")
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 22), "09:30", "Castellterçol", "Barcelona")
    assert c.inscripcion_hasta == datetime(2026, 11, 20, 20, 0) and c.precios == [{"nombre": "Desde", "euros": 6.0}]
    assert buscar(carreras, "Mitja Marató del Maresme").distancias_km == [21.097]
    sin_ficha, _ = cronosports.leer(muestra("cronosports.html"))
    assert all(c.inscripcion_hasta is None for c in sin_ficha)
